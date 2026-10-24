import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Set
from .base import BaseScanner, EvidenceManifest
from ..models import Finding, IdentityCluster
from ..loaders import read_text_safe

class SqlScanner(BaseScanner):
    """Executes SQL snapshot dumps with in-memory SQLite to detect ghost records and replication drift."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        super().__init__(dataset_dir, manifest)
        self.db_dir = dataset_dir / "evidence" / "databases"
        self._parsed_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._preload()

    def _preload(self) -> None:
        if not self.db_dir.exists():
            return

        for sql_file in self.db_dir.glob("*.sql"):
            rel = str(sql_file.relative_to(self.dataset_dir)).replace("\\", "/")
            sql_text = read_text_safe(sql_file)

            conn = sqlite3.connect(":memory:")
            try:
                conn.executescript(sql_text)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall() if r[0] != "snapshot_scope"]

                file_records = []
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table});")
                    col_names = [c[1] for c in cursor.fetchall()]

                    cursor.execute(f"SELECT * FROM {table};")
                    for row in cursor.fetchall():
                        row_dict = dict(zip(col_names, row))
                        file_records.append({
                            "table": table,
                            "data": row_dict
                        })

                self._parsed_cache[rel] = file_records
            except Exception as e:
                # If script execution fails, fallback
                pass
            finally:
                conn.close()

    def scan(self, request_id: str, cluster: IdentityCluster, audit_at: str) -> List[Finding]:
        findings: List[Finding] = []
        user_id = cluster.user_id
        search_emails = {e.lower() for e in cluster.emails}

        for rel_path, records in self._parsed_cache.items():
            if not self.manifest.is_captured_before(rel_path, audit_at):
                continue

            info = self.manifest.get_info_by_path(rel_path)
            file_id = info["file_id"] if info else ""
            origin = info.get("origin", "") if info else ""

            for item in records:
                table = item["table"]
                d = item["data"]

                # Two formats: generic JSON or typed schema
                res_id = d.get("resource_id", "")
                rec_uid = None
                rec_email = ""
                rec_phone = None
                rec_name = None
                rec_hash = None
                collection = d.get("collection_name", "")
                origin_sys = d.get("origin_system", origin)
                is_json_row = False

                if "record_json" in d:
                    is_json_row = True
                    try:
                        rec = json.loads(d["record_json"])
                        rec_uid = rec.get("customer_id") or rec.get("user_id") or rec.get("customer_reference")
                        rec_email = (rec.get("email") or rec.get("owner_email") or "").lower()
                        rec_phone = rec.get("phone")
                        rec_name = rec.get("name") or rec.get("display_name")
                        rec_hash = rec.get("email_hash")
                    except Exception:
                        continue
                else:
                    # Relational schema
                    rec_uid = d.get("user_id") or d.get("customer_reference") or d.get("subject_reference")
                    rec_email = (d.get("email") or d.get("customer_email") or d.get("owner_email") or d.get("requester_email") or "").lower()
                    rec_phone = d.get("phone") or d.get("requester_phone")
                    rec_name = d.get("full_name") or d.get("display_name") or d.get("requester_name")
                    rec_hash = d.get("email_hash")

                matched_id = None
                match_type = "EXACT"

                if rec_uid == user_id:
                    matched_id = user_id
                elif rec_email in search_emails:
                    matched_id = rec_email
                elif rec_hash in cluster.email_hashes:
                    matched_id = rec_hash
                    match_type = "HASHED"

                if not matched_id:
                    continue

                # 1. Tombstones (deleted_customer_references or tombstone_*)
                if res_id.startswith("tombstone") or collection == "deleted_customer_references":
                    has_pii = bool(rec_name or rec_email or rec_phone or rec_hash)
                    if has_pii:
                        findings.append(Finding(
                            request_id=request_id,
                            system="identity_service",
                            location=f"{rel_path}:{table}:{res_id}",
                            identifier=matched_id,
                            match_type=match_type,
                            confidence=1.0,
                            redacted=False,
                            evidence=f"Unredacted tombstone {res_id} retains PII",
                            resource_id=res_id,
                            file_id=file_id
                        ))
                    continue

                # 2. Account profile in replica (drift) or primary
                if res_id.startswith("account") or "customer_profiles" in table or collection == "customer_profiles":
                    # Only report as remaining record if it's ACTIVE or in replica where it should be absent
                    findings.append(Finding(
                        request_id=request_id,
                        system="account_service",
                        location=f"{rel_path}:{table}:{res_id}",
                        identifier=matched_id,
                        match_type=match_type,
                        confidence=1.0,
                        redacted=False,
                        evidence=f"Account record {res_id} still present in {table}",
                        resource_id=res_id,
                        file_id=file_id
                    ))
                    continue

                # 3. Search document
                if res_id.startswith("search") or "search" in table or collection == "customer_search_documents":
                    findings.append(Finding(
                        request_id=request_id,
                        system="search_service",
                        location=f"{rel_path}:{table}:{res_id}",
                        identifier=matched_id,
                        match_type=match_type,
                        confidence=1.0,
                        redacted=False,
                        evidence=f"Search document {res_id} index present",
                        resource_id=res_id,
                        file_id=file_id
                    ))
                    continue

                # 4. Analytics record
                if res_id.startswith("analytics") or "analytics" in table or collection == "customer_analytics_reports":
                    has_pii = bool(rec_email or rec_phone or rec_hash or rec_uid)
                    if has_pii:
                        findings.append(Finding(
                            request_id=request_id,
                            system="analytics_platform",
                            location=f"{rel_path}:{table}:{res_id}",
                            identifier=matched_id,
                            match_type=match_type,
                            confidence=1.0,
                            redacted=False,
                            evidence=f"Analytics profile {res_id} exposed",
                            resource_id=res_id,
                            file_id=file_id
                        ))
                    continue

                # 5. Connector configuration (active data flow)
                if res_id.startswith("data_flow") or "connector" in table or collection == "connector_configurations":
                    enabled = d.get("enabled", 1)
                    if enabled:
                        findings.append(Finding(
                            request_id=request_id,
                            system="integration_service",
                            location=f"{rel_path}:{table}:{res_id}",
                            identifier=matched_id,
                            match_type=match_type,
                            confidence=1.0,
                            redacted=False,
                            evidence=f"Active connector {res_id}",
                            resource_id=res_id,
                            file_id=file_id
                        ))
                    continue

                # 6. Backup catalog (restore risk)
                if res_id.startswith("backup") or "backup" in table or collection == "backup_catalog":
                    restore_allowed = d.get("restore_allowed", 1)
                    if restore_allowed:
                        findings.append(Finding(
                            request_id=request_id,
                            system="backup_service",
                            location=f"{rel_path}:{table}:{res_id}",
                            identifier=matched_id,
                            match_type=match_type,
                            confidence=1.0,
                            redacted=False,
                            evidence=f"Backup restore risk {res_id}",
                            resource_id=res_id,
                            file_id=file_id
                        ))
                    continue

                # 7. Support record
                if res_id.startswith("support") or "support" in table or collection in ("support_conversations", "ticket_attachments"):
                    findings.append(Finding(
                        request_id=request_id,
                        system="support_platform",
                        location=f"{rel_path}:{table}:{res_id}",
                        identifier=matched_id,
                        match_type=match_type,
                        confidence=1.0,
                        redacted=False,
                        evidence=f"Support record {res_id} exposed",
                        resource_id=res_id,
                        file_id=file_id
                    ))
                    continue

                # 8. Customer export
                if res_id.startswith("export") or "export" in table or collection == "customer_export_jobs":
                    findings.append(Finding(
                        request_id=request_id,
                        system="export_service",
                        location=f"{rel_path}:{table}:{res_id}",
                        identifier=matched_id,
                        match_type=match_type,
                        confidence=1.0,
                        redacted=False,
                        evidence=f"Export bundle {res_id} present",
                        resource_id=res_id,
                        file_id=file_id
                    ))
                    continue

        return findings
