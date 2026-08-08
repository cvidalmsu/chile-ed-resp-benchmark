#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import requests

SOURCE_URL = "https://datos.gob.cl/dataset/606ef5bb-11d1-475b-b69f-b980da5757f4/resource/ae6c9887-106d-4e98-8875-40bf2b836041/download/at_urg_respiratorio_semanal.parquet"
RESOURCE_ID = "ae6c9887-106d-4e98-8875-40bf2b836041"
DATASET_ID = "606ef5bb-11d1-475b-b69f-b980da5757f4"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def valid_parquet(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 12:
        return False
    with path.open("rb") as f:
        start = f.read(4)
        f.seek(-4, 2)
        end = f.read(4)
    return start == b"PAR1" and end == b"PAR1"

def download_requests(url: str, output: Path, attempts: int = 10) -> None:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 Chile-ED-Resp/1.0 research reproducibility",
        "Accept": "application/octet-stream,*/*",
        "Referer": "https://datos.gob.cl/",
    }
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with session.get(url, headers=headers, stream=True, timeout=(30, 180)) as r:
                r.raise_for_status()
                tmp = output.with_suffix(output.suffix + ".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                tmp.replace(output)
            if valid_parquet(output):
                return
            raise RuntimeError("Downloaded file does not have a valid Parquet signature")
        except Exception as exc:
            last_error = exc
            if output.exists():
                output.unlink()
            time.sleep(min(2 * attempt, 20))
    raise RuntimeError(f"requests download failed after {attempts} attempts: {last_error}")

def download_curl(url: str, output: Path) -> None:
    cmd = ["curl", "-L", "--fail", "--retry", "10", "--retry-all-errors", "--retry-delay", "3",
           "-A", "Mozilla/5.0 Chile-ED-Resp/1.0", "-o", str(output), url]
    subprocess.run(cmd, check=True)
    if not valid_parquet(output):
        raise RuntimeError("curl download completed but file is not valid Parquet")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="raw/at_urg_respiratorio_semanal.parquet")
    ap.add_argument("--manifest", default="metadata/source_manifest.json")
    ap.add_argument("--url", default=SOURCE_URL)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = Path(args.manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    if args.force or not valid_parquet(out):
        try:
            download_requests(args.url, out)
        except Exception as req_error:
            print(f"requests failed: {req_error}; trying curl")
            download_curl(args.url, out)

    info = {
        "source_dataset_title": "Atenciones de urgencias de causas respiratorias por semana epidemiológica",
        "publisher": "Ministerio de Salud de Chile / DEIS",
        "source_system": "Sistema de Atención Diaria de Urgencias (SADU)",
        "dataset_id": DATASET_ID,
        "resource_id": RESOURCE_ID,
        "source_url": args.url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": out.name,
        "source_bytes": out.stat().st_size,
        "source_sha256": sha256(out),
        "source_license": "Creative Commons Non-Commercial (CC BY-NC 2.0 as linked by datos.gob.cl)",
    }
    manifest.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
