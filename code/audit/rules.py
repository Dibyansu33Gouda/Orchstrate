import csv
from pathlib import Path
from typing import Dict, List, Optional
from .models import RuleDecision, Finding

class RulesEngine:
    """Parses and applies policy rules defined in deletion_rules.csv."""
    def __init__(self, dataset_dir: Path) -> None:
        self.dataset_dir = dataset_dir
        self.rules_file = dataset_dir / "deletion_rules.csv"
        self.rules: Dict[str, Dict[str, str]] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        if not self.rules_file.exists():
            return
            
        with open(self.rules_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = row["rule_id"].strip()
                cat = row["data_category"].strip()
                cond = row.get("condition", "").strip()
                action = row.get("required_action", "").strip()
                self.rules[rid] = {
                    "rule_id": rid,
                    "data_category": cat,
                    "condition": cond,
                    "required_action": action
                }

    def map_category_to_rule_id(self, category: str) -> Optional[str]:
        cat_upper = category.upper().strip()
        for rid, r in self.rules.items():
            if r["data_category"] == cat_upper:
                return rid
        return None

    def classify_finding(self, finding: Finding) -> RuleDecision:
        """
        Classifies a finding into its policy decision:
        PURGE, ANONYMIZE, REDACT, or RETAIN_LEGAL.
        """
        res_id = finding.resource_id.lower()
        sys_id = finding.system.lower()

        # 1. Tombstone
        if res_id.startswith("tombstone") or "deleted_customer_reference" in finding.location:
            rule = self.rules.get("rule_15", {})
            return RuleDecision(
                rule_id="rule_15",
                action="REDACT",
                condition=rule.get("condition", ""),
                explanation="Account tombstone must have direct PII redacted while retaining stable user reference."
            )

        # 2. Security audit log
        if res_id.startswith("audit_record") or "security_audit" in sys_id:
            rule = self.rules.get("rule_12", {})
            return RuleDecision(
                rule_id="rule_12",
                action="RETAIN_LEGAL",
                condition=rule.get("condition", ""),
                explanation="Security audit record is legally retained within retention period."
            )

        # 3. Legal hold record
        if res_id.startswith("legal_hold") or "legal" in sys_id:
            rule = self.rules.get("rule_13", {})
            return RuleDecision(
                rule_id="rule_13",
                action="RETAIN_LEGAL",
                condition=rule.get("condition", ""),
                explanation="Legal hold record is actively retained under compliance hold."
            )

        # 4. Backup archive
        if res_id.startswith("backup") or "backup" in sys_id:
            rule = self.rules.get("rule_14", {})
            return RuleDecision(
                rule_id="rule_14",
                action="BLOCK_RESTORE",
                condition=rule.get("condition", ""),
                explanation="Backup archive must have restore access blocked to prevent data resurrection."
            )

        # 5. Support message / attachment
        if res_id.startswith("support") or "support" in sys_id:
            if "attachment" in finding.location.lower() or finding.location.endswith(".pdf"):
                rule = self.rules.get("rule_06", {})
                return RuleDecision(
                    rule_id="rule_06",
                    action="PURGE",
                    condition=rule.get("condition", ""),
                    explanation="Support ticket attachment belonging only to the subject must be deleted."
                )
            else:
                rule = self.rules.get("rule_05", {})
                return RuleDecision(
                    rule_id="rule_05",
                    action="REDACT",
                    condition=rule.get("condition", ""),
                    explanation="Support message containing shared context must be redacted."
                )

        # 6. Analytics profile / telemetry
        if res_id.startswith("analytics") or "analytics" in sys_id:
            rule = self.rules.get("rule_07", {})
            return RuleDecision(
                rule_id="rule_07",
                action="ANONYMIZE",
                condition=rule.get("condition", ""),
                explanation="Analytics profile attributable to the user must be irreversibly anonymized."
            )

        # 7. Search index entry
        if res_id.startswith("search") or "search" in sys_id:
            rule = self.rules.get("rule_03", {})
            return RuleDecision(
                rule_id="rule_03",
                action="PURGE",
                condition=rule.get("condition", ""),
                explanation="Search index entry must be completely removed."
            )

        # 8. User export
        if res_id.startswith("export") or "export" in sys_id:
            rule = self.rules.get("rule_09", {})
            return RuleDecision(
                rule_id="rule_09",
                action="PURGE",
                condition=rule.get("condition", ""),
                explanation="User export archive must be completely deleted."
            )

        # 9. Marketing profile
        if res_id.startswith("marketing") or "marketing" in sys_id:
            rule = self.rules.get("rule_10", {})
            return RuleDecision(
                rule_id="rule_10",
                action="PURGE",
                condition=rule.get("condition", ""),
                explanation="Marketing profile must be completely deleted."
            )

        # 10. Cache entry
        if res_id.startswith("cache") or "cache" in sys_id:
            rule = self.rules.get("rule_04", {})
            return RuleDecision(
                rule_id="rule_04",
                action="PURGE",
                condition=rule.get("condition", ""),
                explanation="Cache entry must be purged."
            )

        # 11. Email delivery log
        if res_id.startswith("email_delivery") or "email_delivery" in sys_id:
            rule = self.rules.get("rule_11", {})
            return RuleDecision(
                rule_id="rule_11",
                action="REDACT",
                condition=rule.get("condition", ""),
                explanation="Email delivery log containing email address must be redacted."
            )

        # 12. Default user profile / account record
        rule = self.rules.get("rule_01", {})
        return RuleDecision(
            rule_id="rule_01",
            action="PURGE",
            condition=rule.get("condition", ""),
            explanation="User profile record must be completely deleted."
        )
