"""Build an explicitly scoped PyPSA network from reviewed technology intake CSVs.

This does not independently verify citations, calibrate demand, or optimize.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import pypsa

from .parameter_intake_cli import validate_intake
from .illustrative_dispatch import solve_illustrative_dispatch, summarize_illustrative_dispatch
from .parameter_adapter import attach_reviewed_components


def build_intake_network(parameters_path, evidence_path, mapping_path, buses_path,
                         *, snapshots, demand_path=None):
    """Return a network with fixed-capacity components and optional hourly MW loads.

    buses CSV: lut_technology,bus. demand CSV: snapshot,bus,demand_mw.
    Snapshot timestamps are explicit; there is no annual-to-hourly inference.
    """
    validate_intake(parameters_path, evidence_path, mapping_path)
    parameters = pd.read_csv(parameters_path)
    evidence = pd.read_csv(evidence_path)
    mapping = pd.read_csv(mapping_path)
    buses = pd.read_csv(buses_path)
    if not {"lut_technology", "bus"}.issubset(buses):
        raise ValueError("Bus mapping requires lut_technology,bus")
    if buses.empty or buses.isna().any().any() or buses.lut_technology.duplicated().any():
        raise ValueError("Invalid technology bus mapping")
    if buses.bus.astype(str).str.strip().eq("").any():
        raise ValueError("Blank technology bus")
    if set(buses.lut_technology) != set(parameters.lut_technology):
        raise ValueError("Technology bus mapping coverage mismatch")
    network = pypsa.Network()
    times = pd.DatetimeIndex(pd.to_datetime(snapshots))
    if len(times) == 0 or times.hasnans or not times.is_unique or not times.is_monotonic_increasing:
        raise ValueError("Snapshots must be nonempty, unique and ordered")
    network.set_snapshots(times)
    for bus in sorted(buses.bus.unique()):
        network.add("Bus", bus)
    bus_by_technology = dict(zip(buses.lut_technology, buses.bus))
    network = attach_reviewed_components(
        network, parameters, mapping, bus_by_technology, evidence=evidence, empirical=True
    )
    if demand_path is not None:
        demand = pd.read_csv(demand_path)
        required = {"snapshot", "bus", "demand_mw"}
        if not required.issubset(demand):
            raise ValueError("Hourly demand requires snapshot,bus,demand_mw")
        if demand.empty or demand[list(required)].isna().any().any():
            raise ValueError("Missing hourly demand")
        demand["snapshot"] = pd.to_datetime(demand["snapshot"])
        if demand.duplicated(["snapshot", "bus"]).any():
            raise ValueError("Duplicate hourly bus demand")
        if set(demand.bus) != set(network.buses.index):
            raise ValueError("Demand bus coverage mismatch")
        if set(demand.snapshot) != set(times) or len(demand) != len(times) * len(network.buses):
            raise ValueError("Incomplete hourly bus demand coverage")
        values = pd.to_numeric(demand.demand_mw, errors="raise")
        if not values.notna().all() or not (values >= 0).all() or not __import__("numpy").isfinite(values).all():
            raise ValueError("Invalid hourly demand MW")
        for bus in network.buses.index:
            series = demand.loc[demand.bus.eq(bus)].set_index("snapshot").demand_mw.reindex(times)
            network.add("Load", f"load_{bus}", bus=bus, p_set=series)
    return network


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parameters", "evidence", "mapping", "buses"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path, required=True,
                        help="CSV with a snapshot column")
    parser.add_argument("--demand", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solve-illustrative", action="store_true",
                        help="Run only the supported synthetic single-bus generator-only dispatch")
    parser.add_argument("--summary-json", type=Path,
                        help="Required with --solve-illustrative; write audited solve metrics")
    args = parser.parse_args(argv)
    times = pd.read_csv(args.snapshots)
    if "snapshot" not in times or times.empty:
        raise ValueError("Snapshot CSV must contain populated snapshot column")
    network = build_intake_network(args.parameters, args.evidence, args.mapping,
                                   args.buses, snapshots=times.snapshot, demand_path=args.demand)
    if args.solve_illustrative:
        if args.demand is None or args.summary_json is None:
            parser.error("--solve-illustrative requires --demand and --summary-json")
        network, status, condition = solve_illustrative_dispatch(network)
        summary = summarize_illustrative_dispatch(network)
        summary.update({"solver_status": status, "termination_condition": condition})
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    elif args.summary_json is not None:
        parser.error("--summary-json requires --solve-illustrative")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    network.export_to_netcdf(args.output)
    scope = ("illustrative dispatch solved; source citations not independently verified."
             if args.solve_illustrative else
             "no optimization or independent source verification performed.")
    print(f"Exported {len(network.snapshots)} snapshots, {len(network.generators)} "
          f"generators and {len(network.storage_units)} storage units; {scope}")


if __name__ == "__main__":
    main()
