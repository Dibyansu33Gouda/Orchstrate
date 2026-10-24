"""
Evaluation Entry Point for HackerRank Orchestrate: Ghost Data Still Exists.
Executes benchmark comparison on public samples and outputs evaluation metrics.
"""
import sys
import subprocess
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    compare_script = repo_root / "eval" / "compare.py"
    sample_expected = repo_root / "dataset" / "sample_output.csv"
    sample_candidate = repo_root / "sample_test_output.csv"
    
    if not sample_candidate.exists():
        print("Generating candidate sample output...")
        subprocess.run([sys.executable, str(repo_root / "code" / "main.py"), "--sample", "--output", str(sample_candidate)], check=True)
        
    print(f"Running evaluation against {sample_expected.name}...")
    subprocess.run([sys.executable, str(compare_script), str(sample_expected), str(sample_candidate)], check=True)

if __name__ == "__main__":
    main()
