# Analytical expectations for 2020 five-region illustrative benchmark

These figures are **algebraic expectations**, computed from the source-cell-traced LUT annual demand CSV and the benchmark's explicit assumptions; **they are not solver results or observed grid metrics**. Flat load uses 8,784 hours in leap year 2020. Illustrative firm supply is 110% of each region's constant peak with marginal cost 50 per MWh; shortage backup has marginal cost 10,000 per MWh. Hence expected shortage is zero and dispatch cost is demand MWh times 50. Monetary units are illustrative, not empirically calibrated euros or dollars.

Run `python -m lut_to_pypsa.five_region_pipeline --year 2020` and compare the solver's CSV against `data/derived/five_region_2020_analytical_expectations.csv`. A successful comparison verifies internal benchmark consistency, **not** real power-system calibration.

Total source annual demand: **22,487.65660944438 TWh**.
