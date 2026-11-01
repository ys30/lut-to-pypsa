"""Reproducible LUT-to-PyPSA input acceptance report.

Compares source-traced annual demand with the actual PyPSA load matrix.
No dispatch is performed and no LUT-ESTM output equivalence is implied.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from .hourly import hourly_flat, build_load_network


def audit_lut_network_inputs(annual, year=2020, tolerance_mwh=0.01):
    required = {"region", "year", "value_twh", "source_cell", "quantity_kind"}
    if not required.issubset(annual.columns):
        raise ValueError(f"Missing source-trace fields: {sorted(required - set(annual.columns))}")
    selected = annual.loc[annual.year.eq(year)].copy()
    if selected.empty:
        raise ValueError("No demand for requested year")
    if selected.source_cell.isna().any() or selected.source_cell.astype(str).str.strip().eq("").any():
        raise ValueError("Missing LUT source cell")
    if not selected.quantity_kind.eq("annual_energy_service_demand").all():
        raise ValueError("Unsupported LUT quantity kind")
    if selected.region.isna().any() or selected.region.astype(str).str.strip().eq("").any():
        raise ValueError("Missing LUT region")
    if selected.region.duplicated().any():
        raise ValueError("Duplicate LUT region-year record")
    if selected.source_cell.duplicated().any():
        raise ValueError("Duplicate LUT source cell")
    demand = pd.to_numeric(selected.value_twh, errors="coerce")
    if demand.isna().any() or not demand.map(
        lambda value: __import__("math").isfinite(value) and value >= 0
    ).all():
        raise ValueError("Invalid LUT annual demand")
    hourly = hourly_flat(annual, year)
    network = build_load_network(hourly)
    expected_hours = len(pd.date_range(
        f"{year}-01-01", f"{year + 1}-01-01", freq="h", inclusive="left"
    ))
    if len(network.snapshots) != expected_hours:
        raise ValueError("Incomplete PyPSA hourly snapshots")
    if len(hourly) != expected_hours * len(selected):
        raise ValueError("Incomplete LUT hourly region coverage")
    if set(network.loads.bus) != set(selected.region):
        raise ValueError("PyPSA load bus coverage mismatch")
    if set(network.loads_t.p_set.columns) != set(network.loads.index):
        raise ValueError("PyPSA load time-series columns mismatch")
    if network.loads_t.p_set.isna().any().any():
        raise ValueError("Missing PyPSA hourly load")
    rows = []
    for item in selected.itertuples(index=False):
        expected = float(item.value_twh) * 1e6
        load_id = "load_" + str(item.region)
        observed = float(network.loads_t.p_set[load_id].sum())
        delta = observed - expected
        rows.append({
            "region": item.region, "year": int(year), "source_cell": item.source_cell,
            "source_twh": float(item.value_twh), "expected_mwh": expected,
            "pypsa_load_mwh": observed, "difference_mwh": delta,
            "within_tolerance": abs(delta) <= tolerance_mwh,
        })
    report = pd.DataFrame(rows)
    if not report.within_tolerance.all():
        raise ValueError("LUT-to-PyPSA annual load energy conservation failed")
    metadata = {
        "year": int(year), "regions": len(report),
        "snapshots": len(network.snapshots),
        "max_abs_error_mwh": float(report.difference_mwh.abs().max()),
        "tolerance_mwh": float(tolerance_mwh),
        "source_quantity": "annual_energy_service_demand",
        "hourly_profile": "flat_assumption",
        "optimization_executed": False,
        "lut_estm_output_equivalence": False,
    }
    return report, metadata


def run(source_csv, output_dir, year=2020):
    report, metadata = audit_lut_network_inputs(pd.read_csv(source_csv), year)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report.to_csv(out / "lut_pypsa_input_conservation.csv", index=False)
    (out / "lut_pypsa_input_manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + chr(10), encoding="utf-8"
    )
    return report, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_csv")
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--output", default="outputs/lut_input_acceptance")
    args = parser.parse_args()
    _, manifest = run(args.source_csv, args.output, args.year)
    print(json.dumps(manifest, indent=2))
