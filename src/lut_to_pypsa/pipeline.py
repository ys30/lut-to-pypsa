"""A documented LUT-*style* adapter; not an adapter for an actual LUT export."""
from pathlib import Path
import pandas as pd
from .validation import validate_inputs

def load_tables(folder):
    folder = Path(folder)
    return tuple(pd.read_csv(folder / name) for name in ("regions.csv", "generators.csv", "demand.csv"))

def harmonize(regions, generators, demand):
    """Convert illustrative demand from GWh per one-hour interval to MW."""
    report = validate_inputs(regions, generators, demand)
    demand = demand.copy()
    demand["timestamp"] = pd.to_datetime(demand.timestamp, utc=True).dt.tz_convert(None)
    demand["p_set_mw"] = pd.to_numeric(demand.demand_gwh) * 1000.0
    return regions.copy(), generators.copy(), demand, report

def build_network(regions, generators, demand):
    import pypsa
    regions, generators, demand, report = harmonize(regions, generators, demand)
    n = pypsa.Network()
    snapshots = pd.DatetimeIndex(sorted(demand.timestamp.unique()))
    n.set_snapshots(snapshots)
    for region in regions.region:
        n.add("Bus", str(region), carrier="AC")
        n.add("Load", f"load_{region}", bus=str(region))
    for row in generators.itertuples(index=False):
        n.add("Generator", str(row.generator), bus=str(row.region), carrier=str(row.carrier), p_nom=float(row.capacity_mw), marginal_cost=float(row.marginal_cost_eur_mwh))
    wide = demand.pivot(index="timestamp", columns="region", values="p_set_mw").reindex(snapshots)
    wide.columns = [f"load_{r}" for r in wide.columns]
    n.loads_t.p_set = wide.reindex(columns=n.loads.index)
    # Isolated regions are intentional: this toy network has no transmission lines.
    if hasattr(n, "consistency_check"):
        n.consistency_check()
    return n, report

def run_example(data_dir, output_path=None, optimize=False):
    regions, generators, demand = load_tables(data_dir)
    n, report = build_network(regions, generators, demand)
    if optimize:
        n.optimize(solver_name="highs")
    if output_path is not None:
        n.export_to_netcdf(str(output_path))
    return n, report
