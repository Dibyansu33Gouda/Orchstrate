from typing import Literal, Any
from pydantic import BaseModel, Field

MatchType = Literal["EXACT", "NORMALIZED", "HASHED", "PARTIAL_MASK", "FUZZY"]
PhaseType = Literal["FINDING", "REMEDIATION", "VERIFICATION"]
DeletionStatusType = Literal["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"]

OperationType = Literal[
    # Finding
    "REPORT_REMAINING_RECORD",
    "REPORT_EXPOSED_PII",
    "REPORT_ACTIVE_DATA_FLOW",
    "REPORT_RESTORE_RISK",
    # Remediation
    "DISABLE_DATA_FLOW",
    "BLOCK_RESTORE",
    "DELETE_RECORD",
    "REDACT_RECORD",
    "ANONYMIZE_RECORD",
    # Verification
    "VERIFY_RECORD_ABSENT",
    "VERIFY_RECORD_PRESENT",
    "VERIFY_RECORD_REDACTED",
    "VERIFY_RECORD_ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED",
    "VERIFY_RESTORE_BLOCKED",
]

StateType = Literal[
    "PRESENT",
    "ABSENT",
    "ACTIVE",
    "DISABLED",
    "BLOCKED",
    "REDACTED",
    "ANONYMIZED",
]

class Request(BaseModel):
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str

class Finding(BaseModel):
    request_id: str
    system: str            # logical system name from the corpus
    location: str          # file path plus line, row id, or key
    identifier: str        # which identifier of the subject matched
    match_type: MatchType
    confidence: float
    redacted: bool
    record_created_at: str | None = None
    evidence: str          # the raw matched snippet, truncated
    resource_id: str = ""  # logical resource id, e.g. account_005, search_001
    file_id: str = ""      # evidence_XX from evidence_files.csv

class IdentityCluster(BaseModel):
    user_id: str
    name: str | None = None
    primary_email: str
    emails: set[str] = Field(default_factory=set)
    phones: set[str] = Field(default_factory=set)
    email_hashes: set[str] = Field(default_factory=set)
    merge_reasons: list[str] = Field(default_factory=list)
    search_variants: set[str] = Field(default_factory=set)

class RuleDecision(BaseModel):
    rule_id: str
    action: Literal["PURGE", "ANONYMIZE", "REDACT", "RETAIN_LEGAL", "BLOCK_RESTORE"]
    condition: str
    expires_on: str | None = None
    explanation: str = ""

class Vector(BaseModel):
    vector_id: str
    source_system: str
    target_system: str
    resource_id: str
    schedule: str = ""
    enabled: bool = True
    is_live: bool = False
    evidence_id: str = ""
    explanation: str = ""

class Step(BaseModel):
    step_no: int
    phase: PhaseType
    system_id: str
    resource_id: str
    operation: OperationType
    state: StateType
    evidence_id: str = ""

class Verdict(BaseModel):
    case_id: str
    deletion_status: DeletionStatusType
    steps: list[Step] = Field(default_factory=list)
    justification: str = ""
    gate_override: bool = False
    fallback_used: bool = False
