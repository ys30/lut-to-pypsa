"""Small, explicitly illustrative dispatch optimization for an adapted PyPSA network.

This is a smoke test, not a calibrated LUT scenario or evidence of equivalence.
All assets are fixed-capacity. No investment optimization is performed.
"""


def solve_illustrative_dispatch(network, *, solver_name="highs"):
    """Optimize a copy and return (solved_network, solver_status, termination_condition).

    Refuse missing load, generation, or snapshots rather than returning a
    misleading successful solve. The caller must inspect the termination
    condition and may not interpret the output as an empirical LUT result.
    """
    if len(network.snapshots) == 0:
        raise ValueError("Dispatch requires at least one snapshot")
    if network.loads.empty:
        raise ValueError("Dispatch requires at least one Load")
    if network.generators.empty:
        raise ValueError("Dispatch requires at least one Generator")
    if not network.storage_units.empty or not network.stores.empty or not network.links.empty or not network.lines.empty:
        raise ValueError("Illustrative dispatch supports generator-only networks without transfers or storage")
    if len(network.buses) != 1:
        raise ValueError("Illustrative dispatch requires a single-bus network")
    bus = network.buses.index[0]
    if not network.generators.bus.eq(bus).all() or not network.loads.bus.eq(bus).all():
        raise ValueError("Illustrative dispatch requires all generators and loads on the same bus")
    result = network.copy()
    status, condition = result.optimize(solver_name=solver_name)
    if status != "ok" or condition != "optimal":
        raise RuntimeError(f"Illustrative dispatch failed: {status}/{condition}")
    return result, status, condition



def summarize_illustrative_dispatch(solved_network, *, tolerance_mwh=1e-5):
    """Summarize solved hourly dispatch; only for single-bus, generator-only examples.

    This intentionally rejects storage, links, and lines, where generator
    output alone cannot represent complete nodal energy accounting.
    Snapshot weights are applied to energy and operating cost.
    """
    import pandas as pd
    import numpy as np

    network = solved_network
    if network.loads.empty or network.generators.empty:
        raise ValueError("Summary requires loads and generators")
    if not network.storage_units.empty or not network.stores.empty or not network.links.empty or not network.lines.empty:
        raise ValueError("Summary supports generator-only networks without transfers or storage")
    if len(network.buses) != 1:
        raise ValueError("Summary requires a single-bus network")
    bus = network.buses.index[0]
    if not network.generators.bus.eq(bus).all() or not network.loads.bus.eq(bus).all():
        raise ValueError("Summary requires all generators and loads on the same bus")
    snapshots = network.snapshots
    dispatch = network.generators_t.p.reindex(index=snapshots, columns=network.generators.index)
    if dispatch.isna().any().any():
        raise ValueError("Missing solved generator dispatch")
    # PyPSA permits constant Load.p_set values without a loads_t.p_set column.
    # Broadcast static setpoints, then override with any explicit time series.
    demand = pd.DataFrame(
        {name: float(value) for name, value in network.loads.p_set.items()},
        index=snapshots,
    )
    for name in network.loads_t.p_set.columns.intersection(network.loads.index):
        demand[name] = network.loads_t.p_set[name].reindex(snapshots)
    if demand.isna().any().any():
        raise ValueError("Missing hourly demand")
    if not np.isfinite(dispatch.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite generator dispatch")
    if not np.isfinite(demand.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite hourly demand")
    weights = network.snapshot_weightings["generators"].reindex(snapshots)
    if not np.isfinite(weights.to_numpy(dtype=float)).all() or (weights <= 0).any():
        raise ValueError("Invalid snapshot weights")
    hourly_imbalance = dispatch.sum(axis=1) - demand.sum(axis=1)
    if (hourly_imbalance.abs() > tolerance_mwh).any():
        raise ValueError("Hourly dispatch energy imbalance")
    generation_mwh = float(dispatch.sum(axis=1).mul(weights).sum())
    demand_mwh = float(demand.sum(axis=1).mul(weights).sum())
    imbalance_mwh = generation_mwh - demand_mwh
    if not np.isfinite(generation_mwh) or not np.isfinite(demand_mwh) or not np.isfinite(imbalance_mwh):
        raise ValueError("Nonfinite weighted dispatch energy")
    if abs(imbalance_mwh) > tolerance_mwh:
        raise ValueError(f"Dispatch energy imbalance: {imbalance_mwh} MWh")
    marginal_cost = pd.to_numeric(network.generators.marginal_cost, errors="raise")
    if marginal_cost.isna().any() or not np.isfinite(marginal_cost.to_numpy(dtype=float)).all():
        raise ValueError("Invalid generator marginal cost")
    # Broadcast static costs and override with time-varying costs where provided.
    hourly_cost = pd.DataFrame(
        {name: float(value) for name, value in marginal_cost.items()}, index=snapshots
    )
    for name in network.generators_t.marginal_cost.columns.intersection(network.generators.index):
        hourly_cost[name] = network.generators_t.marginal_cost[name].reindex(snapshots)
    if not np.isfinite(hourly_cost.to_numpy(dtype=float)).all():
        raise ValueError("Invalid time-varying generator marginal cost")
    objective_weights = network.snapshot_weightings["objective"].reindex(snapshots)
    if not np.isfinite(objective_weights.to_numpy(dtype=float)).all() or (objective_weights <= 0).any():
        raise ValueError("Invalid objective snapshot weights")
    operating_cost = float(dispatch.mul(hourly_cost).sum(axis=1).mul(objective_weights).sum())
    if not np.isfinite(operating_cost):
        raise ValueError("Nonfinite operating cost")
    return {
        "demand_mwh": demand_mwh,
        "generation_mwh": generation_mwh,
        "imbalance_mwh": imbalance_mwh,
        "operating_cost_eur": operating_cost,
        "scope": "synthetic_single_bus_generator_only",
    }
