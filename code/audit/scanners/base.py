import csv
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from ..models import Finding, IdentityCluster

class EvidenceManifest:
    """Manages file_id mappings and captured_at dates from evidence_files.csv."""
    def __init__(self, dataset_dir: Path) -> None:
        self.manifest_file = dataset_dir / "evidence_files.csv"
        self.path_to_info: Dict[str, Dict[str, str]] = {}
        self.id_to_info: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if not self.manifest_file.exists():
            return
            
        with open(self.manifest_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = row["file_id"].strip()
                fpath = row["file_path"].strip()
                orig = row.get("origin", "").strip()
                cap = row.get("captured_at", "").strip()
                
                info = {
                    "file_id": fid,
                    "file_path": fpath,
                    "origin": orig,
                    "captured_at": cap
                }
                self.id_to_info[fid] = info
                # Normalize path for matching
                norm_path = fpath.replace("\\", "/").lower()
                self.path_to_info[norm_path] = info

    def get_info_by_path(self, rel_path: str) -> Optional[Dict[str, str]]:
        norm = rel_path.replace("\\", "/").lower()
        if norm.startswith("dataset/"):
            norm = norm[len("dataset/"):]
        return self.path_to_info.get(norm)

    def is_captured_before(self, rel_path: str, audit_at: str) -> bool:
        """Check temporal cutoff: captured_at must be <= audit_at."""
        info = self.get_info_by_path(rel_path)
        if not info or not info.get("captured_at"):
            return True
        return info["captured_at"] <= audit_at

class BaseScanner(ABC):
    """Abstract base class for all evidence scanners."""
    def __init__(self, dataset_dir: Path, manifest: EvidenceManifest) -> None:
        self.dataset_dir = dataset_dir
        self.manifest = manifest

    @abstractmethod
    def scan(self, request_id: str, cluster: IdentityCluster, audit_at: str) -> List[Finding]:
        """Scan source files and return list of Findings captured on or before audit_at."""
        pass
