import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .models import Request, Finding, Vector, IdentityCluster, RuleDecision
from .identity import IdentityGraph
from .rules import RulesEngine
from .scanners.base import EvidenceManifest
from .scanners.sql_scanner import SqlScanner
from .scanners.record_scanner import RecordScanner
from .scanners.log_scanner import LogScanner
from .scanners.document_scanner import DocumentScanner
from .recreation import RecreationAnalyzer
from .loaders import read_text_safe

class AuditToolbox:
    """Implements all 9 tools exposed to the agent."""
    def __init__(self, dataset_dir: Path) -> None:
        self.dataset_dir = dataset_dir
        self.manifest = EvidenceManifest(dataset_dir)
        self.identity_graph = IdentityGraph(dataset_dir)
        self.rules_engine = RulesEngine(dataset_dir)
        
        self.sql_scanner = SqlScanner(dataset_dir, self.manifest)
        self.record_scanner = RecordScanner(dataset_dir, self.manifest)
        self.log_scanner = LogScanner(dataset_dir, self.manifest)
        self.doc_scanner = DocumentScanner(dataset_dir, self.manifest)
        self.recreation_analyzer = RecreationAnalyzer(dataset_dir, self.manifest)
        
        self.requests_map: Dict[str, Request] = {}
        self._load_requests()

    def _load_requests(self) -> None:
        from .loaders import load_csv_rows
        # Load sample requests
        for row in load_csv_rows(self.dataset_dir / "sample_deletion_requests.csv"):
            self.requests_map[row["case_id"]] = Request(**row)
        # Load full requests
        for row in load_csv_rows(self.dataset_dir / "deletion_requests.csv"):
            self.requests_map[row["case_id"]] = Request(**row)

    # 1. get_request
    def get_request(self, request_id: str) -> Dict[str, Any]:
        """Fetch request details by case_id."""
        req = self.requests_map.get(request_id)
        if not req:
            return {"error": f"Request {request_id} not found."}
        return req.model_dump()

    # 2. expand_identifiers
    def expand_identifiers(self, request_id: str) -> Dict[str, Any]:
        """Expand subject identifiers, historical aliases, and merge reasons."""
        req = self.requests_map.get(request_id)
        if not req:
            return {"error": f"Request {request_id} not found."}
        cluster = self.identity_graph.get_cluster_by_email(req.email)
        if not cluster:
            return {"error": f"No identity cluster found for {req.email}."}
        return {
            "user_id": cluster.user_id,
            "name": cluster.name,
            "primary_email": cluster.primary_email,
            "emails": list(cluster.emails),
            "phones": list(cluster.phones),
            "email_hashes": list(cluster.email_hashes),
            "merge_reasons": cluster.merge_reasons,
        }

    # 3. list_systems
    def list_systems(self) -> List[Dict[str, Any]]:
        """List corpus inventory, source types, and counts."""
        return [
            {"system": "account_service", "source_type": "SQL / Databases", "evidence_files": 24},
            {"system": "search_service", "source_type": "SQL / Indexes", "evidence_files": 12},
            {"system": "analytics_platform", "source_type": "SQL / JSON Reports", "evidence_files": 15},
            {"system": "security_service", "source_type": "SQL / Audit Ledgers", "evidence_files": 14},
            {"system": "support_platform", "source_type": "Logs / PDFs", "evidence_files": 7},
            {"system": "integration_service", "source_type": "JSON Connectors / Sync", "evidence_files": 10},
            {"system": "backup_service", "source_type": "SQL / Catalogs", "evidence_files": 6},
            {"system": "export_service", "source_type": "JSON Jobs / Exports", "evidence_files": 6},
            {"system": "identity_service", "source_type": "SQL / Tombstones", "evidence_files": 8},
        ]

    # 4. scan_system
    def scan_system(self, request_id: str, system: str) -> List[Dict[str, Any]]:
        """Scan a given system for subject identifiers up to audit_at."""
        req = self.requests_map.get(request_id)
        if not req:
            return []
        cluster = self.identity_graph.get_cluster_by_email(req.email)
        if not cluster:
            return []

        all_findings = []
        all_findings.extend(self.sql_scanner.scan(request_id, cluster, req.audit_at))
        all_findings.extend(self.record_scanner.scan(request_id, cluster, req.audit_at))
        all_findings.extend(self.log_scanner.scan(request_id, cluster, req.audit_at))
        all_findings.extend(self.doc_scanner.scan(request_id, cluster, req.audit_at))

        # Filter by system if specified
        if system and system != "all":
            all_findings = [f for f in all_findings if f.system == system or system in f.system]

        return [f.model_dump() for f in all_findings]

    # 5. read_evidence
    def read_evidence(self, location: str, context_lines: int = 5) -> Dict[str, Any]:
        """Read snippet from a location to evaluate ambiguous findings."""
        parts = location.split(":")
        rel_path = parts[0]
        full_path = self.dataset_dir / rel_path
        if not full_path.exists():
            return {"error": f"File {rel_path} does not exist."}

        text = read_text_safe(full_path)
        lines = text.splitlines()

        line_idx = 0
        if len(parts) > 1 and parts[1].isdigit():
            line_idx = int(parts[1]) - 1

        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        snippet = "\n".join(lines[start:end])

        return {
            "location": location,
            "snippet": snippet,
            "total_lines": len(lines)
        }

    # 6. lookup_rules
    def lookup_rules(self, system: str, data_category: str) -> List[Dict[str, Any]]:
        """Lookup policy rules matching category or system."""
        matches = []
        for rid, rule in self.rules_engine.rules.items():
            if data_category and data_category.lower() in rule["data_category"].lower():
                matches.append(rule)
            elif not data_category:
                matches.append(rule)
        return matches

    # 7. analyze_recreation
    def analyze_recreation(self, request_id: str) -> List[Dict[str, Any]]:
        """Identify live and dormant sync paths and restore vectors."""
        req = self.requests_map.get(request_id)
        if not req:
            return []
        cluster = self.identity_graph.get_cluster_by_email(req.email)
        if not cluster:
            return []
        findings = [Finding(**f) for f in self.scan_system(request_id, "all")]
        vectors = self.recreation_analyzer.analyze(request_id, cluster, findings, req.audit_at)
        return [v.model_dump() for v in vectors]

    # 8. adjudicate_match
    def adjudicate_match(self, finding_id: str, same_person: bool, reason: str) -> Dict[str, Any]:
        """Adjudicate ambiguous/fuzzy findings citing evidence."""
        return {
            "finding_id": finding_id,
            "same_person": same_person,
            "reason": reason,
            "status": "adjudicated"
        }
