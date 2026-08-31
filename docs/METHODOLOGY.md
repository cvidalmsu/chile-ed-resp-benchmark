# Methodology

1. Download the current official DEIS/SADU Parquet from datos.gob.cl.
2. Record retrieval time, byte size and SHA-256 checksum.
3. Normalize column names without changing values.
4. Restrict to 2022-2025, `Hospital`, and hospital emergency units (`UEH`).
5. Preserve all official respiratory consultation and hospitalization cause rows in the long artifact.
6. Parse coordinates only as a type conversion (decimal comma to decimal point).
7. Add provenance and quality-control fields; never overwrite official counts.
8. Build an analysis-ready consultation table by pivoting selected respiratory causes to hospital-week columns.
9. Cross all hospitals with the fixed 209-position DEIS statistical-week calendar (52 weeks in 2022--2024 and 53 in 2025), retaining missing records as missing rows and adding a continuous `time_index`.
10. Create deterministic forecasting features (lags, prior rolling means, previous-year same-week value, seasonal sine/cosine, temporal split). Lags use exact preceding grid positions and never skip missing rows. A 4- or 12-week rolling mean is emitted only when all preceding positions in that window are observed. In a 53-week year, week 53 is retained and encoded with a denominator of 53; the same-week previous-year value is missing if the preceding year has no week 53.
11. Preserve establishment metadata at its hospital-week observation rather than propagating a latest record to earlier periods.
12. Run validation and write checksums, reports and cause inventories.

All released count observations originate in DEIS/SADU. No stochastic augmentation, statistical imputation, smoothing or interpolation of count fields is used.

The release writes both `metadata/variable_completeness.csv` and `metadata/forecast_variable_coverage.csv`. The latter reports observed/missing rows and hospital-level completeness for all seven forecasting causes, not only IRA Alta.

The benchmark recommendation uses IRA Alta coverage of at least 95% on the fixed 209-position calendar. This requires at least 199 observed weeks and permits at most 10 missing weeks. The cutoff lies in the observed gap between the least-complete retained hospital (204/209) and the most-complete excluded hospital (178/209), so any threshold in `(178/209, 204/209]` selects the same 178 hospitals. It is a reproducibility convention rather than a clinical criterion; the full 180-hospital grid is retained for alternative sensitivity analyses.

Release reproduction uses Python 3.12.13 and `requirements.lock`, installed with `python -m pip install --require-hashes -r requirements.lock`. This locks the complete direct and transitive dependency graph to exact versions and hashes. `requirements.txt` remains the editable declaration of minimum development requirements.
