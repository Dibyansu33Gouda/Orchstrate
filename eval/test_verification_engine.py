"""
Verification evidence engine prototype.
Maps all verification proofs from logs, records, and exports.
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

def parse_log_traces(log_path: Path):
    """Parses log files and maps traces linking subjects to resource completions."""
    traces = {}
    completed = []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # Check JSON line
            if "{" in line and "}" in line:
                try:
                    s_idx = line.find("{")
                    e_idx = line.rfind("}")
                    data = json.loads(line[s_idx:e_idx+1])
                    tr = data.get("trace_id")
                    ev = data.get("event", "")
                    svc = data.get("service") or data.get("logger")
                    subj = data.get("subject_ref") or data.get("lookup_key") or data.get("subject_key")
                    res = data.get("resource_id")
                    rows = str(data.get("rows", ""))
                    status = str(data.get("http_status", ""))
                    if tr and subj and "_started" in ev:
                        traces[tr] = (subj, svc)
                    elif tr and res and "_completed" in ev:
                        completed.append((tr, res, svc, rows, status, data))
                except Exception:
                    pass
            else:
                # Text log line (key=value)
                matches = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', line)
                cleaned = {m[0]: (m[1] if m[1] != "" else m[2]) for m in matches}
                tr = cleaned.get("trace_id")
                ev = cleaned.get("event", "")
                svc = cleaned.get("service")
                subj = cleaned.get("lookup_key") or cleaned.get("subject_ref") or cleaned.get("subject_key")
                res = cleaned.get("resource_id")
                rows = cleaned.get("rows", "")
                status = cleaned.get("http_status", "")
                if tr and subj and "_started" in ev:
                    traces[tr] = (subj, svc)
                elif tr and res and "_completed" in ev:
                    completed.append((tr, res, svc, rows, status, cleaned))
                    
    results = []
    for tr, res, svc, rows, status, raw in completed:
        if tr in traces:
            subj, start_svc = traces[tr]
            results.append({
                "trace_id": tr,
                "subject": subj,
                "system": svc or start_svc,
                "resource_id": res,
                "rows": rows,
                "status": status,
                "raw": raw
            })
    return results

# Test on resource_lookup_trace_20260926_103856.log
log_p = DATASET_DIR / "evidence" / "logs" / "resource_lookup_trace_20260926_103856.log"
res = parse_log_traces(log_p)
print(f"Extracted {len(res)} trace completions from {log_p.name}")
for r in res[:5]:
    print("  ", r)
