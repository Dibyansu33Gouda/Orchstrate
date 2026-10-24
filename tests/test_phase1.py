import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
code_dir = REPO_ROOT / "code"
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from audit.normalize import (
    normalize_text,
    normalize_email,
    normalize_phone,
    generate_hashes,
    is_partial_mask,
    matches_mask,
    generate_all_variants,
)
from audit.identity import IdentityGraph
from audit.rules import RulesEngine
from audit.models import Finding
from audit.loaders import parse_sql_inserts

DATASET_DIR = REPO_ROOT / "dataset"

class TestPhase1(unittest.TestCase):
    def test_normalization(self) -> None:
        # Email normalization
        self.assertEqual(normalize_email("John.Doe+promo@gmail.com"), "johndoe@gmail.com")
        self.assertEqual(normalize_email("  Test.User@Outlook.com  "), "test.user@outlook.com")
        
        # Phone normalization
        self.assertEqual(normalize_phone("+1 (202) 555-0103"), "+12025550103")
        self.assertEqual(normalize_phone("+34 612 847 593"), "+34612847593")
        
        # Hashes
        h = generate_hashes("test@example.com")
        self.assertEqual(len(h["sha256"]), 64)
        self.assertEqual(len(h["md5"]), 32)
        self.assertEqual(len(h["sha1"]), 40)
        
        # Mask detection
        self.assertTrue(is_partial_mask("j***@gmail.com"))
        self.assertTrue(is_partial_mask("****1234"))
        self.assertFalse(is_partial_mask("normal@gmail.com"))
        self.assertTrue(matches_mask("j***@gmail.com", "john@gmail.com"))
        self.assertFalse(matches_mask("j***@gmail.com", "alice@gmail.com"))

    def test_identity_graph_full_resolution(self) -> None:
        graph = IdentityGraph(DATASET_DIR)
        
        # Check sample user_01
        cluster1 = graph.get_cluster_by_email("amina.elmasri@gmail.com")
        self.assertIsNotNone(cluster1)
        self.assertEqual(cluster1.user_id, "user_01")
        self.assertIn("amina.elmasri@gmail.com", cluster1.emails)
        
        # Check historical email resolution (from user_audit_log row audit_59: user_523)
        cluster_hist = graph.get_cluster_by_email("o.walker6695@yahoo.com")
        self.assertIsNotNone(cluster_hist)
        self.assertEqual(cluster_hist.user_id, "user_523")
        self.assertTrue(any("audit_59" in r for r in cluster_hist.merge_reasons))

    def test_sql_loader(self) -> None:
        sample_sql = """
        INSERT INTO customer_data_primary VALUES ('account_001', 'account_service', 'customer_profiles', '{"customer_id": "user_01", "email": "test@example.com"}', '2026-09-02T12:00:00Z');
        """
        records = parse_sql_inserts(sample_sql)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["resource_id"], "account_001")
        self.assertEqual(records[0]["origin_system"], "account_service")
        self.assertEqual(records[0]["record"]["customer_id"], "user_01")

    def test_rules_engine(self) -> None:
        rules = RulesEngine(DATASET_DIR)
        
        # User account finding -> PURGE
        f1 = Finding(
            request_id="case_01",
            system="account_service",
            location="customer_accounts.sql:10",
            identifier="user_01",
            match_type="EXACT",
            confidence=1.0,
            redacted=False,
            evidence="user_01",
            resource_id="account_001"
        )
        dec1 = rules.classify_finding(f1)
        self.assertEqual(dec1.rule_id, "rule_01")
        self.assertEqual(dec1.action, "PURGE")
        
        # Tombstone finding -> REDACT
        f2 = Finding(
            request_id="case_31",
            system="identity_service",
            location="failover.sql:5",
            identifier="user_17",
            match_type="EXACT",
            confidence=1.0,
            redacted=False,
            evidence="user_17",
            resource_id="tombstone_440"
        )
        dec2 = rules.classify_finding(f2)
        self.assertEqual(dec2.rule_id, "rule_15")
        self.assertEqual(dec2.action, "REDACT")
        
        # Security audit -> RETAIN_LEGAL
        f3 = Finding(
            request_id="case_03",
            system="security_service",
            location="audit.sql:12",
            identifier="user_03",
            match_type="EXACT",
            confidence=1.0,
            redacted=False,
            evidence="audit_record_2016",
            resource_id="audit_record_2016"
        )
        dec3 = rules.classify_finding(f3)
        self.assertEqual(dec3.rule_id, "rule_12")
        self.assertEqual(dec3.action, "RETAIN_LEGAL")

if __name__ == "__main__":
    unittest.main()
