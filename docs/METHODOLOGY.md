# Methodology

1. Download the current official DEIS/SADU Parquet from datos.gob.cl.
2. Record retrieval time, byte size and SHA-256 checksum.
3. Normalize column names without changing values.
4. Restrict to 2022-2025, `Hospital`, and hospital emergency units (`UEH`).
5. Preserve all official respiratory consultation and hospitalization cause rows in the long artifact.
6. Parse coordinates only as a type conversion (decimal comma to decimal point).
7. Add provenance and quality-control fields; never overwrite official counts.
8. Build an analysis-ready consultation table by pivoting selected respiratory causes to hospital-week columns.
9. Create deterministic forecasting features (lags, prior rolling means, seasonal sine/cosine, temporal split).
10. Run validation and write checksums, reports and cause inventories.

All released count observations originate in DEIS/SADU. No stochastic augmentation, statistical imputation, smoothing or interpolation of count fields is used.
