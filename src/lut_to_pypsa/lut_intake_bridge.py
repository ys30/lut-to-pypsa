"""Bridge LUT flat hourly demand exports to reviewed regional intake.

No generator parameters are fabricated. The returned CSV follows the intake
contract (snapshot,bus,demand_mw) and can be passed to --solve-regional.
"""
import argparse
from pathlib import Path
import pandas as pd


def convert_hourly_loads(hourly, *, region_to_bus=None):
    required = {"timestamp", "region", "p_set_mw"}
    if not required.issubset(hourly):
        raise ValueError("LUT hourly CSV requires timestamp,region,p_set_mw")
    if hourly.empty or hourly[list(required)].isna().any().any():
        raise ValueError("Missing LUT hourly load")
    out = hourly[["timestamp", "region", "p_set_mw"]].copy()
    out["snapshot"] = pd.to_datetime(out.timestamp, utc=True, errors="raise").dt.tz_convert(None)
    out["bus"] = out.region.astype(str)
    if region_to_bus is not None:
        if set(out.bus) != set(region_to_bus):
            raise ValueError("Region-to-bus mapping must cover every LUT region")
        out["bus"] = out.bus.map(region_to_bus)
        if out.bus.isna().any() or len(set(region_to_bus.values())) != len(region_to_bus):
            raise ValueError("Region-to-bus mapping must be one-to-one")
    out["demand_mw"] = pd.to_numeric(out.p_set_mw, errors="raise")
    if not out.demand_mw.notna().all() or not (out.demand_mw >= 0).all():
        raise ValueError("Invalid LUT hourly demand")
    if out.duplicated(["snapshot", "bus"]).any():
        raise ValueError("Duplicate LUT hourly bus demand")
    n_buses = out.bus.nunique()
    if out.groupby("snapshot").bus.nunique().ne(n_buses).any():
        raise ValueError("Incomplete regional coverage at some snapshots")
    return out[["snapshot", "bus", "demand_mw"]].sort_values(["snapshot", "bus"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hourly-lut", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    converted = convert_hourly_loads(pd.read_csv(args.hourly_lut))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    converted.to_csv(args.output, index=False)
    print(f"Exported {len(converted)} hourly bus demand rows across {converted.bus.nunique()} regions")


if __name__ == "__main__":
    main()
