# DECISIONS.md — Architecture & Engineering Decision Records

Every design decision, alternative considered, and empirical evidence is recorded here to defend in the AI judge technical interview.

---

## Decision 1: Root Workspace Normalization
- **What was decided**: Restructured repository so that `AGENTS.md`, `dataset/`, `code/`, `log.txt`, and final `output.csv` reside directly at the project workspace root (`d:\Orchstrate`).
- **Alternative rejected**: Keeping files nested inside `d:\Orchstrate\repo`.
- **Evidence**: `AGENTS.md` §2 and §6 explicitly require `log.txt` and `output.csv` to be in the same root directory as `AGENTS.md`, and hackerrank evaluator expects `code/` and `output.csv` at the top level.

## Decision 2: Point-in-Time Cutoff Evaluation using `audit_at`
- **What was decided**: Every case uses its own exact `audit_at` field from `deletion_requests.csv` as the reference cutoff date. No call to `datetime.now()` is allowed anywhere in the audit logic.
- **Alternative rejected**: Using a global constant date or the latest timestamp across the corpus.
- **Evidence**: `problem_statement.md` §6.2 explicitly states: *"audit_at is the cutoff for the required answer. Use only information available at or before audit_at when deciding the case. Evidence created later must not change the answer for that case."*

## Decision 3: Deterministic Identification of `NOT_APPLICABLE` Requests
- **What was decided**: Requests that express intent to update account details, export data, or unsubscribe from marketing while explicitly requesting to keep the account active/open (such as cases `case_533` to `case_542`) are classified as `NOT_APPLICABLE` with `steps_json=[]`.
- **Alternative rejected**: Relying on `reported_status` alone or treating all requests as deletion requests.
- **Evidence**: In `system_activity.csv`, activities 3486, 3512, 3531, 3618, 3648, 3659, 3741, 3778, 3789, 3827 explicitly log: *"Privacy intake classified request for account_XXXX as non-deletion; no destructive action was authorized."* These match cases 533-542 exactly. Furthermore, `problem_statement.md` states: *"A request for access, correction, export, marketing opt-out, or another non-deletion action is NOT_APPLICABLE, even if other fields resemble a deletion case."*

## Decision 4: Union-Find Identity Graph for 100% Historical Identifier Resolution
- **What was decided**: Build a Union-Find identity graph connecting `user_id` to current emails, historical emails (from `user_audit_log.csv`), phones (current and historical), and SHA-256 email hashes.
- **Alternative rejected**: Matching requests only against `user_identities.csv`.
- **Evidence**: In `deletion_requests.csv`, 418 requests match current email, and 100 requests match historical email from `user_audit_log.csv`. Without resolving historical emails, 100 cases (19.3% of the dataset) would fail to resolve to any user!

## Decision 5: Canonical Step Ordering Engine
- **What was decided**: Enforce strict deterministic sorting on `steps_json`:
  1. `phase`: `FINDING` (1), `REMEDIATION` (2), `VERIFICATION` (3)
  2. `operation`: strict enum order per `problem_statement.md` Allowed Operations table
  3. `system_id`: alphabetical ascending
  4. `resource_id`: alphabetical ascending
- **Alternative rejected**: Preserving arbitrary discovery order or LLM generation order.
- **Evidence**: Analyzed all 32 cases in `sample_output.csv` against this sorting rule; achieved 0 ordering violations across all 32 reference cases.

## Decision 6: Evidence ID Citation Rules
- **What was decided**:
  - `FINDING` steps in `INCOMPLETE` cases must cite participant-visible `file_id` (e.g. `evidence_54`).
  - `VERIFICATION` steps in `COMPLETE` cases must cite participant-visible `file_id` (proving the state at `audit_at`).
  - `REMEDIATION` and future `VERIFICATION` steps in `INCOMPLETE` cases must use an empty string `""` as `evidence_id`.
- **Alternative rejected**: Reusing finding evidence IDs on proposed remediation/future verification steps.
- **Evidence**: Verified against all 32 cases in `sample_output.csv` and documented in `problem_statement.md` §6.6.

## Decision 7: Multi-modal Attachment Strategy
- **What was decided**: Use `pypdf` to extract text from all 4 PDF documents; use companion metadata and structured system activity events for image screenshots (and flag direct queries to images as `UNSCANNABLE` if image OCR is unavailable).
- **Alternative rejected**: Failing or skipping unparsed media files.
- **Evidence**: Working rules state: *"For media files and attachments (PDF, images), extract text with whatever is installable (pypdf, pytesseract), cache the extraction, and scan it like any other text. If extraction is impossible, record the file as UNSCANNABLE and say so in the output justification instead of ignoring it."*

## Decision 8: Verification Evidence Preloading & Correlation
- **What was decided**: Built a dedicated `VerificationCollector` (`code/audit/verifier.py`) that preloads log trace completions, structured handover reports, and service resource exports, linking subjects to verified absent, present, redacted, anonymized, disabled, and blocked states.
- **Alternative rejected**: Generating generic verification steps without grounding them in the corpus evidence.
- **Evidence**: On `sample_output.csv`, all 10 `COMPLETE` cases cite verified evidence files (`evidence_54`, `evidence_94`, `evidence_56`, `evidence_92`, `evidence_51`). This achieved 100.0% status accuracy (32/32) on the benchmark.

## Decision 9: Exemption of Legally Retained Records from Active Policy Violations
- **What was decided**: The deterministic gate exempts records classified as `RETAIN` or `RETAIN_LEGAL` (under `rule_12` for regulatory security audit logs and `rule_13` for active legal holds) from being counted as active policy violations.
- **Alternative rejected**: Treating all surviving records as violations.
- **Evidence**: In `case_21`, an active legal hold in `legal_retention_register_20260529.pdf` is required by policy to be preserved. When treated as a leak, accuracy was 31/32 (96.9%). When correctly treated as legally retained, accuracy reached 32/32 (100.0%).

## Decision 10: Natural Number Case ID Ordering for Output CSV
- **What was decided**: Implemented `case_sort_key` to sort output rows in natural ascending order (`case_33` through `case_550`).
- **Alternative rejected**: Lexical string sorting (`case_100` before `case_33`).
- **Evidence**: `dataset/deletion_requests.csv` is monotonically ordered by case integer from 33 to 550. Aligning natural order prevents line-by-line mismatch errors in automated evaluation harnesses.

## Decision 11: In-Memory SQLite Engine for Heterogeneous SQL Exports
- **What was decided**: Loaded all 24 SQL database snapshots into transient in-memory SQLite databases to query both relational schemas (`customer_profiles_failover_replica`) and JSON-serialized tables (`customer_data_primary`).
- **Alternative rejected**: Handcrafted regex parsers for SQL text.
- **Evidence**: In-memory SQLite executes queries in <1ms without false positive token splits, handling multi-line INSERT statements and JSON payloads natively.



## Decision 8: Remote Repository Updated to User Repository
- **What was decided**: Updated the git remote `origin` to the user's project repository (`https://github.com/Dibyansu33Gouda/Orchstrate.git`).
- **Alternative rejected**: Keeping remote pointing to the read-only starter repository (`interviewstreet/hackerrank-orchestrate-october26`).
- **Evidence**: Explicit user instruction to bind the workspace to their own repository for code development, version control, and submission.
