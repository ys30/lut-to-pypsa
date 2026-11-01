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

    network = solved_network
    if network.loads.empty or network.generators.empty:
        raise ValueError("Summary requires loads and generators")
    if not network.storage_units.empty or not network.stores.empty or not network.links.empty or not network.lines.empty:
        raise ValueError("Summary supports generator-only networks without transfers or storage")
    if len(network.buses) != 1:
        raise ValueError("Summary requires a single-bus network")
    snapshots = network.snapshots
    dispatch = network.generators_t.p.reindex(index=snapshots, columns=network.generators.index)
    if dispatch.isna().any().any():
        raise ValueError("Missing solved generator dispatch")
    demand = network.loads_t.p_set.reindex(index=snapshots, columns=network.loads.index)
    if demand.isna().any().any():
        raise ValueError("Missing hourly demand")
    weights = network.snapshot_weightings["generators"].reindex(snapshots)
    if weights.isna().any() or (weights <= 0).any():
        raise ValueError("Invalid snapshot weights")
    generation_mwh = float(dispatch.sum(axis=1).mul(weights).sum())
    demand_mwh = float(demand.sum(axis=1).mul(weights).sum())
    imbalance_mwh = generation_mwh - demand_mwh
    if abs(imbalance_mwh) > tolerance_mwh:
        raise ValueError(f"Dispatch energy imbalance: {imbalance_mwh} MWh")
    marginal_cost = pd.to_numeric(network.generators.marginal_cost, errors="raise")
    if marginal_cost.isna().any():
        raise ValueError("Missing generator marginal cost")
    operating_cost = float(dispatch.mul(marginal_cost, axis=1).sum(axis=1).mul(weights).sum())
    return {
        "demand_mwh": demand_mwh,
        "generation_mwh": generation_mwh,
        "imbalance_mwh": imbalance_mwh,
        "operating_cost_eur": operating_cost,
        "scope": "synthetic_single_bus_generator_only",
    }
