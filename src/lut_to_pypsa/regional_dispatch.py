"""Fixed-capacity dispatch for disconnected regional buses (no storage or transfers).

This extends the illustrative single-bus smoke test to independent regions.
It is not an empirical LUT reproduction or a capacity-expansion model.
"""
import numpy as np
import pandas as pd


def solve_regional_dispatch(network, *, solver_name="highs", tolerance_mw=1e-5):
    """Solve fixed generator dispatch and audit hourly nodal energy balance."""
    if len(network.snapshots) == 0 or network.buses.empty:
        raise ValueError("Regional dispatch requires buses and snapshots")
    if network.generators.empty or network.loads.empty:
        raise ValueError("Regional dispatch requires generators and loads")
    if any(not getattr(network, component).empty for component in
           ("storage_units", "stores", "links", "lines", "transformers")):
        raise ValueError("Regional dispatch excludes storage and inter-bus transfers")
    buses = set(network.buses.index)
    if set(network.generators.bus) - buses or set(network.loads.bus) - buses:
        raise ValueError("Unknown generator or load bus")
    result = network.copy()
    status, condition = result.optimize(solver_name=solver_name)
    if (status, condition) != ("ok", "optimal"):
        raise RuntimeError(f"Regional dispatch failed: {status}/{condition}")
    snapshots = result.snapshots
    output = result.generators_t.p.reindex(index=snapshots, columns=result.generators.index)
    if output.isna().any().any():
        raise ValueError("Missing solved generation")
    demand = pd.DataFrame({name: float(value) for name, value in
                           result.loads.p_set.items()}, index=snapshots)
    for name in result.loads_t.p_set.columns.intersection(result.loads.index):
        demand[name] = result.loads_t.p_set[name].reindex(snapshots)
    if demand.isna().any().any():
        raise ValueError("Missing solved demand")
    records = []
    weights = result.snapshot_weightings["generators"].reindex(snapshots)
    if not np.isfinite(weights.to_numpy(dtype=float)).all() or (weights <= 0).any():
        raise ValueError("Invalid generator snapshot weights")
    for bus in result.buses.index:
        gen_names = result.generators.index[result.generators.bus.eq(bus)]
        load_names = result.loads.index[result.loads.bus.eq(bus)]
        generation = output[gen_names].sum(axis=1)
        consumption = demand[load_names].sum(axis=1)
        residual = generation - consumption
        if not np.isfinite(residual.to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite nodal balance at {bus}")
        if (residual.abs() > tolerance_mw).any():
            raise ValueError(f"Hourly nodal balance failed at {bus}")
        records.append({"bus": bus,
                        "demand_mwh": float(consumption.mul(weights).sum()),
                        "generation_mwh": float(generation.mul(weights).sum()),
                        "max_abs_balance_mw": float(residual.abs().max())})
    return result, pd.DataFrame.from_records(records), status, condition
