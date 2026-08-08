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

The forecasting artifact pivots selected consultation causes into one row per hospital-week and adds only deterministic features: target lags, prior rolling means, seasonal sine/cosine encoding, coverage diagnostics, and a chronological train/test flag (2022-2024 / 2025).

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
│   ├── hospital_coverage.csv        # populated by the pipeline
│   └── SHA256SUMS.txt               # populated by the pipeline
├── results/                         # validation and optional baseline outputs
├── scripts/
│   ├── download_deis.py
│   ├── build_dataset.py
│   ├── validate_dataset.py
│   ├── baseline_example.py
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
pip install -r requirements.txt
pytest -q
python scripts/make_release.py --start-year 2022 --end-year 2025 --force-download
```

## GitHub build

Use **Actions -> Build DEIS-SADU dataset -> Run workflow**. The workflow downloads the official source, builds the curated release, validates it, and commits `data/`, `metadata/`, and `results/` back to `main`.

## Data integrity principles

- All released count observations originate in the official DEIS/SADU source.
- No stochastic augmentation.
- No imputation of official count fields.
- No smoothing or interpolation of official count fields.
- Source row values are retained in the long artifact.
- Derived forecasting features are explicitly labeled and reproducible.
- SHA-256 checksum and retrieval timestamp are recorded for the source snapshot.

## License

- Curated data: **CC BY-NC 2.0**, following the CC BY-NC 2.0 license linked by the official source.
- Code: MIT.
- Original DEIS/SADU records remain attributable to the Chilean Ministry of Health/DEIS and are not relicensed by the authors.

## DOI

Zenodo DOI after the first public release: `10.5281/zenodo.REPLACE_AFTER_RELEASE`.
