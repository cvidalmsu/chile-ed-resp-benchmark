# Zenodo deposit required before resubmission

No Zenodo DOI for Chile-ED-Resp v1.1.0 was publicly identifiable when the Reviewer 3 revision was prepared. Do not cite a placeholder as an issued DOI.

## Deposit steps

1. Update the public GitHub repository with the reviewed files.
2. Confirm that the workflow passes, `results/validation_report.json` reports zero failures, and the release data/checksums are present.
3. Create and publish the Git tag and release `v1.1.0`.
4. Archive that exact release in Zenodo using `.zenodo.json` as metadata.
5. Record the version-specific DOI assigned by Zenodo.
6. Run `python scripts/update_doi.py 10.5281/zenodo.XXXXXXXX`.
7. Recompile the manuscript and response letter, then confirm that the DOI resolves to the public v1.1.0 record.

The Reviewer 3 response must not be submitted as fully resolved until this deposit has been published and the issued DOI has replaced the pending status.
