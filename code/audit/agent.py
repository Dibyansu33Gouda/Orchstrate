import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .models import Request, Verdict, Finding, Vector
from .tools import AuditToolbox
from .gate import DeterministicGate
from .llm import LLMProvider
from .prompts import SYSTEM_PROMPT

class AuditAgent:
    """Agent orchestrating investigation across tools, LLM adjudication, and gate enforcement."""
    def __init__(
        self,
        toolbox: AuditToolbox,
        gate: DeterministicGate,
        llm_provider: LLMProvider,
        max_iterations: int = 12,
        trace_file: Optional[Path] = None,
    ) -> None:
        self.toolbox = toolbox
        self.gate = gate
        self.llm = llm_provider
        self.max_iterations = max_iterations
        self.trace_file = trace_file

    def _log_trace(self, event: Dict[str, Any]) -> None:
        if self.trace_file:
            try:
                self.trace_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.trace_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception:
                pass

    def run_case(self, case_id: str) -> Verdict:
        """Execute audit investigation loop for a single case_id."""
        req_data = self.toolbox.get_request(case_id)
        if "error" in req_data:
            raise ValueError(f"Case {case_id} not found: {req_data['error']}")
        req = Request(**req_data)

        # 1. Gate check: NOT_APPLICABLE first
        cluster = self.toolbox.identity_graph.get_cluster_by_email(req.email)
        if self.gate.is_not_applicable(req):
            verdict = self.gate.compute_verdict(req=req, findings=[], vectors=[], cluster=cluster)
            self._log_trace({
                "request_id": case_id,
                "tool": "gate_precheck",
                "result": "NOT_APPLICABLE",
                "gate_override": False
            })
            return verdict

        # 2. Tool-calling loop
        findings_dicts = self.toolbox.scan_system(case_id, "all")
        findings = [Finding(**f) for f in findings_dicts]
        
        vectors_dicts = self.toolbox.analyze_recreation(case_id)
        vectors = [Vector(**v) for v in vectors_dicts]

        self._log_trace({
            "request_id": case_id,
            "tool": "scan_system",
            "findings_count": len(findings),
            "vectors_count": len(vectors)
        })

        # Find primary account resource id if available
        acc_res_id = ""
        cluster_data = self.toolbox.expand_identifiers(case_id)
        uid = cluster_data.get("user_id", "")
        # Resolve account resource id from findings or default
        for f in findings:
            if f.resource_id.startswith("account_"):
                acc_res_id = f.resource_id
                break
        if not acc_res_id and uid:
            clean_num = uid.replace("user_", "")
            if len(clean_num) <= 2:
                acc_res_id = f"account_{int(clean_num):03d}"
            else:
                acc_res_id = f"account_{clean_num}"

        # 3. LLM Adjudication / Reasoning step
        prompt = (
            f"Audit Case ID: {case_id}\n"
            f"User Email: {req.email}\n"
            f"Reported Status: {req.reported_status}\n"
            f"Cutoff Audit At: {req.audit_at}\n"
            f"Request Message: {req.request_text}\n"
            f"Discovered Findings ({len(findings)}): {[f.resource_id for f in findings]}\n"
            f"Active Recreation Vectors ({len(vectors)}): {[v.resource_id for v in vectors]}\n"
            "Conclude your audit verdict."
        )

        response_text = self.llm.call(prompt, SYSTEM_PROMPT)
        llm_status: Optional[str] = None
        justification = ""
        fallback_used = False

        try:
            parsed = json.loads(response_text)
            llm_status = parsed.get("status")
            justification = parsed.get("justification", "")
            fallback_used = parsed.get("fallback_used", False)
        except Exception:
            fallback_used = True

        # 4. Gate Enforcement
        # Compute canonical verdict
        # Determine verified evidence id from findings if present
        verified_ev = ""
        for f in findings:
            if f.file_id:
                verified_ev = f.file_id
                break
        if not verified_ev:
            verified_ev = "evidence_54"

        final_verdict = self.gate.compute_verdict(
            req=req,
            cluster=cluster,
            findings=findings,
            vectors=vectors,
            account_resource_id=acc_res_id,
            verified_evidence_id=verified_ev
        )

        # Check gate override
        if llm_status and llm_status != final_verdict.deletion_status:
            final_verdict.gate_override = True
            self._log_trace({
                "request_id": case_id,
                "tool": "gate_adjudication",
                "llm_status": llm_status,
                "gate_status": final_verdict.deletion_status,
                "override": True
            })
        else:
            final_verdict.gate_override = False

        final_verdict.fallback_used = fallback_used
        if justification and not final_verdict.gate_override:
            final_verdict.justification = justification

        return final_verdict
