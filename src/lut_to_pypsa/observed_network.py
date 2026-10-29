"""Build an observed-capacity PyPSA network only after complete geographic audit.

Generator inventories are inputs, not proof of realistic hourly availability.
"""
import argparse
from pathlib import Path

import pandas as pd

from .capacity_inputs import validate_capacity_inventory
from .hourly import build_load_network, hourly_flat


def build_observed_capacity_network(annual, inventory, mapping, year=2020,
                                    allow_partial=False):
    selected = annual.loc[annual.year == year].copy()
    if selected.empty:
        raise ValueError("No demand for requested year")
    summary, coverage = validate_capacity_inventory(
        inventory, mapping, set(selected.region), year)
    # A mapping hit is not evidence that the inventory covers the whole continent.\n    # Require an explicit completeness attestation for every mapped source region.\n    if not allow_partial:\n        if "complete_lut_region_coverage" not in mapping.columns:\n            raise ValueError("Incomplete geographic coverage: explicit completeness attestation required")\n        flags = mapping.complete_lut_region_coverage.map(\n            lambda value: value is True or str(value).strip().lower() == "true")\n        if not flags.all() or not coverage.capacity_inventory_covered.all():\n            raise ValueError("Incomplete geographic coverage; observed-capacity solve blocked")
    if allow_partial:
        covered = set(coverage.loc[coverage.capacity_inventory_covered, "lut_region"])
        selected = selected[selected.region.isin(covered)]
    if selected.empty:
        raise ValueError("No matched demand regions")
    network = build_load_network(hourly_flat(selected, year))
    for row in summary.itertuples(index=False):
        network.add("Generator",
                    f"observed_{row.lut_region}_{row.technology}",
                    bus=row.lut_region,
                    p_nom=float(row.capacity_mw),
                    marginal_cost=0.0,
                    carrier=str(row.technology))
    # This function intentionally does not solve: capacity alone is insufficient
    # to establish availability, dispatch costs, and network constraints.
    return network, summary, coverage


def run(demand_csv, inventory_csv, mapping_csv, output_dir, year=2020,
        allow_partial=False):
    annual = pd.read_csv(demand_csv)
    inventory = pd.read_csv(inventory_csv)
    mapping = pd.read_csv(mapping_csv)
    network, summary, coverage = build_observed_capacity_network(
        annual, inventory, mapping, year=year, allow_partial=allow_partial)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    network.export_to_netcdf(out / "observed_capacity_unsolved.nc")
    summary.to_csv(out / "mapped_capacity_by_technology.csv", index=False)
    coverage.to_csv(out / "capacity_coverage_audit.csv", index=False)
    return coverage


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("demand_csv")
    parser.add_argument("inventory_csv")
    parser.add_argument("mapping_csv")
    parser.add_argument("--output", default="outputs/observed_capacity")
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    print(run(args.demand_csv, args.inventory_csv, args.mapping_csv,
              args.output, args.year, args.allow_partial).to_string(index=False))
