import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
code_dir = REPO_ROOT / "code"
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from audit.models import Request, Finding, Vector, Step, Verdict
from audit.rules import RulesEngine
from audit.gate import DeterministicGate
from audit.output import validate_verdict_rows, write_output_csv

DATASET_DIR = REPO_ROOT / "dataset"

class TestPhase3(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = RulesEngine(DATASET_DIR)
        self.gate = DeterministicGate(self.rules)

    def test_not_applicable_gate(self) -> None:
        req = Request(
            case_id="case_533",
            email="haruka-kato@gmail.com",
            requested_at="2026-08-28T09:00:00Z",
            reported_status="NOT_STARTED",
            reported_at="2026-08-28T10:00:00Z",
            audit_at="2026-08-28T12:00:00Z",
            request_text="The mobile number on my profile is out of date. Please replace it with the new one and leave the account active."
        )
        self.assertTrue(self.gate.is_not_applicable(req))
        verdict = self.gate.compute_verdict(req, [], [])
        self.assertEqual(verdict.deletion_status, "NOT_APPLICABLE")
        self.assertEqual(len(verdict.steps), 0)

    def test_incomplete_verdict(self) -> None:
        req = Request(
            case_id="case_05",
            email="leila.haddad@yahoo.com",
            requested_at="2026-08-27T14:17:00Z",
            reported_status="COMPLETE",
            reported_at="2026-08-28T09:03:00Z",
            audit_at="2026-09-08T13:40:00Z",
            request_text="I deleted this account and received a confirmation, but the same email address is still recognized. Please remove any remaining copy of my profile."
        )
        finding = Finding(
            request_id="case_05",
            system="account_service",
            location="customer_accounts.sql:10",
            identifier="user_05",
            match_type="EXACT",
            confidence=1.0,
            redacted=False,
            evidence="account_005 active",
            resource_id="account_005",
            file_id="evidence_54"
        )
        verdict = self.gate.compute_verdict(req, [finding], [], account_resource_id="account_005")
        self.assertEqual(verdict.deletion_status, "INCOMPLETE")
        # Should have FINDING, REMEDIATION, VERIFICATION
        phases = [s.phase for s in verdict.steps]
        self.assertIn("FINDING", phases)
        self.assertIn("REMEDIATION", phases)
        self.assertIn("VERIFICATION", phases)
        self.assertEqual(verdict.steps[0].evidence_id, "evidence_54")

    def test_complete_verdict(self) -> None:
        req = Request(
            case_id="case_01",
            email="amina.elmasri@gmail.com",
            requested_at="2026-08-18T09:14:00Z",
            reported_status="COMPLETE",
            reported_at="2026-08-20T16:42:00Z",
            audit_at="2026-09-03T11:30:00Z",
            request_text="Hi, I haven't used this account in years and would like it closed."
        )
        verdict = self.gate.compute_verdict(
            req,
            findings=[],
            vectors=[],
            account_resource_id="account_001",
            verified_evidence_id="evidence_54"
        )
        self.assertEqual(verdict.deletion_status, "COMPLETE")
        self.assertEqual(len(verdict.steps), 1)
        self.assertEqual(verdict.steps[0].phase, "VERIFICATION")
        self.assertEqual(verdict.steps[0].operation, "VERIFY_RECORD_ABSENT")
        self.assertEqual(verdict.steps[0].evidence_id, "evidence_54")

    def test_output_validator(self) -> None:
        valid_row = {
            "case_id": "case_01",
            "deletion_status": "COMPLETE",
            "steps_json": '[{"step_no":1,"phase":"VERIFICATION","system_id":"account_service","resource_id":"account_001","operation":"VERIFY_RECORD_ABSENT","state":"ABSENT","evidence_id":"evidence_54"}]'
        }
        errors = validate_verdict_rows([valid_row], expected_count=1)
        self.assertEqual(len(errors), 0)

if __name__ == "__main__":
    unittest.main()
