"""Build an observed-capacity PyPSA network only after complete geographic audit.

Generator inventories are inputs, not proof of realistic hourly availability.
"""
import argparse
import json
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
    # A mapping hit is not evidence that the inventory covers the whole continent.
    # Require an explicit completeness attestation for every mapped source region.
    if not allow_partial:
        if "complete_lut_region_coverage" not in mapping.columns:
            raise ValueError("Incomplete geographic coverage: explicit completeness attestation required")
        flags = mapping.complete_lut_region_coverage.map(
            lambda value: value is True or str(value).strip().lower() == "true")
        if not flags.all() or not coverage.capacity_inventory_covered.all():
            raise ValueError("Incomplete geographic coverage; observed-capacity solve blocked")
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
    manifest = {
        "model": "lut-to-pypsa-observed-capacity-import",
        "year": int(year),
        "optimization_executed": False,
        "calibrated": False,
        "complete_geographic_coverage_attested": not allow_partial,
        "partial_geography_allowed": bool(allow_partial),
        "source_inventory_rows": int(len(inventory)),
        "mapped_generator_capacity_mw": float(summary.capacity_mw.sum()),
        "modeled_regions": sorted(map(str, network.buses.index)),
        "demand_regions": sorted(map(str, annual.loc[annual.year == year, "region"])),
        "inventory_covered_regions": sorted(
            map(str, coverage.loc[coverage.capacity_inventory_covered, "lut_region"])
        ),
        "hourly_load_shape": "flat_assumption",
        "generator_availability": "not_established",
        "generator_marginal_cost": "placeholder_zero_not_for_optimization",
        "transmission_topology": "not_established",
        "lut_estm_output_equivalence": False,
    }
    (out / "network_scope_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
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
