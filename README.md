# LUT-to-PyPSA: Energy Demand Scenario Integration and Validation

[![Tests](https://github.com/ys30/lut-to-pypsa/actions/workflows/tests.yml/badge.svg)](https://github.com/ys30/lut-to-pypsa/actions/workflows/tests.yml)

A small, reproducible **electricity-only** portfolio project demonstrating how to validate tabular energy-system data, harmonize units, construct a PyPSA network, and distinguish input checks from optimization results.

> **Data provenance and limitations:** All included data are **synthetic, illustrative LUT-style tables**, not an export from the LUT model. This project **does not demonstrate or claim real LUT–PyPSA data equivalence, model calibration, or cross-model validation**. An actual LUT adapter requires real source files, schema definitions, geographic and temporal semantics, and permission to use them.

## What it does

- Validates required columns, nulls, unique region/generator IDs, valid region references, nonnegative capacities/costs/demand, timestamps, unique region–snapshot pairs, and complete region coverage.
- Converts demand expressed as **GWh per one-hour interval** to PyPSA load `p_set` in **MW** (`GWh × 1000 / 1 hour`). The one-hour assumption is explicit and must be revised for other time resolutions.
- Creates three independent regional buses, six generators and 24 hourly snapshots. **There are no transmission links, storage, capacity-expansion decisions, or multi-sector coupling** in this demonstration.
- Optionally solves dispatch with HiGHS and exports a PyPSA NetCDF network.
- Includes unit tests, a PyPSA integration test, notebooks, and GitHub Actions.

## Installation

Python 3.10+ is required. In a fresh virtual environment:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Run

```bash
# Validate, construct, and export network (no optimization required)
python -m lut_to_pypsa --data data/synthetic --output synthetic_network.nc

# Solve economic dispatch (requires HiGHS, installed via highspy)
python -m lut_to_pypsa --data data/synthetic --output optimized_network.nc --optimize

# Interactive notebooks
jupyter lab
```

Open `notebooks/01_explore_and_validate.ipynb`, then `notebooks/02_build_and_debug.ipynb`.

## Data dictionary

| File | Column | Meaning |
| --- | --- | --- |
| `regions.csv` | `region` | Unique illustrative region ID |
| `generators.csv` | `generator`, `region`, `carrier` | Generator ID, region reference, technology label |
| `generators.csv` | `capacity_mw` | Fixed nameplate capacity, MW |
| `generators.csv` | `marginal_cost_eur_mwh` | Dispatch marginal cost, EUR/MWh |
| `demand.csv` | `timestamp` | UTC hourly interval start, ISO 8601 |
| `demand.csv` | `region` | Region ID |
| `demand.csv` | `demand_gwh` | Electricity consumed during the one-hour interval, GWh |

## Design notes

**Input vs. output:** `n.loads_t.p_set` is a model input. `n.generators_t.p` is a dispatch result and is normally absent before optimization; an empty dispatch table is not a missing-input error.

**Geography:** Region IDs are illustrative and not real geographic boundaries. Each region is electrically isolated, so regional supply must cover regional demand.

**Validation scope:** Tests establish internal consistency of the supplied *synthetic* schema, not physical realism, data lineage, equivalence of LUT and PyPSA concepts, or validity of optimization assumptions.

**Temporal scope:** 24 hourly snapshots on a single synthetic day. Multi-year or investment-period support would require explicit snapshot weights, representative-period definitions, and investment-period handling.

## Adapting to real LUT data

1. Obtain an authorized LUT export and a data dictionary; document units, coordinate systems, timestamps, time zones, regions, sectors, carriers, and aggregation levels.
2. Build a separate, versioned mapping table for LUT entities to PyPSA components and reject unmapped records rather than silently dropping them.
3. Reconcile annual energy versus hourly power, capacity definitions, carrier semantics, and aggregation boundaries. Use interval duration in unit conversions.
4. Add reconciliation reports (row counts, unmatched IDs, regional/annual totals, tolerances, and exceptions).
5. Compare only semantically compatible quantities; do not infer numerical equivalence from matching CSV headers.
6. Validate on a held-out real export and publish only results permitted by its license and data-use terms.

## Project layout

```text
src/lut_to_pypsa/      validation, mapping, PyPSA network construction, CLI
notebooks/             interactive inspection and debugging
data/synthetic/        fully synthetic example CSVs
tests/                 schema and network checks
.github/workflows/     continuous integration
```

## Reproducibility status

The repository is designed to run on GitHub Actions with Python 3.11. A successful CI run is required before treating the full PyPSA build/solve path as verified. Check the workflow status and dependency versions when using this code.

## License

MIT. Synthetic example data are released with the code.
