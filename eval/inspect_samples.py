import csv
import json

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        steps = json.loads(r["steps_json"])
        print(f"{r['case_id']} ({r['deletion_status']}): {len(steps)} steps")
        for s in steps:
            print(f"   {s['phase']} | {s['operation']} | sys={s['system_id']} | res={s['resource_id']} | st={s['state']} | ev={s.get('evidence_id')}")
