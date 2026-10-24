import csv
import json

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    sample_rows = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

with open("dataset/sample_deletion_requests.csv", "r", encoding="utf-8") as f:
    requests = {r["case_id"]: r["email"] for r in csv.DictReader(f)}

with open("dataset/user_identities.csv", "r", encoding="utf-8") as f:
    users = {r["email"]: r["user_id"] for r in csv.DictReader(f)}

with open("dataset/user_audit_log.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["field_name"] == "email":
            users[r["old_value"]] = r["user_id"]
            users[r["new_value"]] = r["user_id"]

for cid, steps in sample_rows.items():
    req_email = requests.get(cid)
    uid = users.get(req_email)
    for s in steps:
        if s["system_id"] == "account_service":
            print(f"{cid}: req_email={req_email} -> uid={uid} | account_res={s['resource_id']}")
