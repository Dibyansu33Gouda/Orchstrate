# DATA_NOTES.md — HackerRank Orchestrate (Ghost Data Still Exists)
Reconnaissance Date: October 2026 (Phase 0 Reconnaissance)
Target Repository: `d:\Orchstrate`

---

## 1. Schema of Each CSV, Sample Rows, and Column Definitions

### 1.1 `dataset/deletion_requests.csv` (518 rows)
- **Purpose**: Evaluation dataset containing the deletion requests to audit.
- **Header**: `case_id,email,requested_at,reported_status,reported_at,audit_at,request_text`
- **Sample Rows**:
  1. `case_33,ingrid.dahl@outlook.com,2026-07-16T08:00:00Z,COMPLETE,2026-07-18T02:00:00Z,2026-07-19T13:00:00Z,"Please close my account and process the associated personal-data deletion. Please handle any copies that fall within the scope of the deletion request. Please confirm when the review is complete."`
  2. `case_34,haruka.s1838@zoho.com,2026-09-24T08:00:00Z,COMPLETE,2026-09-26T02:00:00Z,2026-09-27T13:00:00Z,"I would like the account associated with this address to be erased. Please handle any copies that fall within the scope of the deletion request. Please contact me if you need information to verify the request."`
  3. `case_35,g.silva76@gmail.com,2026-08-30T03:00:00Z,NOT_STARTED,2026-08-31T21:00:00Z,2026-09-02T08:00:00Z,"Please close my account and process the associated personal-data deletion. Please check the records connected to the account before confirming completion. Please contact me if you need information to verify the request."`
- **Column Meanings**:
  - `case_id`: Unique string identifier for the case (e.g. `case_33`).
  - `email`: Email address provided with the request (may be current or historical).
  - `requested_at`: ISO-8601 UTC timestamp when the user submitted the request.
  - `reported_status`: Internal system claim (`COMPLETE`, `PARTIALLY_COMPLETE`, `NOT_STARTED`).
  - `reported_at`: ISO-8601 UTC timestamp when the system claim was recorded.
  - `audit_at`: ISO-8601 UTC cutoff timestamp for the audit evaluation.
  - `request_text`: Multilingual free-form user message expressing user intent.

### 1.2 `dataset/sample_deletion_requests.csv` (32 rows)
- **Purpose**: 32 public training/reference cases accompanied by ground truth in `sample_output.csv`.
- **Header**: `case_id,email,requested_at,reported_status,reported_at,audit_at,request_text`
- **Sample Rows**:
  1. `case_01,amina.elmasri@gmail.com,2026-08-18T09:14:00Z,COMPLETE,2026-08-20T16:42:00Z,2026-09-03T11:30:00Z,"Hi, I haven’t used this account in years and would like it closed. Please remove the profile and the personal details attached to it."`
  2. `case_02,mateo.rios@outlook.com,2026-08-21T18:06:00Z,PARTIALLY_COMPLETE,2026-08-22T07:25:00Z,2026-09-04T15:00:00Z,"Intenté eliminar mi cuenta ayer, pero la página terminó mostrando un error. ¿Pueden comprobar si todavía queda algún dato y completar la eliminación si hace falta?"`
  3. `case_03,l.fontaine46@yahoo.com,2026-09-13T11:00:00Z,COMPLETE,2026-09-15T11:00:00Z,2026-09-26T11:00:00Z,"Je demande la suppression définitive du compte associé à cette adresse e-mail. Veuillez examiner les identifiants actuels et antérieurs conformément à votre procédure de confidentialité. Merci de confirmer le résultat une fois la vérification terminée."`

