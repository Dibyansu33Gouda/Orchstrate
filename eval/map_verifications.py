import csv
import json
from pathlib import Path

REPO_ROOT = Path("d:/Orchstrate")
DATASET_DIR = REPO_ROOT / "dataset"

with open(DATASET_DIR / "sample_output.csv", "r", encoding="utf-8") as f:
    sample_output = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

with open(DATASET_DIR / "evidence_files.csv", "r", encoding="utf-8") as f:
    manifest = {r["file_id"]: r for r in csv.DictReader(f)}

# Find evidence files for all verification steps
verif_by_ev = {}
for cid, steps in sample_output.items():
    for s in steps:
        if s["phase"] == "VERIFICATION":
            ev = s.get("evidence_id")
            if ev:
                verif_by_ev.setdefault(ev, []).append((cid, s))

print("Verification steps with evidence_id:")
for ev, list_steps in verif_by_ev.items():
    file_info = manifest.get(ev, {})
    print(f"Evidence {ev} ({file_info.get('file_path')}): {len(list_steps)} steps")
    for cid, s in list_steps[:3]:
        print(f"   [{cid}] {s['system_id']} {s['resource_id']} {s['operation']} {s['state']}")
