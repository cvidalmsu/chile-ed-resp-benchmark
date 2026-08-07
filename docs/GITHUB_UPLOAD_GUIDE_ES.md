# Paso a paso para publicar Chile-ED-Resp en GitHub y obtener un DOI

## 1. Preparar la carpeta

1. Descomprima el ZIP final en una ruta simple, por ejemplo `C:\Investigacion\chile-ed-resp-benchmark`.
2. Abra `main.tex`, `README.md`, `CITATION.cff` y `.zenodo.json`.
3. Reemplace `REPLACE-WITH-USERNAME` por su usuario real de GitHub.
4. No reemplace todavía `REPLACE-AFTER-RELEASE`; ese valor se obtiene desde Zenodo.
5. Ejecute la validación antes de publicar:

```powershell
python scripts\validate_dataset.py --input data\chile_ed_resp_weekly_panel.csv --output-dir results
```

El reporte debe terminar con `"all_checks_passed": true`.

## 2. Crear el repositorio desde la interfaz de GitHub

1. Ingrese a GitHub y pulse **New repository**.
2. Use el nombre `chile-ed-resp-benchmark`.
3. Agregue una descripción breve: `Synthetic weekly benchmark for respiratory emergency-demand forecasting`.
4. Seleccione **Public**. La revista necesita que los datos sean accesibles.
5. No marque `Add a README`, `Add .gitignore` ni `Choose a license`, porque esos archivos ya vienen incluidos.
6. Pulse **Create repository**.

## 3. Subir mediante Git desde Windows PowerShell

Abra PowerShell dentro de la carpeta del proyecto y ejecute:

```powershell
git init
git add .
git commit -m "Release Chile-ED-Resp v1.0.0"
git branch -M main
git remote add origin https://github.com/SU-USUARIO/chile-ed-resp-benchmark.git
git push -u origin main
```

Sustituya `SU-USUARIO` por su usuario real. Cuando GitHub solicite autenticación, use GitHub Desktop, el navegador o un personal access token; la contraseña normal de la cuenta no funciona para `git push` por HTTPS.

## 4. Verificar el repositorio

Compruebe en GitHub que estén visibles:

- `data/chile_ed_resp_weekly_panel.csv.gz`
- `data/metadata.json`
- `docs/data_dictionary.csv`
- `scripts/generate_dataset.py`
- `results/validation_report.json`
- `CITATION.cff`
- las licencias y el README

Abra el CSV comprimido o el CSV principal y confirme que GitHub no haya alterado el archivo. Los hashes se encuentran en `data/SHA256SUMS.txt`.

## 5. Crear la versión v1.0.0

1. Dentro del repositorio, pulse **Releases**.
2. Seleccione **Draft a new release**.
3. En **Choose a tag**, escriba `v1.0.0` y cree la etiqueta sobre `main`.
4. Use el título `Chile-ED-Resp Benchmark v1.0.0`.
5. En la descripción indique: `Initial public release accompanying the Data Descriptor submission.`
6. Pulse **Publish release**.

## 6. Vincular GitHub con Zenodo

GitHub entrega control de versiones, pero no un DOI permanente. Para que el dataset sea citable:

1. Ingrese a Zenodo con su cuenta de GitHub.
2. Autorice la integración con GitHub.
3. En la sección **GitHub**, localice `chile-ed-resp-benchmark` y active el interruptor del repositorio.
4. Si la versión `v1.0.0` se creó antes de activar Zenodo, genere una nueva versión `v1.0.1` o use la opción de sincronización disponible.
5. Zenodo archivará la versión y creará un DOI de versión y un DOI conceptual.

## 7. Incorporar el DOI definitivo

1. Copie el DOI de versión asignado por Zenodo.
2. Reemplace `10.5281/zenodo.REPLACE-AFTER-RELEASE` en `main.tex`, `README.md`, `CITATION.cff`, `.zenodo.json` y `data/metadata.json`.
3. Actualice también la URL de GitHub donde corresponda.
4. Registre los cambios:

```powershell
git add .
git commit -m "Add Zenodo DOI and final repository metadata"
git push
```

5. Cree una nueva versión, preferentemente `v1.0.1`, para que Zenodo archive exactamente los archivos que contienen el DOI.
6. Use el DOI de `v1.0.1` en el manuscrito enviado a *Data*.

## 8. Compilar el proyecto LaTeX

Desde una distribución TeX local:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

En Overleaf, cargue todo el contenido de la carpeta como un proyecto ZIP y compile `main.tex` con pdfLaTeX.

## 9. Revisión previa al envío

Antes de enviar a la revista:

- La URL del dataset debe abrir sin iniciar sesión.
- El DOI debe resolver hacia Zenodo.
- La versión citada en el paper debe coincidir con la versión archivada.
- `all_checks_passed` debe ser `true`.
- La licencia del dataset debe aparecer como CC BY 4.0.
- El manuscrito debe indicar claramente que los datos son sintéticos.
- No deben quedar textos `REPLACE-WITH-USERNAME` o `REPLACE-AFTER-RELEASE`.
- El archivo `main.pdf` debe compilar sin referencias o figuras faltantes.
