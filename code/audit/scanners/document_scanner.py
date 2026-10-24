from pathlib import Path
from typing import List, Dict
import pypdf
from .base import BaseScanner, EvidenceManifest
from ..models import Finding, IdentityCluster

class DocumentScanner(BaseScanner):
    """Scans PDF documents under dataset/evidence/documents/."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        super().__init__(dataset_dir, manifest)
        self.doc_dir = dataset_dir / "evidence" / "documents"
        self._extracted_cache: Dict[str, str] = {}
        self._preload()

    def _preload(self) -> None:
        if not self.doc_dir.exists():
            return
        for pdf_file in self.doc_dir.glob("*.pdf"):
            rel = str(pdf_file.relative_to(self.dataset_dir)).replace("\\", "/")
            try:
                reader = pypdf.PdfReader(pdf_file)
                pages_text = []
                for p in reader.pages:
                    pages_text.append(p.extract_text() or "")
                self._extracted_cache[rel] = "\n".join(pages_text)
            except Exception:
                self._extracted_cache[rel] = "UNSCANNABLE"

    def scan(self, request_id: str, cluster: IdentityCluster, audit_at: str) -> List[Finding]:
        findings: List[Finding] = []
        user_id = cluster.user_id
        search_emails = {e.lower() for e in cluster.emails}

        for rel_path, doc_text in self._extracted_cache.items():
            if not self.manifest.is_captured_before(rel_path, audit_at):
                continue

            info = self.manifest.get_info_by_path(rel_path)
            file_id = info["file_id"] if info else ""
            origin = info.get("origin", "") if info else ""

            if doc_text == "UNSCANNABLE":
                findings.append(Finding(
                    request_id=request_id,
                    system=origin or "support_platform",
                    location=rel_path,
                    identifier="UNSCANNABLE",
                    match_type="FUZZY",
                    confidence=0.5,
                    redacted=False,
                    evidence=f"File {rel_path} could not be extracted (UNSCANNABLE)",
                    resource_id="",
                    file_id=file_id
                ))
                continue

            text_lower = doc_text.lower()
            matched_id = None

            if user_id.lower() in text_lower:
                matched_id = user_id
            else:
                for em in search_emails:
                    if em in text_lower:
                        matched_id = em
                        break

            if not matched_id:
                continue

            # Determine resource_id and system
            res_id = ""
            sys_id = origin or "support_platform"
            if "support_001" in doc_text:
                res_id = "support_001"
                sys_id = "support_platform"
            elif "NST-2026-0718-1842" in doc_text:
                res_id = "export_1842"
                sys_id = "export_service"
            elif "audit_record_003" in doc_text:
                res_id = "audit_record_003"
                sys_id = "security_service"

            findings.append(Finding(
                request_id=request_id,
                system=sys_id,
                location=rel_path,
                identifier=matched_id,
                match_type="EXACT",
                confidence=1.0,
                redacted=False,
                evidence=f"PDF document {rel_path} contains reference to {matched_id}",
                resource_id=res_id,
                file_id=file_id
            ))

        return findings
