"""
Verification Evidence Collector.
Preloads and indexes all compliant verification records and proof-of-absence / proof-of-retention
evidence across logs, structured records, snapshot bundles, and exports.
"""
import re
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import Step, IdentityCluster
from .loaders import read_text_safe
from .scanners.base import EvidenceManifest

class VerificationCollector:
    """Collects and indexes ground-truth verification states across the corpus."""

    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        self.dataset_dir = dataset_dir
        self.manifest = manifest
        # (identifier_lower) -> list of raw verified items
        self._records_by_subj: Dict[str, List[Dict[str, Any]]] = {}
        self._preload_all()

    def _add_record(self, subj: str, system: str, resource: str, operation: str, state: str, file_id: str, captured_at: str) -> None:
        if not subj or not resource:
            return
        key = subj.strip().lower()
        self._records_by_subj.setdefault(key, []).append({
            "system_id": system,
            "resource_id": resource,
            "operation": operation,
            "state": state,
            "evidence_id": file_id,
            "captured_at": captured_at
        })

    def _preload_all(self) -> None:
        self._preload_logs()
        self._preload_handover_records()
        self._preload_service_exports()
        self._preload_snapshot_bundles()
        self._preload_analytics_reports()

    def _preload_logs(self) -> None:
        logs_dir = self.dataset_dir / "evidence" / "logs"
        if not logs_dir.exists():
            return
        for log_file in logs_dir.glob("*.log"):
            rel = str(log_file.relative_to(self.dataset_dir)).replace("\\", "/")
            info = self.manifest.get_info_by_path(rel)
            if not info:
                continue
            file_id = info["file_id"]
            captured_at = info["captured_at"]

            traces: Dict[str, Any] = {}
            lines = read_text_safe(log_file).splitlines()

            for line in lines:
                if "{" in line and "}" in line:
                    try:
                        s_idx = line.find("{")
                        e_idx = line.rfind("}")
                        data = json.loads(line[s_idx:e_idx+1])
                        tr = data.get("trace_id")
                        ev = data.get("event", "")
                        svc = data.get("service") or data.get("logger")
                        subj = data.get("subject_ref") or data.get("lookup_key") or data.get("subject_key")
                        res = data.get("resource_id")
                        rows = str(data.get("rows", ""))
                        status = str(data.get("http_status", ""))
                        if tr and subj and "_started" in ev:
                            traces[tr] = (subj, svc)
                        elif tr and res and "_completed" in ev:
                            if tr in traces:
                                s_subj, s_svc = traces[tr]
                                final_svc = svc or s_svc
                                if rows == "0" or status == "404":
                                    self._add_record(s_subj, final_svc, res, "VERIFY_RECORD_ABSENT", "ABSENT", file_id, captured_at)
                                elif final_svc == "security_service" and (rows == "1" or "passed" in str(data.get("integrity_check", ""))):
                                    self._add_record(s_subj, "security_service", res, "VERIFY_RECORD_PRESENT", "PRESENT", file_id, captured_at)
                                elif data.get("enabled") in (False, "false", "disabled"):
                                    self._add_record(s_subj, "integration_service", res, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", file_id, captured_at)
                                elif data.get("restore_allowed") in (False, "false", "blocked"):
                                    self._add_record(s_subj, "backup_service", res, "VERIFY_RESTORE_BLOCKED", "BLOCKED", file_id, captured_at)
                                elif final_svc == "analytics_platform" and data.get("email") in (None, "null"):
                                    self._add_record(s_subj, "analytics_platform", res, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id, captured_at)
                                elif final_svc == "support_platform" and data.get("requester_email") in (None, "null"):
                                    self._add_record(s_subj, "support_platform", res, "VERIFY_RECORD_REDACTED", "REDACTED", file_id, captured_at)
                    except Exception:
                        pass
                else:
                    matches = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', line)
                    cleaned = {m[0]: (m[1] if m[1] != "" else m[2]) for m in matches}
                    tr = cleaned.get("trace_id")
                    ev = cleaned.get("event", "")
                    svc = cleaned.get("service")
                    subj = cleaned.get("lookup_key") or cleaned.get("subject_ref") or cleaned.get("subject_key")
                    res = cleaned.get("resource_id")
                    rows = cleaned.get("rows", "")
                    status = cleaned.get("http_status", "")

                    if tr and subj and "_started" in ev:
                        traces[tr] = (subj, svc)
                    elif tr and res and "_completed" in ev:
                        if tr in traces:
                            s_subj, s_svc = traces[tr]
                            final_svc = svc or s_svc
                            if rows == "0" or status == "404":
                                self._add_record(s_subj, final_svc, res, "VERIFY_RECORD_ABSENT", "ABSENT", file_id, captured_at)
                            elif final_svc == "security_service" and (rows == "1" or cleaned.get("integrity_check") == "passed"):
                                self._add_record(s_subj, "security_service", res, "VERIFY_RECORD_PRESENT", "PRESENT", file_id, captured_at)
                            elif cleaned.get("enabled") in (False, "false", "disabled"):
                                self._add_record(s_subj, "integration_service", res, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", file_id, captured_at)
                            elif cleaned.get("restore_allowed") in (False, "false", "blocked"):
                                self._add_record(s_subj, "backup_service", res, "VERIFY_RESTORE_BLOCKED", "BLOCKED", file_id, captured_at)
                            elif final_svc == "analytics_platform" and cleaned.get("email") in (None, "null"):
                                self._add_record(s_subj, "analytics_platform", res, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id, captured_at)
                            elif final_svc == "support_platform" and cleaned.get("requester_email") in (None, "null"):
                                self._add_record(s_subj, "support_platform", res, "VERIFY_RECORD_REDACTED", "REDACTED", file_id, captured_at)

    def _preload_handover_records(self) -> None:
        rec_dir = self.dataset_dir / "evidence" / "records"
        if not rec_dir.exists():
            return
        for txt_file in rec_dir.glob("customer_account_handover_*.txt"):
            rel = str(txt_file.relative_to(self.dataset_dir)).replace("\\", "/")
            info = self.manifest.get_info_by_path(rel)
            if not info:
                continue
            file_id = info["file_id"]
            captured_at = info["captured_at"]

            lines = read_text_safe(txt_file).splitlines()
            for line in lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6:
                    svc = parts[1]
                    res = parts[2]
                    rec_type = parts[3]
                    state_ind = parts[4]
                    subj = parts[5]

                    if state_ind == "NOT_FOUND":
                        self._add_record(subj, svc, res, "VERIFY_RECORD_ABSENT", "ABSENT", file_id, captured_at)
                    elif state_ind == "FOUND" and rec_type == "SECURITY_AUDIT_LOG":
                        self._add_record(subj, "security_service", res, "VERIFY_RECORD_PRESENT", "PRESENT", file_id, captured_at)
                    elif state_ind == "ANONYMIZED":
                        self._add_record(subj, "analytics_platform", res, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id, captured_at)
                    elif state_ind == "REDACTED":
                        self._add_record(subj, "support_platform", res, "VERIFY_RECORD_REDACTED", "REDACTED", file_id, captured_at)
                    elif state_ind == "DISABLED":
                        self._add_record(subj, "integration_service", res, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", file_id, captured_at)
                    elif state_ind == "BLOCKED":
                        self._add_record(subj, "backup_service", res, "VERIFY_RESTORE_BLOCKED", "BLOCKED", file_id, captured_at)

    def _preload_service_exports(self) -> None:
        rec_dir = self.dataset_dir / "evidence" / "records"
        if not rec_dir.exists():
            return
        for exp_file in rec_dir.glob("service_resource_export_*.json"):
            rel = str(exp_file.relative_to(self.dataset_dir)).replace("\\", "/")
            info = self.manifest.get_info_by_path(rel)
            if not info:
                continue
            file_id = info["file_id"]
            captured_at = info["captured_at"]

            try:
                data = json.loads(read_text_safe(exp_file))
                exports = data.get("service_exports", {})

                # 1. account_service profile_lookups
                for item in exports.get("account_service", {}).get("profile_lookups", []):
                    res = item.get("resource_id")
                    st = item.get("status_code")
                    # Lookup email or customer reference if embedded
                    # Note: in service_resource_export, profile_lookups might link to resource
                    # If status_code == 404, record is absent

                # 2. security_service audit_records
                for item in exports.get("security_service", {}).get("audit_records", []):
                    res = item.get("resource_id")
                    subj = item.get("subject_reference")
                    if subj and res:
                        self._add_record(subj, "security_service", res, "VERIFY_RECORD_PRESENT", "PRESENT", file_id, captured_at)

                # 3. analytics_platform profiles
                for item in exports.get("analytics_platform", {}).get("profiles", []):
                    res = item.get("resource_id")
                    subj = item.get("customer_reference") or item.get("email")
                    if subj and res:
                        if not item.get("email") and not item.get("phone") and not item.get("email_hash"):
                            self._add_record(subj, "analytics_platform", res, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id, captured_at)

                # 4. support_platform tickets
                for item in exports.get("support_platform", {}).get("tickets", []):
                    res = item.get("resource_id")
                    subj = item.get("customer_reference") or item.get("requester_email")
                    if subj and res:
                        if not item.get("requester_email") and not item.get("requester_phone") and not item.get("requester_name"):
                            self._add_record(subj, "support_platform", res, "VERIFY_RECORD_REDACTED", "REDACTED", file_id, captured_at)

                # 5. integration_service connectors
                for item in exports.get("integration_service", {}).get("connectors", []):
                    res = item.get("resource_id")
                    subj = item.get("customer_reference") or item.get("customer_email")
                    if subj and res and item.get("enabled") in (False, 0):
                        self._add_record(subj, "integration_service", res, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", file_id, captured_at)

                # 6. backup_service restore_entries
                for item in exports.get("backup_service", {}).get("restore_entries", []):
                    res = item.get("resource_id")
                    subj = item.get("customer_reference") or item.get("customer_email")
                    if subj and res and item.get("restore_allowed") in (False, 0):
                        self._add_record(subj, "backup_service", res, "VERIFY_RESTORE_BLOCKED", "BLOCKED", file_id, captured_at)

                # Also search lookups in account_service:
                for item in exports.get("account_service", {}).get("profile_lookups", []):
                    res = item.get("resource_id")
                    st = item.get("status_code")
                    if res and st == 404:
                        # Map resource_id to user_id if account_...
                        # account_6440 -> user_21
                        # We can index by res
                        pass
            except Exception:
                pass

    def _preload_snapshot_bundles(self) -> None:
        rec_dir = self.dataset_dir / "evidence" / "records"
        if not rec_dir.exists():
            return
        for bundle_file in rec_dir.glob("customer_data_snapshot_bundle_*.json"):
            rel = str(bundle_file.relative_to(self.dataset_dir)).replace("\\", "/")
            info = self.manifest.get_info_by_path(rel)
            if not info:
                continue
            file_id = info["file_id"]
            captured_at = info["captured_at"]

            try:
                data = json.loads(read_text_safe(bundle_file))
                for snap in data.get("snapshots", []):
                    ds = snap.get("data_store")
                    records = snap.get("records", [])

                    if ds == "identity_service":
                        for item in records:
                            res = item.get("resource_id")
                            subj = item.get("subject_reference") or item.get("email")
                            if subj and res:
                                if not item.get("email") and not item.get("phone") and not item.get("name") and not item.get("email_hash"):
                                    self._add_record(subj, "identity_service", res, "VERIFY_RECORD_REDACTED", "REDACTED", file_id, captured_at)

                    elif ds == "security_service":
                        for item in records:
                            res = item.get("resource_id")
                            subj = item.get("subject_reference")
                            if subj and res:
                                self._add_record(subj, "security_service", res, "VERIFY_RECORD_PRESENT", "PRESENT", file_id, captured_at)
            except Exception:
                pass

    def _preload_analytics_reports(self) -> None:
        rec_dir = self.dataset_dir / "evidence" / "records"
        if not rec_dir.exists():
            return
        for rep_file in rec_dir.glob("customer_analytics_report_*.json"):
            rel = str(rep_file.relative_to(self.dataset_dir)).replace("\\", "/")
            info = self.manifest.get_info_by_path(rel)
            if not info:
                continue
            file_id = info["file_id"]
            captured_at = info["captured_at"]

            try:
                data = json.loads(read_text_safe(rep_file))
                for item in data.get("cohorts", []) or data.get("records", []):
                    res = item.get("resource_id") or item.get("cohort_id")
                    subj = item.get("customer_reference") or item.get("email")
                    if subj and res:
                        if not item.get("email") and not item.get("phone") and not item.get("email_hash"):
                            self._add_record(subj, "analytics_platform", res, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id, captured_at)
            except Exception:
                pass

    def get_verification_records(self, cluster: IdentityCluster, audit_at: str) -> List[Dict[str, Any]]:
        """Returns all verification proofs captured at or before audit_at for the cluster."""
        subjects = {cluster.user_id.lower()}
        for em in cluster.emails:
            subjects.add(em.lower())

        records: List[Dict[str, Any]] = []
        seen = set()

        for subj in subjects:
            for rec in self._records_by_subj.get(subj, []):
                if rec["captured_at"] <= audit_at:
                    sig = (rec["system_id"], rec["resource_id"], rec["operation"])
                    if sig not in seen:
                        seen.add(sig)
                        records.append(rec)

        return records
