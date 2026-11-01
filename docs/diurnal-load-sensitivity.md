# Synthetic diurnal-load sensitivity: design and interpretation

The authentic LUT-DEMAND v1.1 fixture supplies **annual energy-service demand** by continent for 2020, not measured hourly load. This experiment constructs an explicitly **synthetic** 24-hour demand pattern to test the sensitivity of a PyPSA dispatch benchmark to temporal shape while preserving each continent's original annual total.

## Construction

For each region with annual demand `E` MWh and year with `H` hours, the flat baseline is `P_flat = E/H` MW. For hour of day `h`, the synthetic profile is

`P(h) = P_flat × [1 + a × cos(2π(h − 18)/24)]`

where `a` is a dimensionless amplitude, initially `0.20`. The resulting profile peaks at 18:00 and reaches its minimum at 06:00. For a complete 2020 leap year, 366 repetitions of a full 24-hour cycle sum to zero for the cosine term, so annual energy is conserved independently for every continent. The implementation checks this numerically.

At `a=0.20`, the peak and trough are respectively 120% and 80% of the flat baseline. This is a **demonstration shape**, not a measured or empirically fitted regional profile; all five regions currently share the same shape and local-clock interpretation is not established.

## What this does and does not establish

- Validates time-index construction, nonnegative hourly demand, and annual energy conservation.
- Creates a controlled counterfactual for later comparing flat and diurnal dispatch under identical supply assumptions.
- Does **not** by itself establish that any diurnal PyPSA dispatch experiment has been run or verified.
- Does **not** support inference about historical hourly demand, observed unmet load, region-specific demand peaks, storage value, transmission adequacy, or real electricity reliability.

## Next experiment

Solve both load shapes with identical illustrative generator capacities, reserve margins, costs, and the same 8,784 snapshots. Compare peak MW, total shortage-proxy MWh, fraction of hours with positive shortage, dispatch cost in illustrative units, and the regional annual-energy conservation audit. Because the generator is constrained by its hourly nameplate, a diurnal profile can produce shortages during peak hours even when annual firm capacity appears sufficient.

Publish any numerical claims **only after** a CI-verified PyPSA solve, with the synthetic scenario labels attached.
