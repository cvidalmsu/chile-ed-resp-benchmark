# Data dictionary

The machine-readable dictionary is `metadata/data_dictionary.csv`.

## Source schema

The official DEIS/SADU Parquet exposes 25 fields after normalized snake-case naming:

`establecimiento_codigo`, `establecimiento_glosa`, `region_codigo`, `region_glosa`,
`comuna_codigo`, `comuna_glosa`, `servicio_salud_codigo`, `servicio_salud_glosa`,
`tipo_establecimiento`, `dependencia_administrativa`, `nivel_atencion`, `tipo_urgencia`,
`latitud`, `longitud`, `nivel_complejidad`, `anio`, `semana_estadistica`, `orden_causa`,
`causa`, `num_total`, `num_menor1anio`, `num1a4anios`, `num5a14anios`,
`num15a64anios`, and `num65o_mas`.

## Curated long table

`data/chile_ed_resp_hospital_long.parquet` preserves official counts for hospital emergency units (UEH) during 2022-2025 and adds only provenance/quality fields. No official count is imputed, smoothed, rescaled, or generated.

## Forecasting table

`data/chile_ed_resp_ira_alta_forecasting.parquet` pivots selected consultation causes to one row per hospital-week and adds deterministic lag, rolling and seasonal features. Missing source observations remain missing.
