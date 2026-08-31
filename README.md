# Chile-ED-Resp

**A curated and reproducible weekly hospital dataset for respiratory emergency-demand forecasting in Chile**

Repository: https://github.com/cvidalmsu/chile-ed-resp-benchmark

## Purpose

Chile-ED-Resp provides a reproducible curation pipeline and analysis-ready release derived from **official DEIS/SADU weekly respiratory emergency records**. Official count fields are preserved; the forecasting artifact adds only deterministic features computed from prior observations and calendar position.

## Official source

- Publisher: Ministerio de Salud de Chile / Departamento de Estadísticas e Información de Salud (DEIS)
- System: Sistema de Atención Diaria de Urgencias (SADU)
- Dataset: *Atenciones de urgencias de causas respiratorias por semana epidemiológica*
- Resource ID: `ae6c9887-106d-4e98-8875-40bf2b836041`
- Official resource: https://datos.gob.cl/dataset/atenciones-de-urgencia-causas-respiratorias
- Source license linked by the portal: CC BY-NC 2.0

## Release scope

The curated release uses the closed period **2022-2025** and keeps official records for:

- establishments classified as `Hospital`;
- hospital emergency units (`Urgencia Hospitalaria (UEH)`);
- all respiratory consultation and hospitalization causes available in the source;
- total counts and the five official age strata.

The forecasting artifact pivots selected consultation causes into one row per hospital-week on a fixed 209-position DEIS statistical-week calendar and adds only deterministic features: a continuous time index, target lags, prior rolling means, a previous-year same-week field, seasonal sine/cosine encoding, coverage diagnostics, and a chronological train/test flag (2022-2024 / 2025). Precomputed target-derived fields are intended for rolling-origin one-week-ahead evaluation; fixed-origin multi-week forecasts must construct their future predictors recursively.

## Repository structure

```text
.
├── main.tex                         # Data (MDPI) Data Descriptor
├── main.pdf                         # verified compiled manuscript
├── cover_letter.tex
├── cover_letter.pdf                 # verified one-page cover letter
├── references.bib
├── Definitions/                     # MDPI LaTeX class/assets
├── data/                            # curated DEIS/SADU release (after workflow)
├── raw/README.md                    # raw official file is not committed
├── metadata/
│   ├── data_dictionary.csv
│   ├── source_manifest.json         # generated
│   ├── release_metadata.json        # generated
│   ├── causes.csv                   # populated by the pipeline
│   ├── cause_mapping.csv             # cause-to-feature audit
│   ├── filter_audit.csv              # row counts after each filter
│   ├── variable_completeness.csv     # missing and explicit-zero counts
│   ├── forecast_variable_coverage.csv # coverage for every forecasting cause
│   ├── target_summary.csv            # IRA Alta distribution by year
│   ├── temporal_summary.csv          # national week-level summaries
│   ├── hospital_coverage.csv        # populated by the pipeline
│   └── SHA256SUMS.txt               # populated by the pipeline
├── results/                         # validation and rolling-origin outputs
├── scripts/
│   ├── download_deis.py
│   ├── build_dataset.py
│   ├── validate_dataset.py
│   ├── rolling_origin_example.py
│   ├── make_release.py
│   └── update_doi.py
├── tests/
├── docs/
└── .github/workflows/build-deis-sadu-dataset.yml
```

## Local build

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.lock
pytest -q
python scripts/make_release.py --start-year 2022 --end-year 2025 --force-download
```

The reproducible build uses Python 3.12.13. For day-to-day dependency development, maintainers may instead install the minimum constraints:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` is the editable declaration of minimum development requirements. GitHub Actions and archival release reproduction use `requirements.lock`, which fixes all direct and transitive packages to exact versions and verifies their hashes.

## GitHub build

Use **Actions -> Build DEIS-SADU dataset -> Run workflow**. The workflow downloads the official source, builds the curated release, validates it, and commits `data/`, `metadata/`, and `results/` back to `main`.

## Missing observation versus true zero

> **Mandatory interpretation rule:** `NA` means that no qualifying source record was available for the hospital-week-cause combination. `0` means that a qualifying official source row explicitly reported zero events. Do not replace `NA` with `0` unless an external reporting model justifies that recoding.

Lag and rolling fields are computed only after each hospital has been crossed with the complete 209-position calendar. A lag therefore references the exact prior grid position and never skips over an `NA`. A rolling mean is returned only when every value in the preceding 4- or 12-position window is observed; otherwise the rolling feature is `NA`.

## Data integrity principles

- All released count observations originate in the official DEIS/SADU source.
- No stochastic augmentation.
- No imputation of official count fields.
- No smoothing or interpolation of official count fields.
- Source row values are retained in the long artifact.
- Derived forecasting features are explicitly labeled and reproducible.
- Explicit source zeros remain zero, while absent hospital-week-cause records remain missing.
- `scripts/rolling_origin_example.py` recomputes predictors at every one-week-ahead forecast origin without reading the precomputed lag columns.
- SHA-256 checksum and retrieval timestamp are recorded for the source snapshot.

## License

- Curated data: **CC BY-NC 2.0**, following the license linked by the official source.
- Non-commercial redistribution and adaptation are permitted when the redistributor credits the Chilean Ministry of Health/DEIS, identifies Chile-ED-Resp as a transformation, links the official source and the CC BY-NC 2.0 license, identifies further changes, preserves license notices, and does not impose additional legal or technical restrictions.
- Use primarily intended for commercial advantage or private monetary compensation requires separate permission from the applicable rights holder.
- Code: MIT. The MIT license applies only to software and does not override the data license.
- Original DEIS/SADU records are not relicensed by the authors. See `LICENSE-DATA` for the redistribution checklist and authoritative license link.

## DOI

Version 1.1.0 is permanently archived in Zenodo:

- Version-specific DOI: [10.5281/zenodo.22209795](https://doi.org/10.5281/zenodo.22209795)
- All-versions concept DOI: [10.5281/zenodo.22209794](https://doi.org/10.5281/zenodo.22209794)

Use the version-specific DOI when citing the exact dataset release analyzed in the manuscript.
