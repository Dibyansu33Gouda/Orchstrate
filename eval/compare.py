"""
Evaluation and comparison script to compare candidate output against sample_output.csv
or ground truth references.
Computes:
1. Case-level deletion status accuracy
2. Step-level count, operation, phase, and field-level match metrics
3. Sequence alignment / order accuracy
"""
import csv
import json
import sys
from pathlib import Path

def evaluate(expected_path: str, candidate_path: str):
    exp_path = Path(expected_path)
    cand_path = Path(candidate_path)
    
    if not exp_path.exists():
        print(f"Expected file {expected_path} not found.")
        return
    if not cand_path.exists():
        print(f"Candidate file {candidate_path} not found.")
        return
        
    with open(exp_path, "r", encoding="utf-8") as f:
        expected = {row["case_id"]: row for row in csv.DictReader(f)}
        
    with open(cand_path, "r", encoding="utf-8") as f:
        candidate = {row["case_id"]: row for row in csv.DictReader(f)}
        
    total_cases = len(expected)
    status_matches = 0
    
    status_by_class = {"COMPLETE": [0, 0], "INCOMPLETE": [0, 0], "NOT_APPLICABLE": [0, 0]}
    
    total_expected_steps = 0
    total_candidate_steps = 0
    step_exact_matches = 0
    step_set_matches = 0
    phase_matches = 0
    op_matches = 0
    
    print("=" * 80)
    print(f"EVALUATION: {cand_path.name} vs {exp_path.name} ({total_cases} cases)")
    print("=" * 80)
    
    for case_id, exp_row in expected.items():
        cand_row = candidate.get(case_id)
        if not cand_row:
            print(f"[MISSING] {case_id} not in candidate")
            continue
            
        exp_status = exp_row["deletion_status"]
        cand_status = cand_row["deletion_status"]
        
        status_by_class[exp_status][1] += 1
        if exp_status == cand_status:
            status_matches += 1
            status_by_class[exp_status][0] += 1
        else:
            print(f"[STATUS MISMATCH] {case_id}: Expected {exp_status}, Got {cand_status}")
            
        exp_steps = json.loads(exp_row["steps_json"])
        cand_steps = json.loads(cand_row["steps_json"])
        
        total_expected_steps += len(exp_steps)
        total_candidate_steps += len(cand_steps)
        
        # Set-based matching
        exp_sigs = {(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"), s.get("state"), s.get("evidence_id")) for s in exp_steps}
        cand_sigs = {(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"), s.get("state"), s.get("evidence_id")) for s in cand_steps}
        step_set_matches += len(exp_sigs.intersection(cand_sigs))
        
        # Compare step details
        min_len = min(len(exp_steps), len(cand_steps))
        for i in range(min_len):
            es = exp_steps[i]
            cs = cand_steps[i]
            if es.get("phase") == cs.get("phase"):
                phase_matches += 1
            if es.get("operation") == cs.get("operation"):
                op_matches += 1
            if (es.get("phase") == cs.get("phase") and 
                es.get("operation") == cs.get("operation") and
                es.get("system_id") == cs.get("system_id") and
                es.get("resource_id") == cs.get("resource_id") and
                es.get("state") == cs.get("state")):
                step_exact_matches += 1
                
    status_acc = (status_matches / total_cases) * 100 if total_cases > 0 else 0
    print("-" * 80)
    print(f"Overall Status Accuracy: {status_matches}/{total_cases} ({status_acc:.1f}%)")
    for st, (corr, tot) in status_by_class.items():
        pct = (corr / tot * 100) if tot > 0 else 0
        print(f"  {st:15s}: {corr:2d}/{tot:2d} ({pct:.1f}%)")
    print("-" * 80)
    print(f"Total Steps: Expected={total_expected_steps}, Candidate={total_candidate_steps}")
    prec = (step_set_matches / total_candidate_steps * 100) if total_candidate_steps else 0
    rec = (step_set_matches / total_expected_steps * 100) if total_expected_steps else 0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0
    print(f"Step Set Matches: {step_set_matches}")
    print(f"  Step Precision: {prec:.1f}%")
    print(f"  Step Recall:    {rec:.1f}%")
    print(f"  Step F1 Score:  {f1:.1f}%")
    print(f"Sequential Step Phase Matches: {phase_matches}/{total_expected_steps} ({(phase_matches/total_expected_steps*100 if total_expected_steps else 0):.1f}%)")
    print(f"Step Operation Matches: {op_matches}/{total_expected_steps} ({(op_matches/total_expected_steps*100 if total_expected_steps else 0):.1f}%)")
    print(f"Step Exact Matches: {step_exact_matches}/{total_expected_steps} ({(step_exact_matches/total_expected_steps*100 if total_expected_steps else 0):.1f}%)")
    print("=" * 80)

    if len(sys.argv) > 3 and sys.argv[3] == "--diff":
        for case_id, exp_row in list(expected.items())[:5]:
            print(f"\n=== CASE {case_id} ===")
            exp_steps = json.loads(exp_row["steps_json"])
            cand_steps = json.loads(candidate.get(case_id, {}).get("steps_json", "[]"))
            print("  EXPECTED STEPS:")
            for s in exp_steps:
                print(f"    [{s.get('phase')}] {s.get('operation')} | sys={s.get('system_id')} res={s.get('resource_id')} st={s.get('state')} ev={s.get('evidence_id')}")
            print("  CANDIDATE STEPS:")
            for s in cand_steps:
                print(f"    [{s.get('phase')}] {s.get('operation')} | sys={s.get('system_id')} res={s.get('resource_id')} st={s.get('state')} ev={s.get('evidence_id')}")

if __name__ == "__main__":
    exp = sys.argv[1] if len(sys.argv) > 1 else "dataset/sample_output.csv"
    cand = sys.argv[2] if len(sys.argv) > 2 else "sample_test_output.csv"
    evaluate(exp, cand)

