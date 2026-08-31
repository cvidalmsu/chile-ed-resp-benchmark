# Checklist final antes de enviar a Data (MDPI)

## A. Publicar la versión DEIS/SADU en GitHub

1. Reemplaza el contenido actual del repositorio por este paquete.
2. Confirma que ya no queden artefactos de versiones experimentales anteriores.
3. Haz `git add -A`, commit y push a `main`.
4. En GitHub abre **Actions -> Build DEIS-SADU dataset -> Run workflow**.
5. Espera a que la acción termine y comprueba que haya creado `data/`, `metadata/` y `results/`.
6. Revisa `results/validation_report.json`: debe mostrar `fail: 0`.
7. Revisa `metadata/hospital_coverage.csv` para conocer exactamente qué hospitales cumplen el umbral de cobertura >= 95%.
8. Revisa `metadata/release_metadata.json` para los conteos exactos de filas, columnas, hospitales y causas de la versión que enviarás.

## B. Release permanente completada

1. Release archivada: `v1.1.0`.
2. DOI específico de la versión: `10.5281/zenodo.22209795`.
3. DOI conceptual para todas las versiones: `10.5281/zenodo.22209794`.
4. Confirma que el registro de Zenodo y el repositorio continúen públicos.
5. Realiza el commit y push final de `main.tex`, `main.pdf`, `README.md`, `CITATION.cff`, `references.bib` y los metadatos actualizados.

## C. Paper

1. Confirma que `main.tex` contiene el DOI definitivo.
2. Confirma los roles CRediT con los siete autores.
3. Compila `main.tex` y `cover_letter.tex`.
4. Verifica que el repositorio y Zenodo sean públicos antes de enviar.
5. En el formulario de MDPI selecciona **Data Descriptor**.
6. En Data Availability, usa el DOI de Zenodo y conserva la atribución a DEIS/SADU.

## D. Licencia

El recurso oficial enlaza **CC BY-NC 2.0**. Los archivos de datos derivados conservan esa licencia. El código se distribuye bajo MIT. No cambies el dataset a CC BY 4.0 ni CC0 sin una revisión jurídica específica del material de origen.
