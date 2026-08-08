#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

FILES = [Path('main.tex'), Path('README.md'), Path('CITATION.cff'), Path('.zenodo.json')]
PLACEHOLDER = '10.5281/zenodo.REPLACE-AFTER-RELEASE'

def main():
    ap = argparse.ArgumentParser(description='Replace the Zenodo DOI placeholder in publication metadata.')
    ap.add_argument('doi', help='Version DOI, e.g. 10.5281/zenodo.12345678')
    args = ap.parse_args()
    if not args.doi.startswith('10.') or '/' not in args.doi:
        raise SystemExit('The DOI does not look valid.')
    changed = []
    for path in FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8')
        if PLACEHOLDER in text:
            path.write_text(text.replace(PLACEHOLDER, args.doi), encoding='utf-8')
            changed.append(str(path))
    print('Updated:', ', '.join(changed) if changed else 'no placeholder found')

if __name__ == '__main__':
    main()
