"""Auditable generator-capacity input contract for future observed fleets.

No automatic inference of global coverage from a national inventory.
Only explicit one-to-one geographic mappings are accepted.
"""
import argparse
from pathlib import Path
import pandas as pd


REQUIRED = {"plant_id", "source_region", "technology", "capacity_mw",
            "data_year", "source_dataset", "source_url"}


def validate_capacity_inventory(inventory, mapping, demand_regions, year):
    missing = REQUIRED - set(inventory.columns)
    if missing:
        raise ValueError(f"Missing capacity fields: {sorted(missing)}")
    if not {"source_region", "lut_region"}.issubset(mapping.columns):
        raise ValueError("Mapping requires source_region and lut_region")
    if inventory.empty or mapping.empty:
        raise ValueError("Inventory and mapping must not be empty")
    if inventory[list(REQUIRED)].isna().any().any():
        raise ValueError("Null inventory field")
    if inventory.plant_id.duplicated().any():
        raise ValueError("Duplicate plant_id")
    if mapping.source_region.duplicated().any():
        raise ValueError("Ambiguous geographic mapping")
    capacity = pd.to_numeric(inventory.capacity_mw, errors="raise")
    if not capacity.map(lambda x: 0 <= x < float("inf")).all():
        raise ValueError("Invalid generator capacity")
    if not inventory.data_year.eq(year).all():
        raise ValueError("Inventory year mismatch")
    if not inventory.source_url.astype(str).str.startswith(("https://", "http://")).all():
        raise ValueError("Source URL required for provenance")
    unmatched = set(inventory.source_region) - set(mapping.source_region)
    if unmatched:
        raise ValueError(f"Unmapped source regions: {sorted(unmatched)}")
    unknown = set(mapping.lut_region) - set(demand_regions)
    if unknown:
        raise ValueError(f"Unknown LUT regions: {sorted(unknown)}")
    mapped = inventory.merge(mapping, on="source_region", how="left", validate="many_to_one")
    mapped["capacity_mw"] = pd.to_numeric(mapped.capacity_mw, errors="raise")
    summary = (mapped.groupby(["lut_region", "technology"], as_index=False)
               .agg(capacity_mw=("capacity_mw", "sum"),
                    plant_count=("plant_id", "nunique")))
    covered = set(summary.lut_region)
    expected = set(demand_regions)
    coverage = pd.DataFrame({
        "lut_region": sorted(expected),
        "capacity_inventory_covered": [r in covered for r in sorted(expected)],
    })
    return summary, coverage


def run(inventory_csv, mapping_csv, demand_csv, output_dir, year=2020,
        allow_partial=False):
    demand = pd.read_csv(demand_csv)
    regions = set(demand.loc[demand.year == year, "region"])
    if not regions:
        raise ValueError("No LUT demand regions for year")
    summary, coverage = validate_capacity_inventory(
        pd.read_csv(inventory_csv), pd.read_csv(mapping_csv), regions, year)
    if not allow_partial and not coverage.capacity_inventory_covered.all():
        raise ValueError("Incomplete LUT geographic coverage; pass --allow-partial only for audit")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "mapped_capacity_by_technology.csv", index=False)
    coverage.to_csv(out / "capacity_coverage_audit.csv", index=False)
    return coverage


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("inventory_csv")
    p.add_argument("mapping_csv")
    p.add_argument("demand_csv")
    p.add_argument("--output", default="outputs/capacity_audit")
    p.add_argument("--year", type=int, default=2020)
    p.add_argument("--allow-partial", action="store_true")
    args = p.parse_args()
    print(run(args.inventory_csv, args.mapping_csv, args.demand_csv,
              args.output, args.year, args.allow_partial).to_string(index=False))
