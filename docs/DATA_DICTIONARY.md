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

`data/chile_ed_resp_ira_alta_forecasting.parquet` pivots selected consultation causes to one row per hospital-week on a fixed 209-week calendar and adds deterministic lag, rolling and seasonal features. The `time_index` field is continuous across the 2022--2025 window, while `weeks_in_statistical_year` records the 52/53-week transition.

## Exact cause-to-variable mapping

The following strings are the original source labels retained in `metadata/cause_mapping.csv`.

| `orden_causa` | Original `causa` label | Measure | Forecast field |
|---:|---|---|---|
| 3 | `TOTAL CAUSA SISTEMA  RESPIRATORIO (J00-J98)` | consultation | excluded aggregate |
| 4 | `IRA Alta (J00-J06)` | consultation | `ira_alta` |
| 5 | `Influenza (J09-J11)` | consultation | `influenza` |
| 6 | `Neumonía (J12-J18)` | consultation | `pneumonia` |
| 7 | `Bronquitis/bronquiolitis aguda (J20-J21)` | consultation | `bronchitis_bronchiolitis` |
| 8 | `Crisis obstructiva bronquial (J40-J46)` | consultation | excluded non-target category |
| 9 | `Otra causa respiratoria no contenidas en las categorías anteriores (J22; J30-J39, J47, J60-J98)` | consultation | `other_respiratory` |
| 10 | `TOTAL ATENCIONES POR COVID-19  Virus no Identificado U07.2` | consultation | `covid19_unidentified` |
| 11 | `TOTAL ATENCIONES POR COVID-19, Virus Identificado U07.1` | consultation | `covid19_identified` |
| 33 | `- Causas sistema respiratorio (J00-J98)` | hospitalization | excluded hospitalization |
| 34 | `- Por covid-19, virus no identificado U07.2` | hospitalization | excluded hospitalization |
| 35 | `- Por covid-19, virus identificado U07.1` | hospitalization | excluded hospitalization |

## Mandatory missing/zero interpretation

| Stored value | Meaning |
|---|---|
| `NA` | No qualifying source record was available for the hospital-week-cause combination. |
| `0` | A qualifying official source row explicitly reported zero events. |

These states are not interchangeable. Do not replace `NA` with `0` unless an external reporting model justifies that recoding. The release does not impute missing official counts.

## Lag and rolling behavior when observations are missing

Features are computed after constructing the complete hospital-by-calendar grid and ordering each hospital by `time_index`.

- `ira_alta_lag_k` is the value at the exact grid position `t-k`. If that source position is `NA`, the lag is `NA`; the calculation never substitutes an earlier observed week.
- `ira_alta_rollmean_4` and `ira_alta_rollmean_12` use only the 4 or 12 grid positions preceding `t`. They require all positions in the corresponding window to be observed (`min_periods` equals the window length). Any `NA` in the window produces an `NA` rolling feature.
- Boundary positions without sufficient history remain `NA`.
- `ira_alta_prev_year_same_week` is obtained by matching hospital, statistical year minus one, and the same statistical-week number; it remains `NA` when that prior coordinate is absent.

Consequently, missing observations never compress the time axis or change the calendar interpretation of a lag.

Coverage statistics for every forecasting cause are provided in `metadata/forecast_variable_coverage.csv`.

The seasonal field is named `ira_alta_prev_year_same_week`, because it matches the same official statistical week in the preceding year rather than applying a fixed 52-row shift. If the current record is week 53 and the preceding statistical year has only 52 weeks, this feature is `NA`.

The cyclic seasonal coordinates are

`season_sin = sin(2*pi*(statistical_week-1)/weeks_in_statistical_year)` and
`season_cos = cos(2*pi*(statistical_week-1)/weeks_in_statistical_year)`.

In a 53-week year, week 53 is retained and encoded at angle `2*pi*52/53`, the final unique phase before week 1 of the next year returns to `(0, 1)`. Week 53 is not dropped or duplicated as week 1. The denominator is 52 in 52-week years and 53 in 53-week years, so the same numbered week can have a slightly different normalized annual phase by design.
