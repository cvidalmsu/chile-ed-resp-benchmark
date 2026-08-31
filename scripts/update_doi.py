#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
from pathlib import Path

MAIN = Path("main.tex")
README = Path("README.md")
CITATION = Path("CITATION.cff")


def replace_or_fail(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not locate the expected {label} text; update the script or file manually.")
    return text.replace(old, new, 1)

def main():
    ap = argparse.ArgumentParser(description='Replace the Zenodo DOI placeholder in publication metadata.')
    ap.add_argument('doi', help='Version DOI, e.g. 10.5281/zenodo.12345678')
    args = ap.parse_args()
    if not args.doi.startswith('10.') or '/' not in args.doi:
        raise SystemExit('The DOI does not look valid.')
    doi_url = f"https://doi.org/{args.doi}"

    main_text = MAIN.read_text(encoding="utf-8")
    if args.doi not in main_text:
        main_text = replace_or_fail(
            main_text,
            "Publisher/location: GitHub. Repository: \\url{\\dataseturl}.}",
            f"Publisher/location: GitHub. Repository: \\url{{\\dataseturl}}. Permanent archive: \\url{{{doi_url}}}.}}",
            "dataset metadata",
        )
        main_text = replace_or_fail(
            main_text,
            "GitHub repository at \\url{\\dataseturl}. Version 1.1.0",
            f"GitHub repository at \\url{{\\dataseturl}} and the permanent Version 1.1.0 archive at \\url{{{doi_url}}}. Version 1.1.0",
            "Data Availability Statement",
        )
        MAIN.write_text(main_text, encoding="utf-8")

    readme_text = README.read_text(encoding="utf-8")
    readme_text = re.sub(
        r"## DOI\n\n.*?(?=\n## |\Z)",
        f"## DOI\n\nVersion-specific Zenodo DOI: [{args.doi}]({doi_url}).\n",
        readme_text,
        flags=re.DOTALL,
    )
    README.write_text(readme_text, encoding="utf-8")

    citation_text = CITATION.read_text(encoding="utf-8")
    if re.search(r"^doi:", citation_text, flags=re.MULTILINE):
        citation_text = re.sub(r"^doi:.*$", f"doi: {args.doi}", citation_text, flags=re.MULTILINE)
    else:
        citation_text = citation_text.replace("version: 1.1.0\n", f"version: 1.1.0\ndoi: {args.doi}\n", 1)
    CITATION.write_text(citation_text, encoding="utf-8")

    print("Updated:", MAIN, README, CITATION)

if __name__ == '__main__':
    main()
