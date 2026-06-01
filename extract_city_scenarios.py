"""
extract_city_scenarios.py

Usage:
    python extract_city_scenarios.py <city> <amount> <train_folder>

Example:
    python extract_city_scenarios.py austin 500 "D:/argoverse2/train"

Scans all scenario subfolders in <train_folder>, finds scenarios matching
<city>, and copies up to <amount> of them into a new folder named
"<city>_scenarios" next to the train folder.
"""

import sys
import shutil
import pandas as pd
from pathlib import Path


def find_parquet(scenario_dir: Path):
    try:
        return next(scenario_dir.glob("*.parquet"))
    except StopIteration:
        return None


def get_city(parquet_path: Path) -> str | None:
    try:
        df = pd.read_parquet(parquet_path, columns=["city"])
        return df["city"].iloc[0]
    except Exception:
        return None


def main():
    if len(sys.argv) != 4:
        print("Usage: python extract_city_scenarios.py <city> <amount> <train_folder>")
        print('Example: python extract_city_scenarios.py austin 500 "D:/argoverse2/train"')
        sys.exit(1)

    city_filter = sys.argv[1].lower()
    amount = int(sys.argv[2])
    train_folder = Path(sys.argv[3])

    if not train_folder.exists():
        print(f"Error: folder not found: {train_folder}")
        sys.exit(1)

    output_folder = train_folder.parent / f"{city_filter}_scenarios"
    output_folder.mkdir(exist_ok=True)
    print(f"Output folder: {output_folder}")

    scenario_dirs = sorted([p for p in train_folder.iterdir() if p.is_dir()])
    total = len(scenario_dirs)
    print(f"Found {total} scenario folders. Scanning for city='{city_filter}'.../n")

    copied = 0
    scanned = 0

    for scenario_dir in scenario_dirs:
        if copied >= amount:
            break

        scanned += 1
        parquet = find_parquet(scenario_dir)
        if parquet is None:
            continue

        city = get_city(parquet)
        if city and city.lower() == city_filter:
            dest = output_folder / scenario_dir.name
            if not dest.exists():
                shutil.copytree(scenario_dir, dest)
            copied += 1
            print(f"[{copied}/{amount}] Copied: {scenario_dir.name}")

        # Progress every 1000 scanned
        if scanned % 1000 == 0:
            print(f"  ... scanned {scanned}/{total}, copied {copied} so far")

    print(f"/nDone! Copied {copied} '{city_filter}' scenarios to:/n  {output_folder}")


if __name__ == "__main__":
    main()
