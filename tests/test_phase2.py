import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
code_dir = REPO_ROOT / "code"
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from audit.scanners.base import EvidenceManifest
from audit.scanners.sql_scanner import SqlScanner
from audit.scanners.document_scanner import DocumentScanner
from audit.recreation import RecreationAnalyzer
from audit.identity import IdentityGraph

DATASET_DIR = REPO_ROOT / "dataset"

class TestPhase2(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = EvidenceManifest(DATASET_DIR)
        self.graph = IdentityGraph(DATASET_DIR)

    def test_evidence_manifest(self) -> None:
        info = self.manifest.get_info_by_path("evidence/databases/customer_accounts_failover_replica_20260902.sql")
        self.assertIsNotNone(info)
        self.assertEqual(info["file_id"], "evidence_54")
        
        # Test cutoff logic
        # Captured 2026-09-02T12:00:00Z
        self.assertTrue(self.manifest.is_captured_before("evidence/databases/customer_accounts_failover_replica_20260902.sql", "2026-09-03T11:30:00Z"))
        self.assertFalse(self.manifest.is_captured_before("evidence/databases/customer_accounts_failover_replica_20260902.sql", "2026-09-01T00:00:00Z"))

    def test_document_scanner(self) -> None:
        scanner = DocumentScanner(DATASET_DIR, self.manifest)
        # Check Priya Raman (user_07, priya.raman@gmail.com) in delivery_correction_attachment.pdf
        cluster = self.graph.get_cluster_by_email("priya.raman@gmail.com")
        self.assertIsNotNone(cluster)
        
        # Scan with audit_at after the document was captured
        findings = scanner.scan("case_07", cluster, "2026-09-20T12:00:00Z")
        self.assertGreater(len(findings), 0)
        self.assertEqual(findings[0].file_id, "evidence_58")
        self.assertIn("delivery_correction_attachment.pdf", findings[0].location)

    def test_recreation_analyzer(self) -> None:
        analyzer = RecreationAnalyzer(DATASET_DIR, self.manifest)
        from audit.models import Finding
        f_flow = Finding(
            request_id="case_11",
            system="integration_service",
            location="connector.json",
            identifier="user_11",
            match_type="EXACT",
            confidence=1.0,
            redacted=False,
            evidence="data_flow_9522",
            resource_id="data_flow_9522",
            file_id="evidence_03"
        )
        cluster = self.graph.get_cluster_by_user_id("user_11")
        self.assertIsNotNone(cluster)
        vectors = analyzer.analyze("case_11", cluster, [f_flow], "2026-09-30T12:00:00Z")
        self.assertEqual(len(vectors), 1)
        self.assertEqual(vectors[0].vector_id, "data_flow_9522")
        self.assertTrue(vectors[0].is_live)

if __name__ == "__main__":
    unittest.main()
