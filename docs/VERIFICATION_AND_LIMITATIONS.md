# Project A — verification and interpretation record

Last reviewed: 2026-11-01. Repository: `ys30/lut-to-pypsa`.

## Verified engineering scope

- **Input provenance:** source-cell-traced 2020 annual electricity energy-service-demand fixture for five continents; the original LUT workbook is not redistributed. The input acceptance audit checks annual energy conservation.
- **Temporal translation:** 8,784 hourly snapshots for leap year 2020. The flat and cosine diurnal profiles are **assumptions**, not observed electricity load.
- **Optimization:** illustrative independent-region PyPSA dispatch with HiGHS; firm and shortage generators, no transmission, storage, investment optimization or sector coupling.
- **Quality gates:** unit tests, LUT input/parameter acceptance, PyPSA integration, and five-region annual acceptance all passed at commit `9eb75518`. [Five-region acceptance](https://github.com/ys30/lut-to-pypsa/actions/runs/41400565389).
- **Reproducible figures:** the acceptance workflow checks four expected PNG outputs, including the six-scenario amplitude × phase chart. The README includes a versioned SVG based on the verified rounded scenario totals.

## Latest verified release baseline

- **Commit:** `061ceef3` (README documents the automated figure consistency gate).
- **Four CI checks passed:** [five-region annual acceptance #41401811304](https://github.com/ys30/lut-to-pypsa/actions/runs/41401811304), [tests #41401811269](https://github.com/ys30/lut-to-pypsa/actions/runs/41401811269), [PyPSA integration #41401811249](https://github.com/ys30/lut-to-pypsa/actions/runs/41401811249), and [LUT input/parameter acceptance #41401811247](https://github.com/ys30/lut-to-pypsa/actions/runs/41401811247).
- **Figure reproducibility gate:** the acceptance workflow regenerates the six-scenario CSV, validates all six cases against the versioned SVG metadata within 0.0005 TWh, and renders four PNG figures. This is a numerical-data consistency check; it does not pixel-compare the plotted SVG geometry to its metadata.
- **Maintenance rule:** any change to the synthetic dispatch assumptions or the six-scenario numerical results requires updating the versioned SVG, rerunning the complete acceptance workflow, and revising the README interpretation.

## Main controlled numerical result

With the same annual demand and installed firm capacity, an assumed 90% firm-capacity factor, 20% synthetic demand amplitude, and 40% synthetic availability dip:

| Supply availability trough | Shortage proxy (TWh) |
| --- | ---: |
| 06:00 | 4,677.433 |
| 18:00 | 5,579.834 |

The aligned-minus-opposite difference is **+902.402 TWh**. The 3 × 2 demand-amplitude/phase experiment and full-year audit are recorded in [CI run #41392582624](https://github.com/ys30/lut-to-pypsa/actions/runs/41392582624).

## Scientific interpretation gates

1. **Not an empirical reliability study.** The shortage variable is a modeled high-cost generator output, not observed unserved energy or outage events.
2. **Not calibrated.** Installed capacities, costs, diurnal load and firm availability are imposed assumptions. No measured hourly load, generation, network topology or operational validation is included.
3. **Do not interpret the initial −24.44% comparison causally.** That comparison also changed installed firm capacity. Fixed-nameplate controls remove this confound.
4. **Conditional timing sensitivity.** The +902.402 TWh effect is specific to the synthetic supply-demand phase alignment and capacity regime. It is not a transferable prediction for actual grids.
5. **Not LUT-ESTM equivalence.** Source-traced annual demand is not evidence that LUT technology mix, sector coupling, costs or optimized outputs have been reproduced.

## Completion boundary

**Engineering demonstration:** verified and portfolio-ready under the above limitations.

**Empirical energy-system research:** not complete. Requires documented real regional hourly demand and supply, calibrated capacities/costs, appropriate transmission/storage modeling, and external validation before real-world reliability or policy conclusions.

**Downstream reuse:** the five-continent LUT fixture is not a Western-US load dataset. Any Project B/C handoff requires an independently documented geography and physical-demand mapping.
