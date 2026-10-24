import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .base import BaseScanner, EvidenceManifest
from ..models import Finding, IdentityCluster
from ..loaders import read_text_safe

def extract_all_records(data: Any, system_hint: str = "") -> List[Tuple[Dict[str, Any], str]]:
    """Recursively extracts all record dictionaries from arbitrarily nested JSON structures."""
    results: List[Tuple[Dict[str, Any], str]] = []
    if isinstance(data, dict):
        current_hint = data.get("data_store") or data.get("origin_system") or system_hint
        if any(k in data for k in ("resource_id", "job_id", "export_id", "flow_id", "user_id", "customer_reference", "subject_reference", "email", "owner_email")):
            results.append((data, current_hint))
        for k, v in data.items():
            sub_hint = current_hint
            if k in ("account_service", "identity_service", "security_service", "analytics_platform", "search_service", "support_platform", "integration_service", "backup_service", "export_service"):
                sub_hint = k
            results.extend(extract_all_records(v, sub_hint))
    elif isinstance(data, list):
        for item in data:
            results.extend(extract_all_records(item, system_hint))
    return results

class RecordScanner(BaseScanner):
    """Scans JSON and text records under dataset/evidence/records/."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        super().__init__(dataset_dir, manifest)
        self.records_dir = dataset_dir / "evidence" / "records"
        self._cache: Dict[str, Any] = {}
        self._preload()

    def _preload(self) -> None:
        if not self.records_dir.exists():
            return
        for fpath in self.records_dir.iterdir():
            if fpath.is_file():
                rel = str(fpath.relative_to(self.dataset_dir)).replace("\\", "/")
                raw = read_text_safe(fpath)
                if fpath.suffix == ".json":
                    try:
                        self._cache[rel] = json.loads(raw)
                    except Exception:
                        self._cache[rel] = raw
                else:
                    self._cache[rel] = raw

    def scan(self, request_id: str, cluster: IdentityCluster, audit_at: str) -> List[Finding]:
        findings: List[Finding] = []
        user_id = cluster.user_id
        search_emails = {e.lower() for e in cluster.emails}

        for rel_path, content in self._cache.items():
            if not self.manifest.is_captured_before(rel_path, audit_at):
                continue

            info = self.manifest.get_info_by_path(rel_path)
            file_id = info["file_id"] if info else ""
            default_origin = info.get("origin", "") if info else ""

            # 1. Text file scanning
            if isinstance(content, str):
                lines = content.splitlines()
                for idx, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    matched_id = None
                    if re.search(rf"\b{re.escape(user_id)}\b", line, re.IGNORECASE):
                        matched_id = user_id
                    else:
                        for em in search_emails:
                            if em in line_lower:
                                matched_id = em
                                break
                    if matched_id:
                        findings.append(Finding(
                            request_id=request_id,
                            system=default_origin or "account_service",
                            location=f"{rel_path}:{idx}",
                            identifier=matched_id,
                            match_type="EXACT",
                            confidence=1.0,
                            redacted=False,
                            evidence=line[:120].strip(),
                            resource_id="",
                            file_id=file_id
                        ))
                continue

            # 2. Recursive JSON scanning
            extracted = extract_all_records(content, default_origin)
            for item, sys_hint in extracted:
                res_id = item.get("resource_id") or item.get("job_id") or item.get("export_id") or item.get("flow_id") or ""
                item_uid = item.get("user_id") or item.get("customer_id") or item.get("customer_reference") or item.get("subject_reference")
                item_email = (item.get("email") or item.get("owner_email") or item.get("customer_email") or "").lower()
                item_phone = item.get("phone")
                item_name = item.get("name") or item.get("full_name") or item.get("display_name")
                item_hash = item.get("email_hash")

                matched_id = None
                match_type = "EXACT"

                if item_uid == user_id:
                    matched_id = user_id
                elif item_email in search_emails:
                    matched_id = item_email
                elif item_hash in cluster.email_hashes:
                    matched_id = item_hash
                    match_type = "HASHED"

                if not matched_id:
                    continue

                # Compliance filters:
                # 1. Disabled connectors (enabled == False) are compliant
                if res_id.startswith("data_flow") or "connector" in sys_hint:
                    if item.get("enabled") is False or item.get("enabled") == 0:
                        continue

                # 2. Blocked restores (restore_allowed == False) are compliant
                if res_id.startswith("backup") or "backup" in sys_hint:
                    if item.get("restore_allowed") is False or item.get("restore_allowed") == 0:
                        continue

                # 3. Redacted support tickets (emails and phone are null) are compliant
                if res_id.startswith("support") or "support" in sys_hint:
                    if not item.get("requester_email") and not item.get("requester_phone") and not item.get("requester_name"):
                        continue

                # 4. Anonymized analytics (email, phone, hash are null) are compliant
                if res_id.startswith("analytics") or "analytics" in sys_hint:
                    if not item.get("email") and not item.get("phone") and not item.get("email_hash") and not item.get("customer_reference"):
                        continue

                # 5. Redacted tombstones (name, email, phone, hash are null) are compliant
                if res_id.startswith("tombstone") or "tombstone" in sys_hint:
                    has_pii = bool(item_name or item_email or item_phone or item_hash)
                    if not has_pii:
                        continue

                # 6. Legal security audit records are compliant retained records
                if res_id.startswith("audit_record") or "security_audit" in sys_hint:
                    continue

                sys_id = sys_hint or default_origin
                if res_id.startswith("data_flow"):
                    sys_id = "integration_service"
                elif res_id.startswith("export"):
                    sys_id = "export_service"
                elif res_id.startswith("analytics"):
                    sys_id = "analytics_platform"
                elif res_id.startswith("account"):
                    sys_id = "account_service"
                elif res_id.startswith("search"):
                    sys_id = "search_service"
                elif res_id.startswith("support"):
                    sys_id = "support_platform"
                elif res_id.startswith("tombstone"):
                    sys_id = "identity_service"
                elif res_id.startswith("backup"):
                    sys_id = "backup_service"

                findings.append(Finding(
                    request_id=request_id,
                    system=sys_id,
                    location=f"{rel_path}:{res_id}",
                    identifier=matched_id,
                    match_type=match_type,
                    confidence=1.0,
                    redacted=False,
                    record_created_at=item.get("created_at") or item.get("updated_at"),
                    evidence=f"JSON record {res_id} references {matched_id}",
                    resource_id=res_id,
                    file_id=file_id
                ))

        return findings
