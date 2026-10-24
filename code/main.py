import sys
import argparse
from pathlib import Path

# Add project root and code directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
code_dir = REPO_ROOT / "code"
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from audit.config import AuditConfig
from audit.tools import AuditToolbox
from audit.gate import DeterministicGate
from audit.llm import get_llm_provider
from audit.agent import AuditAgent
from audit.output import write_output_csv, validate_verdict_rows
from audit.loaders import load_csv_rows

def main() -> None:
    parser = argparse.ArgumentParser(description="HackerRank Orchestrate: Deletion Audit Agent")
    parser.add_argument("--input", type=str, default=str(REPO_ROOT / "dataset" / "deletion_requests.csv"), help="Path to input CSV")
    parser.add_argument("--output", type=str, default=str(REPO_ROOT / "output.csv"), help="Path to output CSV")
    parser.add_argument("--mode", type=str, choices=["hybrid", "deterministic"], default="hybrid", help="Audit mode")
    parser.add_argument("--limit", type=int, default=None, help="Optional row processing limit")
    parser.add_argument("--sample", action="store_true", help="Run against sample_deletion_requests.csv")

    args = parser.parse_args()

    input_path = Path(args.input)
    if args.sample:
        input_path = REPO_ROOT / "dataset" / "sample_deletion_requests.csv"

    output_path = Path(args.output)
    config = AuditConfig(mode=args.mode)

    print(f"==================================================")
    print(f"Starting Deletion Audit Pipeline")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Mode:   {args.mode}")
    print(f"==================================================")

    # Initialize components
    toolbox = AuditToolbox(config.dataset_dir)
    gate = DeterministicGate(toolbox.rules_engine, config.dataset_dir, toolbox.manifest)
    llm = get_llm_provider(preferred_provider=config.llm_provider, model_name=config.llm_model)
    agent = AuditAgent(toolbox, gate, llm, max_iterations=config.max_iterations, trace_file=config.trace_path)

    requests = load_csv_rows(input_path)
    if args.limit:
        requests = requests[:args.limit]

    total = len(requests)
    print(f"Loaded {total} requests to audit.")

    verdicts = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, r in enumerate(requests, 1):
        cid = r["case_id"]
        v = agent.run_case(cid)
        verdicts.append(v)
        status_counts[v.deletion_status] = status_counts.get(v.deletion_status, 0) + 1
        if idx % 50 == 0 or idx == total:
            print(f"Progress: [{idx}/{total}] - Last: {cid} -> {v.deletion_status} ({len(v.steps)} steps)")

    print(f"\nAudit complete! Status counts: {status_counts}")
    
    # Write and validate output
    expected_rows = total
    write_output_csv(verdicts, output_path, expected_count=expected_rows)
    print(f"Successfully generated and validated {output_path} ({len(verdicts)} rows).")

if __name__ == "__main__":
    main()
