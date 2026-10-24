import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"

class AuditConfig(BaseModel):
    repo_root: Path = REPO_ROOT
    dataset_dir: Path = DATASET_DIR
    evidence_dir: Path = EVIDENCE_DIR
    output_path: Path = REPO_ROOT / "output.csv"
    trace_path: Path = REPO_ROOT / "trace.jsonl"
    
    # LLM Settings
    llm_provider: Literal["gemini", "groq", "openai", "anthropic", "deterministic"] = Field(
        default=os.getenv("AUDIT_LLM_PROVIDER", "gemini") # type: ignore
    )
    llm_model: str = Field(default=os.getenv("AUDIT_LLM_MODEL", "gemini-2.5-flash"))
    max_iterations: int = Field(default=int(os.getenv("AUDIT_MAX_ITERATIONS", "12")))
    mode: Literal["hybrid", "deterministic"] = Field(
        default=os.getenv("AUDIT_MODE", "hybrid") # type: ignore
    )
    
    # Tool settings
    evidence_context_lines: int = 5
    temperature: float = 0.0

DEFAULT_CONFIG = AuditConfig()
