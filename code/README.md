# Ghost Data Still Exists: Deletion Audit Agent

An enterprise AI-powered privacy deletion audit system designed for the **HackerRank Orchestrate (October 2026)** challenge.

The agent investigates commerce platform deletion requests against global system evidence (databases, replicas, logs, support tickets, exports, search indexes, backups, and synchronization connectors) to determine whether user personal data was completely deleted or whether ghost data and recreation paths survive.

---

## 1. Architecture Overview

The system implements a **Hybrid Agent + Deterministic Gate** architecture:
- **Identity Graph (`audit/identity.py`)**: Disjoint-set (Union-Find) engine that resolves current and historical user identifiers (emails, phones, user IDs, hashes) from `user_identities.csv` and `user_audit_log.csv`.
- **Multi-System Scanners (`audit/scanners/`)**:
  - `sql_scanner.py`: In-memory SQLite execution engine querying relational and JSON-dump database snapshots.
  - `record_scanner.py`: Recursive nested JSON flattener and text record parser.
  - `log_scanner.py`: Regex boundary scanner with trace ID correlation.
  - `document_scanner.py`: PDF document extractor with caching.
- **Recreation Vector Analyzer (`audit/recreation.py`)**: Discovers active ETL connectors and unblocked backup restoration channels.
- **Rules Engine (`audit/rules.py`)**: Typed policy mapper implementing all 15 rules from `deletion_rules.csv`.
- **Deterministic Gate (`audit/gate.py`)**: Non-bypassable policy enforcer guaranteeing 100% adherence to problem statement rules:
  - Immediate `NOT_APPLICABLE` classification for non-deletion requests.
  - Complete vs. Incomplete status calculation.
  - Strict topological step sorting (`FINDING` < `REMEDIATION` < `VERIFICATION`).
  - Pre-remediation dependency ordering (disabling sync/restore before deleting data).
- **Multi-Provider LLM (`audit/llm.py`)**: Pluggable LLM interface supporting Gemini, OpenAI, Groq, or deterministic zero-dependency fallback, with SHA-256 prompt response caching.
- **Output Validator & Writer (`audit/output.py`)**: Validates and serializes predictions into `output.csv`.

---

## 2. Setup and Installation

### Prerequisites
- Python 3.11 or newer (Python 3.12 recommended)
- Git

### Installation
From the repository root:

```bash
# Optional: create a virtual environment
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration (Optional)
If running with commercial LLM providers, copy `.env.example` to `.env` and set your API key:

```bash
cp .env.example .env
```

Available environment variables:
- `AUDIT_LLM_PROVIDER`: `gemini`, `openai`, `groq`, or `fallback` (default: auto-detected or `fallback`)
- `AUDIT_LLM_MODEL`: Model identifier (e.g., `gemini-1.5-flash`, `gpt-4o-mini`)
- `GEMINI_API_KEY`: Google Gemini API key
- `OPENAI_API_KEY`: OpenAI API key
- `GROQ_API_KEY`: Groq API key

*Note: The system contains full deterministic fallback capability and runs 100% offline without requiring any API keys or network access.*

---

## 3. Running the Audit Pipeline

### Audit Full Evaluation Dataset (518 Requests)
To run the full evaluation dataset and generate `output.csv` at the repository root:

```bash
python code/main.py --input dataset/deletion_requests.csv --output output.csv
```

### Audit Public Sample Cases (32 Cases)
To verify performance on the public sample dataset:

```bash
python code/main.py --sample --output sample_test_output.csv
```

### Additional CLI Flags
- `--limit N`: Audit only the first `N` requests.
- `--mode [hybrid|deterministic]`: Choose execution mode (`hybrid` incorporates LLM reasoning; `deterministic` runs pure rule-based gate).
- `--case case_XXX`: Run audit on a single specific case ID.

---

## 4. Running Tests and Evaluations

### Run All Unit Tests
```bash
python -m unittest discover tests
```

### Compare Against Sample Ground Truth
```bash
python eval/compare.py dataset/sample_output.csv sample_test_output.csv --diff
```

---

## 5. Deliverables and Reports

- `output.csv`: Complete, validated predictions for all 518 evaluation requests.
- `evaluation/evaluation_report.md`: Status accuracy breakdown, step-level metrics, and three custom evaluation cases.
- `evaluation/usage_report.md`: Complete model invocation telemetry, token counts, and cost breakdown.
- `INTERVIEW_NOTES.md`: Comprehensive 30-minute AI judge technical interview preparation guide.
