"""
Packaging script for HackerRank Orchestrate: Ghost Data Still Exists.
Packages code.zip conforming strictly to AGENTS.md §6.8 and §6.9:
- Includes runnable code, prompts, configs, README.md, and evaluation reports.
- Strictly excludes dataset/, virtual environments, __pycache__, caches, logs, and secrets.
"""
import zipfile
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
ZIP_OUTPUT = REPO_ROOT / "code.zip"

EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    ".git",
    ".llm_cache",
    "dataset",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
    ".log",
    ".tmp",
}

EXCLUDE_FILES = {
    ".env",
    "output.csv",
    "sample_test_output.csv",
    "trace.jsonl",
}

def package() -> None:
    print(f"Creating submission archive: {ZIP_OUTPUT.name}...")
    
    # Ensure requirements.txt and .env.example are in code/
    for fname in ["requirements.txt", ".env.example"]:
        src = REPO_ROOT / fname
        dst = CODE_DIR / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            
    # Also copy evaluation reports to code/evaluation/ if needed
    eval_dir = CODE_DIR / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    
    packaged_files = []
    
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in CODE_DIR.rglob("*"):
            if file_path.is_dir():
                continue
            # Check exclusions
            parts = set(file_path.parts)
            if any(d in parts for d in EXCLUDE_DIRS):
                continue
            if file_path.suffix.lower() in EXCLUDE_EXTS:
                continue
            if file_path.name in EXCLUDE_FILES:
                continue
                
            arcname = file_path.relative_to(REPO_ROOT).as_posix()
            zipf.write(file_path, arcname=arcname)
            packaged_files.append(arcname)
            
    print(f"Successfully packaged {len(packaged_files)} files into {ZIP_OUTPUT.name} ({ZIP_OUTPUT.stat().st_size / 1024:.1f} KB).")
    print("Files included:")
    for f in sorted(packaged_files):
        print(f"  + {f}")

if __name__ == "__main__":
    package()
