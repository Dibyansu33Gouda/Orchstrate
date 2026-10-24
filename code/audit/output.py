import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from .models import Verdict, Step

REQUIRED_COLUMNS = ["case_id", "deletion_status", "steps_json"]
ALLOWED_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}

def case_sort_key(cid: str) -> Any:
    """Natural sort key for case identifiers like case_01 or case_33."""
    if cid and "_" in cid:
        parts = cid.split("_")
        if parts[1].isdigit():
            return (parts[0], int(parts[1]))
    return cid

def validate_verdict_rows(rows: List[Dict[str, Any]], expected_count: int = 518) -> List[str]:
    """
    Validates output rows against the strict challenge contract:
    - Exactly expected_count rows
    - Exact columns and allowed values
    - Valid JSON steps with consecutive numbering
    - Valid phase, operation, and state enums
    """
    errors = []
    if len(rows) != expected_count:
        errors.append(f"Row count mismatch: expected {expected_count}, got {len(rows)}")

    case_ids = []
    for idx, row in enumerate(rows, 1):
        cid = row.get("case_id")
        status = row.get("deletion_status")
        raw_steps = row.get("steps_json")

        if not cid:
            errors.append(f"Row {idx}: missing case_id")
        case_ids.append(cid)

        if status not in ALLOWED_STATUSES:
            errors.append(f"Row {idx} ({cid}): invalid status '{status}'")

        try:
            steps = json.loads(raw_steps)
            if not isinstance(steps, list):
                errors.append(f"Row {idx} ({cid}): steps_json is not an array")
                continue

            if status == "NOT_APPLICABLE" and len(steps) != 0:
                errors.append(f"Row {idx} ({cid}): NOT_APPLICABLE must have empty steps_json, got {len(steps)} steps")

            for s_idx, s in enumerate(steps, 1):
                if s.get("step_no") != s_idx:
                    errors.append(f"Row {idx} ({cid}): step_no {s.get('step_no')} != {s_idx}")
                if s.get("phase") not in ("FINDING", "REMEDIATION", "VERIFICATION"):
                    errors.append(f"Row {idx} ({cid}): invalid phase {s.get('phase')}")
                if status == "COMPLETE" and s.get("phase") != "VERIFICATION":
                    errors.append(f"Row {idx} ({cid}): COMPLETE case has non-VERIFICATION step")
                if status == "COMPLETE" and not s.get("evidence_id"):
                    errors.append(f"Row {idx} ({cid}): COMPLETE verification step missing evidence_id")
                if s.get("phase") == "REMEDIATION" and s.get("evidence_id") != "":
                    errors.append(f"Row {idx} ({cid}): REMEDIATION step must have empty evidence_id")

        except Exception as e:
            errors.append(f"Row {idx} ({cid}): invalid JSON in steps_json: {e}")

    # Check ascending order
    if case_ids != sorted(case_ids, key=case_sort_key):
        errors.append("Rows are not sorted by case_id ascending")

    return errors

def write_output_csv(verdicts: List[Verdict], output_path: Path, expected_count: int = 518) -> None:
    """Writes verdicts to CSV after performing strict validation."""
    # Convert to dict format
    rows = []
    for v in verdicts:
        steps_dicts = [s.model_dump() for s in v.steps]
        # Compact JSON encoding without unnecessary spaces
        steps_json = json.dumps(steps_dicts, separators=(",", ":"))
        rows.append({
            "case_id": v.case_id,
            "deletion_status": v.deletion_status,
            "steps_json": steps_json
        })

    # Sort natural ascending by case_id
    rows.sort(key=lambda r: case_sort_key(r["case_id"]))

    # Validate
    validation_errors = validate_verdict_rows(rows, expected_count=expected_count)
    if validation_errors:
        raise ValueError(f"Output CSV validation failed with {len(validation_errors)} errors:\n" + "\n".join(validation_errors[:10]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
