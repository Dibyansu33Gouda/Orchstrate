"""
Prototype verification collector to inspect how well we extract verification steps
matching sample_output.csv.
"""
import re
import json
import csv
from pathlib import Path

REPO_ROOT = Path("d:/Orchstrate")
DATASET_DIR = REPO_ROOT / "dataset"

# Load manifest
manifest = {}
with open(DATASET_DIR / "evidence_files.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        manifest[row["file_id"]] = row

print(f"Loaded {len(manifest)} manifest entries")
