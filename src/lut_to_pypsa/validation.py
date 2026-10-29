"""Input validation, independent of PyPSA optimization results."""
import pandas as pd

class InputValidationError(ValueError):
    pass

def _require(condition, message):
    if not condition:
        raise InputValidationError(message)

def validate_inputs(regions, generators, demand):
    """Validate a synthetic, intentionally narrow electricity-only schema."""
    for name, table, columns in [
        ("regions", regions, ["region"]),
        ("generators", generators, ["generator", "region", "carrier", "capacity_mw", "marginal_cost_eur_mwh"]),
        ("demand", demand, ["timestamp", "region", "demand_gwh"]),
    ]:
        _require(set(columns).issubset(table.columns), f"{name}: missing columns {sorted(set(columns)-set(table.columns))}")
        _require(not table.empty, f"{name}: table is empty")
        _require(not table[columns].isna().any().any(), f"{name}: null required values")
    _require(regions.region.is_unique, "Duplicate regions")
    _require(generators.generator.is_unique, "Duplicate generator names")
    known = set(regions.region)
    _require(set(generators.region).issubset(known), "Generator references unknown region")
    _require(set(demand.region).issubset(known), "Demand references unknown region")
    for col in ["capacity_mw", "marginal_cost_eur_mwh"]:
        values = pd.to_numeric(generators[col], errors="coerce")
        _require(values.notna().all() and (values >= 0).all(), f"Invalid {col}")
    values = pd.to_numeric(demand.demand_gwh, errors="coerce")
    _require(values.notna().all() and (values >= 0).all(), "Invalid demand_gwh")
    timestamps = pd.to_datetime(demand.timestamp, errors="coerce", utc=True)
    _require(timestamps.notna().all(), "Invalid timestamps")
    _require(not pd.MultiIndex.from_arrays([timestamps, demand.region]).duplicated().any(), "Duplicate (timestamp, region) demand")
    _require(demand.groupby("timestamp").region.nunique().eq(len(known)).all(), "Incomplete region coverage per snapshot")
    return {"regions": len(regions), "generators": len(generators), "snapshots": timestamps.nunique(), "demand_rows": len(demand)}
