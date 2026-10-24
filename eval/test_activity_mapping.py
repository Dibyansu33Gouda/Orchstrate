import csv
from datetime import datetime, timedelta

def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open("dataset/sample_deletion_requests.csv", "r", encoding="utf-8") as f:
    requests = list(csv.DictReader(f))

activities = []
with open("dataset/system_activity.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["target_system"] == "account_service" and r["event_type"] == "DELETE_RECORD":
            activities.append((parse_iso(r["event_time"]), r["resource_id"], r["details"]))

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    expected = {r["case_id"]: r["steps_json"] for r in csv.DictReader(f)}

print(f"Loaded {len(requests)} requests and {len(activities)} account delete activities.")

matches = 0
for req in requests:
    cid = req["case_id"]
    req_at = parse_iso(req["requested_at"])
    rep_at = parse_iso(req["reported_at"])
    
    # Find activity between req_at and rep_at + 1 hour
    cand = []
    for ts, res, det in activities:
        if req_at - timedelta(hours=1) <= ts <= rep_at + timedelta(hours=1):
            cand.append((abs((ts - rep_at).total_seconds()), res, det))
            
    cand.sort()
    chosen_res = cand[0][1] if cand else None
    
    # Check if chosen_res is in expected steps
    exp_steps = expected[cid]
    if chosen_res and chosen_res in exp_steps:
        matches += 1
        print(f"[{cid}] Matched! res={chosen_res}")
    else:
        print(f"[{cid}] Missed! cand={chosen_res} in exp={'Yes' if (chosen_res and chosen_res in exp_steps) else 'No'}")

print(f"Total account matches from system_activity: {matches}/{len(requests)}")
