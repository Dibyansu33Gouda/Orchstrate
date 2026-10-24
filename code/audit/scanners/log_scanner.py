import re
from pathlib import Path
from typing import List, Dict
from .base import BaseScanner, EvidenceManifest
from ..models import Finding, IdentityCluster
from ..loaders import read_text_safe

class LogScanner(BaseScanner):
    """Scans log files for exposed user data and readback verification evidence."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        super().__init__(dataset_dir, manifest)
        self.logs_dir = dataset_dir / "evidence" / "logs"
        self._cache: Dict[str, List[str]] = {}
        self._preload()

    def _preload(self) -> None:
        if not self.logs_dir.exists():
            return
        for log_file in self.logs_dir.glob("*.log"):
            rel = str(log_file.relative_to(self.dataset_dir)).replace("\\", "/")
            raw = read_text_safe(log_file)
            self._cache[rel] = raw.splitlines()

    def scan(self, request_id: str, cluster: IdentityCluster, audit_at: str) -> List[Finding]:
        findings: List[Finding] = []
        user_id = cluster.user_id
        search_emails = {e.lower() for e in cluster.emails}

        res_pattern = re.compile(r"\b(account_\w+|support_\w+|search_\w+|analytics_\w+|tombstone_\w+|data_flow_\w+|backup_\w+|export_\w+|audit_record_\w+)\b", re.IGNORECASE)
        uid_pattern = re.compile(rf"\b{re.escape(user_id)}\b", re.IGNORECASE)

        for rel_path, lines in self._cache.items():
            if not self.manifest.is_captured_before(rel_path, audit_at):
                continue

            info = self.manifest.get_info_by_path(rel_path)
            file_id = info["file_id"] if info else ""
            origin = info.get("origin", "") if info else ""

            is_readback = "resource_lookup_trace" in rel_path or "service_readback" in origin

            for line_no, line in enumerate(lines, 1):
                line_lower = line.lower()
                matched_id = None

                if uid_pattern.search(line):
                    matched_id = user_id
                else:
                    for em in search_emails:
                        if em in line_lower:
                            matched_id = em
                            break

                if not matched_id:
                    continue

                res_match = res_pattern.search(line)
                res_id = res_match.group(1) if res_match else ""

                # In readback logs:
                # 1. Started events are just query starts
                if is_readback and ("_started" in line or "lookup_started" in line or "read_started" in line):
                    continue
                # 2. "http_status=404" or "rows=0" means record is absent
                if is_readback and ("http_status=404" in line or "rows=0" in line):
                    continue
                # 3. Anonymized analytics reads
                if is_readback and ("email=null" in line and "phone=null" in line and "customer_reference=null" in line):
                    continue

                # Audit reads of legal audit logs are NOT remaining record findings
                if "audit_record" in res_id or "audit_record_read" in line:
                    continue

                # Check if it was already redacted
                is_redacted = "[redacted]" in line_lower or "***" in line_lower or "requester_email=null" in line

                sys_id = origin or "account_service"
                if "support" in rel_path or res_id.startswith("support"):
                    sys_id = "support_platform"
                elif "search" in rel_path or res_id.startswith("search"):
                    sys_id = "search_service"
                elif "analytics" in rel_path or res_id.startswith("analytics"):
                    sys_id = "analytics_platform"

                if is_redacted and not any(em in line_lower for em in search_emails):
                    continue

                findings.append(Finding(
                    request_id=request_id,
                    system=sys_id,
                    location=f"{rel_path}:{line_no}",
                    identifier=matched_id,
                    match_type="EXACT",
                    confidence=0.9 if is_redacted else 1.0,
                    redacted=is_redacted,
                    evidence=line[:120].strip(),
                    resource_id=res_id,
                    file_id=file_id
                ))

        return findings
