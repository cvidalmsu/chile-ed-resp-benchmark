# Actualización del repositorio GitHub con la versión DEIS/SADU

Repositorio objetivo: `https://github.com/cvidalmsu/chile-ed-resp-benchmark`

## 1. Actualizar el contenido del repositorio

Antes de subir esta revisión, elimina los artefactos de datos de versiones experimentales anteriores (`data/`, `results/`, `figures/` y cualquier script `generate_dataset.py`). El paquete nuevo está estructurado como la versión reproducible basada exclusivamente en DEIS/SADU.

Desde una copia local del repositorio:

```bash
git clone https://github.com/cvidalmsu/chile-ed-resp-benchmark.git
cd chile-ed-resp-benchmark
```

Copia sobre esa carpeta **todo** el contenido del ZIP nuevo y luego:

```bash
git add -A
git commit -m "Publish curated DEIS/SADU reproducible pipeline"
git push origin main
```

## 2. Generar el dataset real dentro de GitHub

1. Abre el repositorio en GitHub.
2. Entra a **Actions**.
3. Selecciona **Build DEIS-SADU dataset**.
4. Pulsa **Run workflow** y confirma la rama `main`.
5. El flujo descargará el Parquet oficial, construirá los archivos 2022-2025, ejecutará validaciones y hará un commit automático de `data/`, `metadata/` y `results/`.

El archivo raw oficial no se guarda en Git; se registra su URL, fecha de descarga, tamaño y SHA-256 en `metadata/source_manifest.json`.

## 3. Revisar antes del release

Verifica que existan:

- `data/chile_ed_resp_hospital_long.parquet`
- `data/chile_ed_resp_hospital_long.csv.gz`
- `data/chile_ed_resp_ira_alta_forecasting.parquet`
- `data/chile_ed_resp_ira_alta_forecasting.csv`
- `metadata/release_metadata.json`
- `metadata/source_manifest.json`
- `metadata/SHA256SUMS.txt`
- `results/validation_report.json`
- `results/validation_checks.csv`

Comprueba que `validation_report.json` tenga `fail: 0`.

## 4. Crear release y DOI

1. GitHub -> **Releases** -> **Draft a new release**.
2. Tag: `v1.0.0`.
3. Título: `Chile-ED-Resp v1.0.0 - curated DEIS/SADU release`.
4. Publica el release.
5. Vincula el repositorio con Zenodo y archiva el release.
6. Sustituye `10.5281/zenodo.REPLACE_AFTER_RELEASE` en `main.tex`, `README.md`, `CITATION.cff` y `.zenodo.json` por el DOI real.
7. Recompila el paper y confirma que GitHub y Zenodo sean públicos antes de enviar a *Data*.

## 5. Importante sobre licencia

El portal oficial informa una licencia Creative Commons Non-Commercial. Por ello, el dataset derivado se distribuye como **CC BY-NC 2.0**. El código permanece bajo MIT.

## 6. Reemplazo automático del DOI

Cuando Zenodo entregue el DOI de versión, puedes actualizar los metadatos principales con:

```bash
python scripts/update_doi.py 10.5281/zenodo.XXXXXXXX
```

Después recompila el paper y realiza un commit final.