### 1.3 `dataset/sample_output.csv` (32 rows)
- **Purpose**: Canonical expected output for the 32 sample cases.
- **Header**: `case_id,deletion_status,steps_json`
- **Sample Rows**:
  1. `case_01,COMPLETE,"[{""evidence_id"":""evidence_54"",""operation"":""VERIFY_RECORD_ABSENT"",""phase"":""VERIFICATION"",""resource_id"":""account_001"",""state"":""ABSENT"",""step_no"":1,""system_id"":""account_service""}]"`
  2. `case_02,COMPLETE,"[{""evidence_id"":""evidence_54"",""operation"":""VERIFY_RECORD_ABSENT"",""phase"":""VERIFICATION"",""resource_id"":""account_002"",""state"":""ABSENT"",""step_no"":1,""system_id"":""account_service""}]"`
  3. `case_03,COMPLETE,"[{""step_no"":1,""phase"":""VERIFICATION"",""system_id"":""account_service"",""resource_id"":""account_7566"",""operation"":""VERIFY_RECORD_ABSENT"",""state"":""ABSENT"",""evidence_id"":""evidence_94""},{""step_no"":2,""phase"":""VERIFICATION"",""system_id"":""security_service"",""resource_id"":""audit_record_2016"",""operation"":""VERIFY_RECORD_PRESENT"",""state"":""PRESENT"",""evidence_id"":""evidence_94""},{""step_no"":3,""phase"":""VERIFICATION"",""system_id"":""analytics_platform"",""resource_id"":""analytics_9406"",""operation"":""VERIFY_RECORD_ANONYMIZED"",""state"":""ANONYMIZED"",""evidence_id"":""evidence_94""}]"`
