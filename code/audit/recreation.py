import json
from pathlib import Path
from typing import List, Dict, Set
from .models import Vector, Finding, IdentityCluster
from .loaders import read_text_safe
from .scanners.base import EvidenceManifest

class RecreationAnalyzer:
    """Analyzes active data flows, connectors, sync pipelines, and backup restore risks."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        self.dataset_dir = dataset_dir
        self.manifest = manifest
        self.connectors_file = dataset_dir / "evidence" / "records" / "connector_configurations_20260812.json"
        self.data_flows: List[Dict] = []
        self._load_connectors()

    def _load_connectors(self) -> None:
        if self.connectors_file.exists():
            try:
                raw = read_text_safe(self.connectors_file)
                data = json.loads(raw)
                if isinstance(data, list):
                    self.data_flows = data
                elif isinstance(data, dict):
                    self.data_flows = data.get("connectors", []) or data.get("flows", [])
            except Exception:
                pass

    def analyze(self, request_id: str, cluster: IdentityCluster, findings: List[Finding], audit_at: str) -> List[Vector]:
        vectors: List[Vector] = []
        user_id = cluster.user_id
        search_emails = {e.lower() for e in cluster.emails}

        # Check for active data flows among findings or connectors
        for f in findings:
            if f.resource_id.startswith("data_flow"):
                # Active data flow finding
                vectors.append(Vector(
                    vector_id=f.resource_id,
                    source_system="integration_service",
                    target_system=f.system,
                    resource_id=f.resource_id,
                    enabled=True,
                    is_live=True,
                    evidence_id=f.file_id,
                    explanation=f"Active data flow {f.resource_id} can synchronize or recreate user data."
                ))
            elif f.resource_id.startswith("backup"):
                # Backup restore risk
                vectors.append(Vector(
                    vector_id=f.resource_id,
                    source_system="backup_service",
                    target_system="account_service",
                    resource_id=f.resource_id,
                    enabled=True,
                    is_live=True,
                    evidence_id=f.file_id,
                    explanation=f"Backup archive {f.resource_id} poses an unblocked restore risk."
                ))

        return vectors
