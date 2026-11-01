# Empirical technology-parameter intake (Project A only)

**Status:** intake specification; no empirical parameter values have been collected or verified by this file. Do not interpret passing validation as independent source verification.

## Required parameter table

One row per LUT technology. Required columns:
`lut_technology,pypsa_component,capacity_mw,capacity_basis,source_reference,data_year`

Supported adapter components: `Generator`, `StorageUnit`. Provide explicit `marginal_cost_eur_per_mwh` and `availability_fraction` for each row. Storage additionally requires `efficiency`, `efficiency_basis` (`per_direction` or `round_trip`), `max_hours`, and `standing_loss_per_hour`. Do not populate unknown values with zero.

## Evidence table

One row per supplied numerical parameter and technology:
`lut_technology,parameter_name,parameter_value,unit,source_document,source_location,source_year,geographic_scope,evidence_status`.

`source_location` must identify the actual page, table, section or data record, not just a homepage. `source_checked` means a reviewer has checked the value and unit against the source; the code cannot independently certify that check. Record whether the underlying source is observed, modeled, or assumed in accompanying notes. Keep original downloads and their licenses outside the repository if redistribution is restricted.

## Minimum empirical review before solving

1. Identify LUT technology names and exact geographic/year scope. The existing 2020 five-continent LUT demand cannot be described as observed Western-US hourly demand.
2. Verify electrical nameplate capacity in MW; document conversions from thermal capacity or energy units. Do not silently convert Store MWh to MW.
3. Verify marginal-cost currency, price year, and EUR/MWh basis. Record conversion rates and inflation adjustments explicitly; no automatic conversion is performed.
4. Document generator availability as a constant assumption unless independently sourced hourly profiles are provided. A flat annual-demand-to-hourly conversion is not an observed load curve.
5. Document storage charge/discharge efficiency basis, duration, standing-loss period, and whether the data represent installed assets or modeled technologies.
6. Check that each parameter is represented by a matching evidence row, then run `validate_technology_parameters`, `check_parameter_evidence_coverage`, and `attach_reviewed_components(..., empirical=True, evidence=...)`.
7. Run a separate fixed-capacity solve and inspect the solver status, hourly balance, and output units. The current `solve_illustrative_dispatch` supports only single-bus, generator-only networks; it is not a storage or multi-bus empirical solver.

## Reporting boundaries

Do not claim LUT reproduction, empirical calibration, or regional validation solely from a successful synthetic dispatch. Publish provenance, assumptions, coverage gaps, and the input acceptance manifest before reporting comparative results.