- **Column Meanings**:
  - `case_id`: Must match the input `case_id`.
  - `deletion_status`: Exact enum: `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
  - `steps_json`: JSON-serialized array of step objects, ordered strictly by phase, operation, system_id, resource_id.

### 1.4 `dataset/output.csv` (0 rows, header template)
- **Header**: `case_id,deletion_status,steps_json`
- **Purpose**: Blank template at dataset level; final evaluated submission file must be written to root `./output.csv`.

### 1.5 `dataset/deletion_rules.csv` (15 rows)
- **Purpose**: Policy mapping data categories to required actions and legal retention rules.
- **Header**: `rule_id,data_category,condition,required_action`
- **Sample Rows**:
  1. `rule_01,USER_PROFILE,Always,DELETE`
  2. `rule_02,SECONDARY_IDENTIFIER,Always,DELETE`
  3. `rule_03,SEARCH_INDEX_ENTRY,Always,DELETE`
- **Column Meanings**:
  - `rule_id`: Identifier for the policy rule (`rule_01` to `rule_15`).
  - `data_category`: Target data type (e.g., `USER_PROFILE`, `SUPPORT_MESSAGE`, `SECURITY_AUDIT_LOG`, `ACCOUNT_TOMBSTONE`).
  - `condition`: Logical condition for rule applicability (e.g., "Always", "Record is within the supplied retention period").
  - `required_action`: Policy action: `DELETE`, `REDACT`, `ANONYMIZE`, `RETAIN`.

### 1.6 `dataset/evidence_files.csv` (94 rows)
- **Purpose**: Manifest of all evidence artifacts located under `dataset/evidence/`.
- **Header**: `file_id,file_path,origin,captured_at`
- **Sample Rows**:
  1. `evidence_01,evidence/logs/service_events_ap_south_20260915.log,central_observability_export,2026-09-15T11:59:39Z`
  2. `evidence_02,evidence/records/customer_data_snapshot_bundle_20260917.json,records_assurance_snapshot_bundle,2026-09-17T12:00:00Z`
  3. `evidence_03,evidence/records/customer_account_handover_20261001.txt,customer_account_service,2026-10-01T12:00:00Z`
- **Column Meanings**:
  - `file_id`: Unique ID (`evidence_01` to `evidence_94`) cited in `steps_json`.
  - `file_path`: Relative path under `dataset/`.
  - `origin`: Logical system or export process that produced the artifact.
  - `captured_at`: Timestamp when the artifact was captured.

### 1.7 `dataset/user_identities.csv` (850 rows)
- **Purpose**: Current identity snapshot for all known platform users (`user_01` to `user_850`).
- **Header**: `user_id,name,email,phone,email_hash,updated_at`
- **Sample Rows**:
  1. `user_01,Amina El-Masri,amina.elmasri@gmail.com,+971 50 482 7316,d4e1f59abcf9a1e0cfdc7c27ad6c07ed4ff88b326a16ed5eed5ec6bc31618c93,2026-05-28T04:03:00Z`
  2. `user_02,Mateo Ríos,mateo.rios@outlook.com,+34 612 847 593,fad1c282b6b8ff346ee92e617331f69c2b6bb345af954eeb44581c57529eab9d,2026-04-24T07:44:00Z`
  3. `user_03,Oliver Bennett,oliver-bennett@gmail.com,+1 (202) 555-0103,1fa7764c96e40e8570cbb7569f707f6d84c593cecbe5c1ed2b0a07a624dba039,2026-03-14T14:21:00Z`
- **Column Meanings**:
  - `user_id`: Stable primary user key (`user_XX`).
  - `name`: Full name string.
  - `email`: Current registered email.
  - `phone`: E.164 formatted international phone number.
  - `email_hash`: SHA-256 hash (64 hex characters) of `email`.
  - `updated_at`: Last snapshot update timestamp.

### 1.8 `dataset/user_audit_log.csv` (306 rows)
- **Purpose**: Historical identity change ledger.
- **Header**: `audit_id,user_id,event_time,field_name,old_value,new_value`
- **Sample Rows**:
  1. `audit_01,user_485,2024-12-14T16:31:44Z,phone,+33 6 24 34 80 16,+33 6 63 29 68 28`
  2. `audit_02,user_505,2024-12-25T00:51:04Z,phone,+81 90 6278 6936,+81 90 7870 0272`
  3. `audit_03,user_525,2025-01-04T00:11:24Z,phone,+46 70 144 08 06,+46 70 808 74 05`
- **Column Meanings**:
  - `audit_id`: Audit row ID (`audit_01` to `audit_306`).
  - `user_id`: References `user_identities.user_id`.
  - `event_time`: Timestamp when identifier was updated.
  - `field_name`: Field changed (`email`, `email_hash`, `phone`).
  - `old_value`: Historical identifier prior to change.
  - `new_value`: Resulting identifier (matches `user_identities.csv`).

### 1.9 `dataset/system_activity.csv` (4,011 rows)
- **Purpose**: Global chronological stream of platform events.
- **Header**: `activity_id,event_time,event_type,source_system,target_system,resource_id,reported_result,details`
- **Sample Rows**:
  1. `activity_01,2026-01-04T14:56:29Z,INDEX_RECORD,account_service,search_service,search_9729,SUCCESS,Customer search-index refresh processed search_9729.`
  2. `activity_02,2026-01-04T16:08:26Z,INDEX_RECORD,account_service,search_service,search_6919,SUCCESS,Customer search-index refresh processed search_6919.`
  3. `activity_03,2026-01-04T17:14:03Z,INDEX_RECORD,account_service,search_service,search_4613,SUCCESS,Customer search-index refresh processed search_4613.`

---

## 2. Encoding of "No Deletion Requested" & Distinct Status Values

### 2.1 How "No Deletion Requested" is Encoded
- **In `deletion_requests.csv`**:
  - It is **NOT** indicated by a blank column or a special flag.
  - The `reported_status` column can say `NOT_STARTED` (e.g. cases 533-542).
  - The true classification comes from semantic evaluation of `request_text`.
  - When `request_text` requests an export/download, marketing opt-out, invoice copy, or account update while explicitly stating intent to keep the account active or not delete records:
    - Example 1 (`case_533`): *"The mobile number on my profile is out of date. Please replace it with the new one and leave the account active."*
    - Example 2 (`case_534`): *"Please stop the promotional emails. I still need the account and my order history, so I am not asking for deletion."*
    - Example 3 (`case_535`): *"I'd like to download my account information in a portable format. Please keep the account as it is."*
  - **In `output.csv`**:
    - The output `deletion_status` must be exactly `NOT_APPLICABLE`.
    - `steps_json` must be exactly `[]` (an empty JSON array).
- **Corroborating Evidence**:
  - In `system_activity.csv`, there are exactly 10 `CLASSIFY_REQUEST` events (activities 3486, 3512, 3531, 3618, 3648, 3659, 3741, 3778, 3789, 3827) where `details` explicitly states: *"Privacy intake classified request for account_XXXX as non-deletion; no destructive action was authorized."* These match cases `case_533` through `case_542`.

### 2.2 Distinct Values of Status-Like Columns
- **`deletion_requests.csv` -> `reported_status`** (3 values):
  - `COMPLETE`: 254 cases
  - `PARTIALLY_COMPLETE`: 152 cases
  - `NOT_STARTED`: 112 cases
- **`system_activity.csv` -> `reported_result`** (3 values):
  - `SUCCESS`: 2,914 events
  - `FAILED`: 721 events
  - `PARTIAL`: 376 events
- **`system_activity.csv` -> `event_type`** (17 values):
  - `DELETE_RECORD` (890), `UPDATE_RECORD` (672), `SYNC_RECORD` (447), `INDEX_RECORD` (400), `SEND_EMAIL` (368), `REFRESH_CACHE` (284), `RETAIN_RECORD` (206), `ANONYMIZE_RECORD` (204), `REDACT_RECORD` (173), `CREATE_EXPORT` (155), `CHECK_DATA_FLOW` (89), `BLOCK_RESTORE` (36), `DISABLE_DATA_FLOW` (36), `CHECK_RESTORE_ACCESS` (28), `LINK_RESOURCE_IDENTITY` (12), `CLASSIFY_REQUEST` (10), `RESTORE_BACKUP` (1).
- **Output `deletion_status`** (3 allowed values):
  - `COMPLETE`
  - `INCOMPLETE`
  - `NOT_APPLICABLE`
- **Output `steps_json` -> `phase`** (3 allowed values):
  - `FINDING`
  - `REMEDIATION`
  - `VERIFICATION`
- **Output `steps_json` -> `operation`** (15 allowed values):
  - Findings: `REPORT_REMAINING_RECORD`, `REPORT_EXPOSED_PII`, `REPORT_ACTIVE_DATA_FLOW`, `REPORT_RESTORE_RISK`
  - Remediation: `DISABLE_DATA_FLOW`, `BLOCK_RESTORE`, `DELETE_RECORD`, `REDACT_RECORD`, `ANONYMIZE_RECORD`
  - Verification: `VERIFY_RECORD_ABSENT`, `VERIFY_RECORD_PRESENT`, `VERIFY_RECORD_REDACTED`, `VERIFY_RECORD_ANONYMIZED`, `VERIFY_DATA_FLOW_DISABLED`, `VERIFY_RESTORE_BLOCKED`
- **Output `steps_json` -> `state`** (7 allowed values):
  - `PRESENT`, `ABSENT`, `ACTIVE`, `DISABLED`, `BLOCKED`, `REDACTED`, `ANONYMIZED`

---

## 3. Systems and Source Types in the Corpus

The corpus contains 94 evidence files under `dataset/evidence/` categorized across 5 modalities:

| Source Category | Count | Formats | Logical Systems Represented | Typical Content / Role |
|---|---|---|---|---|
| **Databases** | 24 | `.sql` (SQLite text) | `account_service`, `search_service`, `analytics_platform`, `security_service`, `identity_service`, `backup_service`, `integration_service`, `support_platform`, `legal_service` | Point-in-time SQL snapshot dumps with primary, read replicas, regional replicas (`ap_south`, `eu_west`), reporting replicas, and failover replicas. Contains `customer_profiles`, `customer_search_documents`, `security_audit_events`, `deleted_customer_references` (tombstones). |
| **Records** | 29 | 28 `.json`, 1 `.txt` | `records_assurance_snapshot_bundle`, `integration_service`, `export_service`, `analytics_platform`, `security_service`, `customer_account_service` | Snapshot bundles of customer records, active connector configurations (`connector_configurations_20260812.json`), export jobs, audit ledgers, and account handover reports (`customer_account_handover_20261001.txt`). |
| **Logs** | 26 | `.log` (text / JSON lines) | `central_observability_export`, `service_readback_logs`, `support_platform`, `account_history_service` | Service events (`service_events_ap_south_20260915.log`), support replica logs, readback traces, structured service events, and syslog archives. |
| **Documents** | 4 | `.pdf` (PDF 1.4) | `support_platform`, `account_history_service`, `legal_retention_service`, `security_service` | Support attachments (`delivery_correction_attachment.pdf`), customer statements (`account_history_report_20260718.pdf`), disputed order register (`legal_retention_register_20260529.pdf`), and signed compliance extracts (`security_retention_extract.pdf`). |
| **Images** | 11 | `.png` | Admin consoles for account, search, connector, analytics, export, support, backup, security audit, deleted accounts, object storage, marketing | Visual screenshots representing console views; companion entries exist in `system_activity.csv` (`LINK_RESOURCE_IDENTITY`). |

---

## 4. Identifiers and Identity Graph Links

### 4.1 Identifier Types
1. `user_id`: Canonical stable reference `user_01` to `user_850`.
2. `email`: RFC 5322 email string. Subject to case variations in some log/search documents (e.g. `BCARVALHO6517@GMAIL.COM`).
3. `email_hash`: SHA-256 hex string (64 chars) of `email`. Verified 100% consistent with `sha256(email.encode('utf-8'))`.
4. `phone`: International telephone string (e.g. `+971 50 482 7316`, `+1 (202) 555-0103`, `+33 6 10 19 61 86`).
5. `name`: Full name string (e.g. "Amina El-Masri", "Ingrid Dahl").
6. `order_id`: Order reference numbers formatted as `ORD-2026NNNN`.
7. `ticket_id`: Customer support ticket references formatted as `CS-NNNN`.
8. `resource_id`: Prefix-based logical identifiers (`account_*`, `analytics_*`, `search_*`, `support_*`, `audit_record_*`, `tombstone_*`, `data_flow_*`, `backup_*`, `export_*`, `legal_hold_*`, `object_*`, `email_delivery_*`, `cache_*`, `marketing_*`).
9. `address`: Postal delivery address (present in PDF statement and support attachments).

### 4.2 Historical Identifier Resolution
- Every single one of the 518 cases in `deletion_requests.csv` resolves to a known user in the corpus:
  - **418 cases** match current email directly in `user_identities.csv`.
  - **100 cases** match historical email (`old_value` where `field_name == 'email'`) in `user_audit_log.csv`.
  - **0 cases** are unmatched.
- Union-Find clusters must link `user_id` <-> `email` (current) <-> `email` (historical) <-> `phone` (current) <-> `phone` (historical) <-> `email_hash`.

---

## 5. Deletion Policy Rules (`deletion_rules.csv`)

| Rule ID | Data Category | Condition | Required Action | Engine Mapping |
|---|---|---|---|---|
| `rule_01` | `USER_PROFILE` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_02` | `SECONDARY_IDENTIFIER` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_03` | `SEARCH_INDEX_ENTRY` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_04` | `CACHE_ENTRY` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_05` | `SUPPORT_MESSAGE` | Conversation contains shared context that must be retained | `REDACT` | `REPORT_EXPOSED_PII` -> `REDACT_RECORD` -> `VERIFY_RECORD_REDACTED` |
| `rule_06` | `SUPPORT_ATTACHMENT` | Attachment belongs only to the deletion subject | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_07` | `ANALYTICS_PROFILE` | Record is still attributable to a user | `ANONYMIZE` | `REPORT_EXPOSED_PII` -> `ANONYMIZE_RECORD` -> `VERIFY_RECORD_ANONYMIZED` |
| `rule_08` | `PRODUCT_TELEMETRY` | Record is still attributable to a user | `ANONYMIZE` | `REPORT_EXPOSED_PII` -> `ANONYMIZE_RECORD` -> `VERIFY_RECORD_ANONYMIZED` |
| `rule_09` | `USER_EXPORT` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_10` | `MARKETING_PROFILE` | Always | `DELETE` | `REPORT_REMAINING_RECORD` -> `DELETE_RECORD` -> `VERIFY_RECORD_ABSENT` |
| `rule_11` | `EMAIL_DELIVERY_LOG` | Log contains a user email address | `REDACT` | `REPORT_EXPOSED_PII` -> `REDACT_RECORD` -> `VERIFY_RECORD_REDACTED` |
| `rule_12` | `SECURITY_AUDIT_LOG` | Record is within supplied retention period | `RETAIN` | `VERIFY_RECORD_PRESENT` (legal/security hold) |
| `rule_13` | `LEGAL_HOLD_RECORD` | A supplied legal hold is active | `RETAIN` | `VERIFY_RECORD_PRESENT` (disputed orders, tax records) |
| `rule_14` | `BACKUP_ARCHIVE` | Restore access can be blocked | `RETAIN` | `REPORT_RESTORE_RISK` -> `BLOCK_RESTORE` -> `VERIFY_RESTORE_BLOCKED` |
| `rule_15` | `ACCOUNT_TOMBSTONE` | Account deleted; only stable internal user_id needed | `REDACT` | Direct PII (name, email, phone, email_hash) must be removed, only user_id retained. If PII present: `REPORT_EXPOSED_PII` -> `REDACT_RECORD` -> `VERIFY_RECORD_REDACTED`. |

For active data flows:
- `REPORT_ACTIVE_DATA_FLOW` -> `DISABLE_DATA_FLOW` -> `VERIFY_DATA_FLOW_DISABLED`.

---

## 6. Planted, Adversarial, and Edge-Case Content

1. **Replication Drift Ghost Records**:
   - In multiple database dumps (e.g. `customer_data_read_replica_20260613.sql`, `20260708.sql`, `20260802.sql`, `20260827.sql`, `20260921.sql`), replicas contain `account_*` rows for users that have already been deleted from the `primary` table!
2. **Incomplete Tombstone Redaction (Ghost Data in Tombstones)**:
   - In `customer_data_failover_replica_20260920.sql`, 4 out of 8 tombstone records (`tombstone_3745`, `tombstone_7389`, `tombstone_8095`, `tombstone_8648`) still contain cleartext name, email, phone, or email_hash, violating `rule_15`.
3. **Orphan Search Documents**:
   - In several SQL files, search documents exist with `display_name = null` and `customer_reference = null`, but cleartext `email` is still present.
4. **Duplicate Requests & Resurrection Vectors**:
   - `ingrid.dahl@outlook.com` has two requests: `case_52` (audited 2026-06-19) and `case_33` (audited 2026-07-19).
   - In between, `export_1260` and `export_1842` / `statement NST-2026-0718-1842` were created, proving data recreation.
5. **Non-Deletion Requests (Adversarial False Positives)**:
   - Exactly 10 requests (`case_533` to `case_542`) have request texts asking to update phone/email, download data, or opt-out of marketing while explicitly stating "leave the account active", "not asking for deletion", "keep the account as it is". These must output `NOT_APPLICABLE` with `steps_json=[]`.
6. **Prompt Injections**:
   - Zero overt jailbreak strings found in raw files, but agent prompt must enforce strict data untrusted boundaries.

---

## 7. Exact Output Schema Contract

- **File Path**: Root directory `output.csv` (i.e. `d:\Orchstrate\output.csv`).
- **Columns**: `case_id,deletion_status,steps_json`
- **Row Count**: Exactly 518 data rows + 1 header row, sorted ascending by `case_id`.
- **Formatting Rules**:
  - `deletion_status`: `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
  - For `NOT_APPLICABLE`: `steps_json` must be `[]`.
  - For `COMPLETE`: exactly 0 findings, 0 remediations, only `VERIFICATION` steps with non-empty `evidence_id`.
  - For `INCOMPLETE`: `FINDING` steps (non-empty `evidence_id`), `REMEDIATION` steps (`evidence_id: ""`), `VERIFICATION` steps (`evidence_id: ""`).
  - Consecutive `step_no` from 1.
  - Strict step order: Phase (`FINDING` < `REMEDIATION` < `VERIFICATION`), Operation order per problem statement table, `system_id` ascending, `resource_id` ascending.

---

## 8. Open Questions

1. **OCR on Screenshots**: Tesseract binary is not installed in the Windows environment, but every screenshot has a direct date-and-resource companion in `system_activity.csv` (`LINK_RESOURCE_IDENTITY`) and `dataset/evidence/records/` and `dataset/evidence/databases/`. Recommendation: Use companion structured records and record unparsed images as `UNSCANNABLE` if queried directly.
2. **Audit Reference Timestamp**: Should the cutoff strictly be the row's `audit_at`? Confirmed: Yes, the problem statement states *"Use only information available at or before audit_at when deciding the case. Evidence created later must not change the answer for that case."*

