import re
import json
import csv
import sys
from pathlib import Path
sys.path.insert(0, ".")
from eval.test_verification_engine import parse_log_traces

REPO_ROOT = Path("d:/Orchstrate")
DATASET_DIR = REPO_ROOT / "dataset"

# Load sample requests
with open(DATASET_DIR / "sample_deletion_requests.csv", "r", encoding="utf-8") as f:
    sample_requests = list(csv.DictReader(f))

# Load users
user_by_email = {}
with open(DATASET_DIR / "user_identities.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        user_by_email[r["email"].lower()] = r["user_id"]

with open(DATASET_DIR / "user_audit_log.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["field_name"] == "email":
            user_by_email[r["old_value"].lower()] = r["user_id"]
            user_by_email[r["new_value"].lower()] = r["user_id"]

# Load sample output expected accounts
with open(DATASET_DIR / "sample_output.csv", "r", encoding="utf-8") as f:
    expected_acc = {}
    for r in csv.DictReader(f):
        steps = json.loads(r["steps_json"])
        for s in steps:
            if s["system_id"] == "account_service":
                expected_acc[r["case_id"]] = s["resource_id"]
                break

# Build evidence map for accounts
account_from_handover = {}
rec_dir = DATASET_DIR / "evidence" / "records"
for f in rec_dir.glob("customer_account_handover_*.txt"):
    with open(f, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6 and parts[1] == "account_service":
                account_from_handover[parts[5].lower()] = parts[2]

account_from_logs = {}
logs_dir = DATASET_DIR / "evidence" / "logs"
for f in logs_dir.glob("*.log"):
    traces = parse_log_traces(f)
    for t in traces:
        if t["system"] == "account_service":
            account_from_logs[t["subject"].lower()] = t["resource_id"]

# Evaluate match rate
correct = 0
total = len(sample_requests)

for req in sample_requests:
    cid = req["case_id"]
    em = req["email"].lower()
    uid = user_by_email.get(em, "")
    
    # Resolve
    res = account_from_handover.get(em) or account_from_logs.get(em) or account_from_logs.get(uid.lower())
    if not res:
        # Fallback to padded user_id
        num = uid.split("_")[1]
        if len(num) <= 2:
            res = f"account_{int(num):03d}"
        else:
            res = f"account_{num}"
            
    exp = expected_acc.get(cid)
    if res == exp:
        correct += 1
        print(f"[{cid}] MATCH: {res}")
    else:
        print(f"[{cid}] MISMATCH: got {res}, expected {exp} (em={em}, uid={uid})")

print(f"\nAccount Resource ID Accuracy: {correct}/{total} ({(correct/total*100):.1f}%)")
