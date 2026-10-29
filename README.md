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

## Authentic LUT-DEMAND v1.1 integration (2020–2050)

The repository now includes a **tested real-workbook extractor** at `src/lut_to_pypsa/real_lut.py`. Its source is the official `LUT-DEMAND_v1.1.xlsm` workbook, worksheet `Export power ESD,FED GCML`, section **CONTINENTS** (rows 10–15), parameter **Energy service demand - power sector - electricity**, unit **TWhel**. The five geographic labels are Africa, Asia, Australia / Oceania, Europe, and Americas. This is *annual energy service demand*, not a measured hourly grid load.

To reproduce, download the LUT-DEMAND v1.1 workbook from https://doi.org/10.5281/zenodo.7189337 and place it at `data/external/LUT-DEMAND_v1.1.xlsm` (the original workbook is intentionally not versioned):

```bash
python -m pip install -e '.[dev]'
python -m lut_to_pypsa.real_lut data/external/LUT-DEMAND_v1.1.xlsm --output outputs/lut
python -m pytest -q
```

Outputs include `lut_continent_electricity_annual.csv` (35 source-cell-traced observations, TWh and MWh), `global_reconciliation.csv` (global row versus five continents), and `provenance.json` (workbook SHA-256 and calculation limitations). On the uploaded LUT-DEMAND v1.1 workbook, **35 values were extracted** and the maximum absolute global reconciliation difference was approximately **7.3e-12 TWh**.

**Important limitations:** The extraction reads cached Excel formula results and **does not recalculate formulas, execute macros, or independently verify that cached values reflect a freshly recalculated workbook**. A five-continent sum check is an internal consistency check, **not independent model validation**. No hourly demand shape is supplied by this extraction, and no PyPSA network solve is claimed. Genuine-data tests are skipped in public CI unless the workbook is supplied locally; synthetic regression tests remain available.

Next: document and test an explicitly sourced hourly disaggregation, then create a PyPSA Load import with annual-energy conservation checks. Avoid equating electricity energy service demand with delivered load without a documented modeling assumption.

## Annual LUT ESD → hourly PyPSA Load (flat baseline)

`src/lut_to_pypsa/hourly.py` converts the authentic annual demand CSV into **hourly MW** by dividing annual MWh by the number of hours in the selected year (8,784 in leap year 2020; 8,760 in 2025). This is a deliberately **flat, assumed load profile**, not observed or LUT-provided hourly demand. Interpreting LUT electricity energy-service demand as a PyPSA bus load is also an explicit modeling assumption.

```bash
python -m lut_to_pypsa.hourly outputs/lut/lut_continent_electricity_annual.csv --year 2020 --output outputs/pypsa
```

The command writes `pypsa_loads_flat_2020.csv` (5 regions × 8,784 hours = 43,920 records) and `annual_energy_check_2020.csv`. Annual energy conservation is checked for every region. To build the load-only PyPSA network:

```python
from pathlib import Path
import pandas as pd
from lut_to_pypsa.hourly import build_load_network
loads = pd.read_csv('outputs/pypsa/pypsa_loads_flat_2020.csv', parse_dates=['timestamp'])
network = build_load_network(loads)
network.export_to_netcdf('outputs/pypsa/lut_load_only_2020.nc')
```

**This is a load-only network, not a solved power system.** It has no generators, lines, transmission capacities, emissions, or cost assumptions. Adding those requires separate, appropriately sourced datasets. Run tests from the repository root with `pytest -q`; tests requiring PyPSA are skipped if it is not installed.

## Layer 2: illustrative PyPSA optimization

`src/lut_to_pypsa/benchmark.py` creates one firm generator and one high-penalty shortage generator per region, with no transmission lines. Firm capacity is 110% of flat-profile peak load; assumed marginal costs are 50 and 10,000 currency units/MWh. These are **illustrative assumptions, not LUT outputs or real generation data**.

After preparing authentic hourly loads, run:

```bash
python -m lut_to_pypsa.benchmark outputs/pypsa/pypsa_loads_flat_2020.csv --output outputs/illustrative
```

The script solves PyPSA dispatch with HiGHS and writes `illustrative_dispatch_summary.csv` (demand, generation, shortage and balance residual) and `illustrative_solved_network.nc`. Integration tests need PyPSA and HiGHS. This does not constitute independent LUT-ESTM vs PyPSA model comparison: the supplied LUT-DEMAND workbook contains demand scenarios, not comparable optimized generation, capacity, cost or emissions outputs.
