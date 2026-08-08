#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys

def run(*args):
    print("+", " ".join(args))
    subprocess.run(args, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-year", default="2022")
    ap.add_argument("--end-year", default="2025")
    ap.add_argument("--force-download", action="store_true")
    args = ap.parse_args()
    cmd = [sys.executable, "scripts/download_deis.py"]
    if args.force_download: cmd.append("--force")
    run(*cmd)
    run(sys.executable, "scripts/build_dataset.py", "--start-year", args.start_year, "--end-year", args.end_year)
    run(sys.executable, "scripts/validate_dataset.py")
    try:
        run(sys.executable, "scripts/baseline_example.py")
    except subprocess.CalledProcessError:
        print("Baseline example failed or lacked enough complete lag-52 cases; core release remains valid.")

if __name__ == "__main__":
    main()
