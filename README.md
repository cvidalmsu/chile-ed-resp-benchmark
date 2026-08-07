# Chile-ED-Resp Benchmark

**Version:** 1.0.0  
**Status:** Complete synthetic dataset package prepared for a *Data* (MDPI) Data Descriptor submission.

Chile-ED-Resp is a deterministic synthetic weekly panel for respiratory emergency-demand forecasting. It contains 1,728 hospital-week records: nine artificial hospital profiles, each observed for 192 epidemiological weeks from 2022-W01 through 2025-W36.

> **Important:** Every observation is synthetic. The files do not report real hospital or patient activity and must not be used for clinical, epidemiological, staffing, procurement, or policy decisions.

## Repository structure

```text
.
├── main.tex
├── references.bib
├── cover_letter.tex
├── Definitions/                 # MDPI LaTeX class and assets
├── data/
│   ├── chile_ed_resp_weekly_panel.csv
│   ├── chile_ed_resp_weekly_panel.csv.gz
│   ├── reference_hospital_features.csv
│   ├── metadata.json
│   └── SHA256SUMS.txt
├── docs/
│   ├── data_dictionary.csv
│   ├── DATA_DICTIONARY.md
│   └── GITHUB_UPLOAD_GUIDE_ES.md
├── scripts/
│   ├── generate_dataset.py
│   ├── validate_dataset.py
│   ├── baseline_forecasting.py
│   ├── reproduce_figures.py
│   └── build_real_deis_panel.py
├── results/
├── figures/
├── CITATION.cff
├── LICENSE-DATA
├── LICENSE-CODE
├── requirements.txt
└── .zenodo.json
```

## Quick reproduction

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/generate_dataset.py --output-dir data
python scripts/validate_dataset.py --input data/chile_ed_resp_weekly_panel.csv --output-dir results
python scripts/baseline_forecasting.py --input data/chile_ed_resp_weekly_panel.csv --output-dir results
python scripts/reproduce_figures.py --data data/chile_ed_resp_weekly_panel.csv --metrics results/baseline_metrics.csv --predictions results/baseline_predictions.csv --output-dir figures
```

## Compile the manuscript

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Dataset files

- `chile_ed_resp_weekly_panel.csv`: main 1,728-row panel.
- `reference_hospital_features.csv`: H09 features with lags and rolling means.
- `metadata.json`: machine-readable release metadata.
- `SHA256SUMS.txt`: integrity hashes.

## Licenses

- Dataset and documentation: CC BY 4.0.
- Code: MIT License.
- The optional `build_real_deis_panel.py` script downloads an external official source. Any output generated from that source inherits the source portal's current licensing terms and is not part of the bundled synthetic dataset.

## Before journal submission

1. Replace `REPLACE-WITH-USERNAME` in `main.tex`, `CITATION.cff`, `.zenodo.json`, and this README.
2. Upload the repository to GitHub.
3. Create release `v1.0.0`.
4. Archive the release in Zenodo and obtain a DOI.
5. Replace the placeholder DOI in all metadata files and recompile the manuscript.
6. Verify that the repository and Zenodo record are public before submitting to *Data*.

Detailed instructions are available in `docs/GITHUB_UPLOAD_GUIDE_ES.md`.
