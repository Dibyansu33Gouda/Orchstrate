import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple
from .models import IdentityCluster
from .normalize import normalize_email, normalize_phone, generate_all_variants

class DisjointSetUnion:
    """Union-Find data structure tracking merge provenance."""
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}
        self.reasons: Dict[Tuple[str, str], str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            return x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str, reason: str) -> bool:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False
        self.parent[root_x] = root_y
        self.reasons[(x, y)] = reason
        self.reasons[(y, x)] = reason
        return True

class IdentityGraph:
    """Graph of user identities, audit history, and precomputed search variants."""
    def __init__(self, dataset_dir: Path) -> None:
        self.dataset_dir = dataset_dir
        self.dsu = DisjointSetUnion()
        self.user_to_cluster: Dict[str, IdentityCluster] = {}
        self.email_to_user: Dict[str, str] = {}
        self.phone_to_users: Dict[str, Set[str]] = defaultdict(set)
        self.shared_phones: Set[str] = set()
        self.merge_provenance: Dict[str, List[str]] = defaultdict(list)
        
        self._load_identities()
        self._load_audit_logs()
        self._build_clusters()

    def _load_identities(self) -> None:
        ident_path = self.dataset_dir / "user_identities.csv"
        if not ident_path.exists():
            return
            
        with open(ident_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"].strip()
                name = row.get("name", "").strip()
                email = row.get("email", "").strip()
                phone = row.get("phone", "").strip()
                email_hash = row.get("email_hash", "").strip()

                norm_em = normalize_email(email)
                norm_ph = normalize_phone(phone)

                self.email_to_user[email.lower()] = uid
                if norm_em:
                    self.email_to_user[norm_em] = uid
                    self.dsu.union(f"uid:{uid}", f"email:{norm_em}", f"user_identities.csv: primary email for {uid}")

                if norm_ph:
                    self.phone_to_users[norm_ph].add(uid)

                # Initialize cluster
                cluster = IdentityCluster(
                    user_id=uid,
                    name=name,
                    primary_email=email,
                    emails={email, norm_em} if norm_em else {email},
                    phones={phone, norm_ph} if norm_ph else {phone},
                    email_hashes={email_hash} if email_hash else set(),
                    merge_reasons=[f"Created from user_identities.csv snapshot for {uid}"],
                    search_variants=set(),
                )
                self.user_to_cluster[uid] = cluster

    def _load_audit_logs(self) -> None:
        audit_path = self.dataset_dir / "user_audit_log.csv"
        if not audit_path.exists():
            return

        with open(audit_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = row.get("audit_id", "")
                uid = row.get("user_id", "").strip()
                field = row.get("field_name", "").strip()
                old_val = row.get("old_value", "").strip()
                new_val = row.get("new_value", "").strip()

                if uid not in self.user_to_cluster:
                    continue

                cluster = self.user_to_cluster[uid]

                if field == "email":
                    old_norm = normalize_email(old_val)
                    self.email_to_user[old_val.lower()] = uid
                    if old_norm:
                        self.email_to_user[old_norm] = uid
                        self.dsu.union(f"uid:{uid}", f"email:{old_norm}", f"user_audit_log.csv [{aid}]: historical email changed from {old_val} to {new_val}")
                    cluster.emails.add(old_val)
                    if old_norm:
                        cluster.emails.add(old_norm)
                    reason = f"Audit [{aid}] historical email: {old_val} -> {new_val}"
                    cluster.merge_reasons.append(reason)
                    self.merge_provenance[uid].append(reason)

                elif field == "email_hash":
                    cluster.email_hashes.add(old_val)
                    cluster.email_hashes.add(new_val)
                    cluster.merge_reasons.append(f"Audit [{aid}] historical email_hash: {old_val}")

                elif field == "phone":
                    old_norm = normalize_phone(old_val)
                    cluster.phones.add(old_val)
                    if old_norm:
                        cluster.phones.add(old_norm)
                        self.phone_to_users[old_norm].add(uid)
                    cluster.merge_reasons.append(f"Audit [{aid}] historical phone: {old_val} -> {new_val}")

    def _build_clusters(self) -> None:
        # Check for shared phones
        for phone, uids in self.phone_to_users.items():
            if len(uids) > 1:
                self.shared_phones.add(phone)

        # Precompute search variants for each cluster
        for uid, cluster in self.user_to_cluster.items():
            variants: Set[str] = set()
            # User ID variants
            variants.update(generate_all_variants(uid, "user_id"))
            # Email variants
            for em in cluster.emails:
                variants.update(generate_all_variants(em, "email"))
            # Phone variants (skip shared phones to avoid fuzzy false positives in standard exact scans)
            for ph in cluster.phones:
                norm_ph = normalize_phone(ph)
                if norm_ph not in self.shared_phones:
                    variants.update(generate_all_variants(ph, "phone"))
            # Hashes
            for eh in cluster.email_hashes:
                if eh:
                    variants.add(eh.lower())
            # Name variants
            if cluster.name:
                variants.update(generate_all_variants(cluster.name, "name"))

            cluster.search_variants = variants

    def get_cluster_by_email(self, email: str) -> IdentityCluster | None:
        email_clean = email.strip().lower()
        uid = self.email_to_user.get(email_clean)
        if not uid:
            norm = normalize_email(email)
            uid = self.email_to_user.get(norm)
        if uid and uid in self.user_to_cluster:
            return self.user_to_cluster[uid]
        return None

    def get_cluster_by_user_id(self, user_id: str) -> IdentityCluster | None:
        return self.user_to_cluster.get(user_id.strip())
