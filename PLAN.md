# Implementation Plan: Deletion Audit Agent (Ghost Data Still Exists)

## Phase 0: Reconnaissance & Environment Grounding (COMPLETED)
- [x] Cloned challenge repo, organized workspace root at `d:\Orchstrate`.
- [x] Established AGENTS.md compliant logging protocol in `log.txt`.
- [x] Read and analyzed all 9 CSV files, 94 evidence files (24 SQL, 29 JSON/txt, 26 log, 4 PDF, 11 PNG).
- [x] Produced comprehensive `DATA_NOTES.md` and initial `DECISIONS.md`.
- [x] Identified 10 non-deletion requests (`case_533` to `case_542`) needing `NOT_APPLICABLE`.
- [x] Extracted text from all 4 PDFs using `pypdf`.
- [x] Formulated Open Questions for user alignment.

## Phase 1: Core Domain Models & Ingestion Layer
- [ ] `code/audit/config.py`: Centralized configuration (paths, model name, caps, cutoff dates, timeouts).
- [ ] `code/audit/models.py`: Pydantic v2 schemas (`Request`, `IdentityCluster`, `Finding`, `RuleDecision`, `Vector`, `Step`, `Verdict`).
- [ ] `code/audit/normalize.py`: Robust identifier normalization (lowercase, trim, strip Gmail dots/+tags, E.164 phone formatting, unicode fold, SHA-256/SHA-1/MD5 generation, partial mask detection).
- [ ] `code/audit/identity.py`: Union-Find identity graph connecting `user_id`, current emails, historical emails, phones, and email hashes with full link provenance.
- [ ] `code/audit/loaders.py`: Encoding-safe loaders (UTF-8, UTF-8-BOM, CP1252 fallbacks) for CSV, JSON, Log, and SQL dumps.
- [ ] `code/audit/rules.py`: Typed rule engine parsing `deletion_rules.csv` mapping categories and conditions to actions.
- [ ] Unit tests for Phase 1 components in `tests/test_phase1.py`.

## Phase 2: Evidence Scanners & Recreation Analyzer
- [ ] `code/audit/scanners/base.py`: Base scanner interface returning `list[Finding]`.
- [ ] `code/audit/scanners/sql_scanner.py`: Scanner for all 24 SQL database dumps (detecting replication drift, ghost account rows, orphaned search documents, and unredacted tombstones).
- [ ] `code/audit/scanners/record_scanner.py`: Scanner for JSON snapshot bundles, connector configs, exports, and audit ledgers.
- [ ] `code/audit/scanners/log_scanner.py`: Scanner for service events, support replica logs, readback logs, and audit traces.
- [ ] `code/audit/scanners/document_scanner.py`: Scanner for extracted PDF text (delivery correction attachments, statements, registers).
- [ ] `code/audit/recreation.py`: Directed sync/ETL graph analyzer identifying live vs. dormant vectors and restore risks.
- [ ] Unit tests for Phase 2 components in `tests/test_phase2.py`.

## Phase 3: Deterministic Gate & Step Ordering
- [ ] `code/audit/gate.py`: Invariant enforcement computing deterministic status (`NOT_APPLICABLE`, `INCOMPLETE`, `COMPLETE`) that LLM cannot override.
- [ ] `code/audit/output.py`: Strict CSV writer and schema validator enforcing exact columns `case_id,deletion_status,steps_json`, consecutive step numbering from 1, and canonical sort order.
- [ ] Verification against all 32 reference cases in `dataset/sample_output.csv`.

## Phase 4: Hybrid Agent Loop & LLM Provider
- [ ] `code/audit/llm.py`: Thin provider interface supporting Gemini, Groq, Anthropic, or OpenAI with automatic key discovery and deterministic fallback.
- [ ] `code/audit/tools.py`: Deterministic tools (`get_request`, `expand_identifiers`, `list_systems`, `scan_system`, `read_evidence`, `lookup_rules`, `analyze_recreation`, `adjudicate_match`, `submit_verdict`).
- [ ] `code/audit/prompts.py`: Hardened system prompts enforcing untrusted data boundaries and output schemas.
- [ ] `code/audit/agent.py`: Tool-calling loop with 12-iteration hard cap, caching, retry logic, and fallback.

## Phase 5: CLI, Packaging & Evaluation Reports
- [ ] `code/main.py`: CLI entrypoint accepting `--input` and `--output`.
- [ ] `eval/compare.py`: Diff evaluation comparing agent mode vs. deterministic fallback mode.
- [ ] `code/evaluation/evaluation_report.md` & `code/evaluation/usage_report.md`: Hackathon evaluation reports.
- [ ] `scripts/package.sh`: Packaging script for clean `code.zip`.

## Phase 6: Interview Preparation & Final Validation
- [ ] `INTERVIEW_NOTES.md`: Honest technical defense for AI judge interview.
- [ ] Full 518-case audit execution and validation.

