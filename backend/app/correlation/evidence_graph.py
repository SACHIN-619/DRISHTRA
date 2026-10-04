"""
DRISHTRA Correlation Engine - Cross-Lifecycle Evidence Graph
Constructs a typed, epistemically rigorous knowledge graph connecting:
Contributor -> Dataset -> Model -> Runtime -> Inference -> Findings -> Evidence

Epistemic Status Categories:
- OBSERVED: Directly recorded telemetry / cryptographic record
- DERIVED: Algorithmically computed from raw data (e.g. hash, feature centroid)
- SUPPORTS: Evidence reinforces an integrity hypothesis
- CORRELATES: Statistical or temporal co-occurrence without direct causality
- UNKNOWN: Unverified or missing connection

Core Capabilities:
1. Forward Traceability: Contributor -> Dataset -> Model -> Runtime -> Inference
2. Reverse Traceability: Suspicious Inference -> Evidence -> Model -> Dataset -> Contributor
3. Cross-Lifecycle Multi-Path Convergence Analysis (The Core Innovation)
4. Dynamic Contributor Risk Identification without hardcoded IDs
"""
from typing import Dict, Any, List, Optional, Set
import networkx as nx
from app.schemas.all_schemas import GraphNode, GraphEdge, EvidenceGraphResponse, LineageTraceResponse

class EvidenceGraphBuilder:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.graph = nx.DiGraph()

    @classmethod
    def from_database(cls, case_id: str, db) -> "EvidenceGraphBuilder":
        from app.db.models import Contributor, Dataset, ModelAsset, InferenceRecord, Finding, RuntimeBinding, EvidenceEdge
        builder = cls(case_id)

        contribs = db.query(Contributor).filter(Contributor.case_id == case_id).all()
        datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
        models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
        inferences = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).all()
        findings = db.query(Finding).filter(Finding.case_id == case_id).all()

        flagged_assets = {f.asset_id for f in findings if f.severity in ["CRITICAL", "HIGH"]}
        flagged_contrib_ids = set()
        for d in datasets:
            if d.dataset_id in flagged_assets:
                flagged_contrib_ids.add(d.contributor_id)
        for m in models:
            if m.model_id in flagged_assets:
                flagged_contrib_ids.add(m.contributor_id)

        for c in contribs:
            status = "FLAGGED" if c.contributor_id in flagged_contrib_ids else "NORMAL"
            builder.add_node(f"contributor:{c.contributor_id}", c.name, "Contributor", status=status, details={"type": c.contributor_type})

        for d in datasets:
            d_findings = [f for f in findings if f.asset_id == d.dataset_id]
            status = "FINDING" if d_findings else "VERIFIED"
            builder.add_node(f"dataset:{d.dataset_id}", d.name, "Dataset", status=status, details={"sha256": d.sha256[:16] if d.sha256 else "", "samples": d.sample_count})

        for m in models:
            m_findings = [f for f in findings if f.asset_id == m.model_id]
            status = "FINDING" if m_findings else "VERIFIED"
            builder.add_node(f"model:{m.model_id}", m.name, "Model", status=status, details={"arch": m.architecture, "digest": m.weight_sha256[:16] if m.weight_sha256 else ""})

        runtimes = db.query(RuntimeBinding).filter(RuntimeBinding.case_id == case_id).all()
        for r in runtimes:
            builder.add_node(f"runtime:{r.runtime_id}", f"Runtime ({r.hardware_target}/{r.quantization})", "Runtime", status="NORMAL")

        for inf in inferences:
            builder.add_node(
                f"inference:{inf.inference_id}",
                f"Inference #{inf.sequence} ({inf.inference_id})",
                "Inference",
                status=inf.verification_status,
                details={"verification": inf.verification_status, "nonce": inf.nonce}
            )

        edges = db.query(EvidenceEdge).filter(EvidenceEdge.case_id == case_id).all()
        for e in edges:
            rel = "contributed" if e.relationship == "contributed_by" else e.relationship
            builder.add_edge(e.source_node, e.target_node, rel, epistemic_status=e.epistemic_status)

        # Structural lineage that follows directly from registered records (OBSERVED)
        def _ensure(src, dst, rel):
            if src in builder.graph and dst in builder.graph and not builder.graph.has_edge(src, dst):
                builder.add_edge(src, dst, rel, epistemic_status="OBSERVED")
        for d in datasets:
            _ensure(f"contributor:{d.contributor_id}", f"dataset:{d.dataset_id}", "contributed")
        for m in models:
            _ensure(f"contributor:{m.contributor_id}", f"model:{m.model_id}", "supplied")
            if m.reference_model_id:
                _ensure(f"model:{m.reference_model_id}", f"model:{m.model_id}", "reference_for")
        for r in runtimes:
            _ensure(f"model:{r.model_id}", f"runtime:{r.runtime_id}", "bound_to")
        rt_by_model = {}
        for r in runtimes:
            rt_by_model.setdefault(r.model_id, r.runtime_id)
        for inf in inferences:
            rt = inf.runtime_id or rt_by_model.get(inf.model_id)
            if rt and f"runtime:{rt}" in builder.graph:
                _ensure(f"runtime:{rt}", f"inference:{inf.inference_id}", "produced")
            elif inf.model_id:
                _ensure(f"model:{inf.model_id}", f"inference:{inf.inference_id}", "produced")

        # Counter-evidence: checks that actually ran and passed (latest per asset/check)
        from app.db.models import CheckExecution
        latest = {}
        for ce in db.query(CheckExecution).filter(CheckExecution.case_id == case_id).order_by(CheckExecution.executed_at.asc()).all():
            latest[(ce.asset_id, ce.check_id)] = ce
        for (asset_id, check_id), ce in latest.items():
            prefix = {"DATASET": "dataset:", "MODEL": "model:", "INFERENCE": "inference:"}.get(ce.asset_type, "")
            if f"{prefix}{asset_id}" not in builder.graph:
                continue
            if ce.outcome == "PASS":
                node = f"check:{asset_id}:{check_id}"
                builder.add_node(node, check_id, "CounterEvidence", status="VERIFIED", details={"detail": ce.detail, "execution_id": ce.execution_id})
                builder.add_edge(f"{prefix}{asset_id}", node, "verified_by", epistemic_status="OBSERVED")
            elif ce.outcome in ("NOT_APPLICABLE", "NOT_TESTED", "INCONCLUSIVE"):
                node = f"limit:{asset_id}:{check_id}"
                builder.add_node(node, check_id, "Limitation", status=ce.outcome, details={"detail": ce.detail})
                builder.add_edge(f"{prefix}{asset_id}", node, "limited_by", epistemic_status="DECLARED")

        for f in findings:
            f_node = f"finding:{f.finding_id}"
            builder.add_node(f_node, f.finding_type, "Finding", status=f.severity, details={"severity": f.severity, "explanation": f.explanation})
            prefix = "dataset:" if f.asset_type == "DATASET" else ("model:" if f.asset_type == "MODEL" else "inference:")
            builder.add_edge(f"{prefix}{f.asset_id}", f_node, "has_finding", epistemic_status="DERIVED")

        return builder

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        status: str = "NORMAL",
        details: Optional[Dict[str, Any]] = None
    ):
        self.graph.add_node(
            node_id,
            id=node_id,
            label=label,
            type=node_type,
            status=status,
            details=details or {}
        )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        epistemic_status: str = "OBSERVED",
        evidence_ids: Optional[List[str]] = None
    ):
        edge_id = f"{source_id}->{target_id}:{relationship}"
        self.graph.add_edge(
            source_id,
            target_id,
            id=edge_id,
            relationship=relationship,
            epistemic_status=epistemic_status,
            evidence_ids=evidence_ids or []
        )

    def to_schema(self) -> EvidenceGraphResponse:
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append(GraphNode(
                id=n,
                label=data.get("label", n),
                type=data.get("type", "UNKNOWN"),
                status=data.get("status", "NORMAL"),
                details=data.get("details", {})
            ))
        
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(GraphEdge(
                id=data.get("id", f"{u}->{v}"),
                source=u,
                target=v,
                relationship=data.get("relationship", "linked_to"),
                epistemic_status=data.get("epistemic_status", "OBSERVED"),
                evidence_ids=data.get("evidence_ids", [])
            ))

        return EvidenceGraphResponse(case_id=self.case_id, nodes=nodes, edges=edges)

    def trace_flag_subgraph(self, target_node_id: str) -> Dict[str, Any]:
        """
        Reconstructs the explanatory upstream path for:
        "WHY WAS THIS RESULT FLAGGED?" (The Centerpiece Capability)
        
        Reverse lineage traversal:
        Inference -> Model -> Dataset -> Contributor
        Plus all attached Findings and Evidence nodes.
        """
        if target_node_id not in self.graph:
            return {
                "target": target_node_id,
                "nodes": [],
                "edges": [],
                "trace_summary": f"Target node '{target_node_id}' not found in evidence graph.",
                "converged": False,
                "lifecycle_boundaries": []
            }

        # 1. Reverse traversal: find all upstream ancestors
        ancestors = nx.ancestors(self.graph, target_node_id)
        sub_nodes: Set[str] = set(ancestors)
        sub_nodes.add(target_node_id)

        # 2. Include any findings/evidence directly attached to these nodes
        lifecycle_boundaries = set()
        implicated: Set[str] = set()  # lifecycle layers in the lineage that carry findings
        for n in list(sub_nodes):
            n_type = self.graph.nodes[n].get("type", "").upper()
            if n_type in ["CONTRIBUTOR", "DATASET", "MODEL", "RUNTIME", "INFERENCE"]:
                lifecycle_boundaries.add(n_type)

            for neighbor in self.graph.neighbors(n):
                neighbor_data = self.graph.nodes.get(neighbor, {})
                if neighbor_data.get("type") in ["Finding", "Evidence", "CounterEvidence", "Limitation"]:
                    sub_nodes.add(neighbor)
                    if neighbor_data.get("type") == "Finding" and n_type in ["DATASET", "MODEL", "RUNTIME", "INFERENCE"]:
                        implicated.add(n_type)

        # 3. Build induced subgraph
        subgraph = self.graph.subgraph(sub_nodes)

        nodes_out = [
            {
                "id": n,
                "label": subgraph.nodes[n].get("label", n),
                "type": subgraph.nodes[n].get("type"),
                "status": subgraph.nodes[n].get("status"),
                "details": subgraph.nodes[n].get("details", {})
            }
            for n in subgraph.nodes()
        ]

        edges_out = [
            {
                "source": u,
                "target": v,
                "relationship": subgraph.edges[u, v].get("relationship"),
                "epistemic_status": subgraph.edges[u, v].get("epistemic_status"),
                "evidence_ids": subgraph.edges[u, v].get("evidence_ids", [])
            }
            for u, v in subgraph.edges()
        ]

        # Multi-path convergence: findings on >= 2 distinct lifecycle layers of this lineage
        converged = len(implicated) >= 2

        summary = (
            f"Reverse lineage trace reconstructed {len(nodes_out)} correlated assets and findings. "
            + (f"Findings on {len(implicated)} lifecycle layers ({', '.join(sorted(implicated))}) converge on '{target_node_id}'."
               if converged else f"Findings confined to {', '.join(sorted(implicated)) or 'no'} layer(s) of this lineage.")
        )

        return {
            "target": target_node_id,
            "nodes": nodes_out,
            "edges": edges_out,
            "trace_summary": summary,
            "lineage_summary": summary,
            "converged": converged,
            "lifecycle_boundaries": sorted(list(lifecycle_boundaries)),
            "implicated_layers": sorted(implicated),
        }

    def analyze_cross_lifecycle_convergence(self, case_findings: List[Any]) -> Dict[str, Any]:
        """
        Implements Requirement 14: Structured Cross-Lifecycle Evidence Correlation.
        Answers:
        - Which evidence paths converge?
        - Which asset do they implicate?
        - Which lifecycle boundaries are involved?
        """
        implicated_assets: Dict[str, Set[str]] = {} # asset_id -> set of lifecycle boundaries
        supporting_paths: List[Dict[str, Any]] = []

        for f in case_findings:
            # (fixed: the previous conditional-expression precedence made every ORM finding "UNKNOWN"/"FINDING")
            asset_id = (f.get("asset_id") if isinstance(f, dict) else getattr(f, "asset_id", None)) or "UNKNOWN"
            finding_type = (f.get("finding_type") if isinstance(f, dict) else getattr(f, "finding_type", None)) or "FINDING"
            severity = (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", None)) or "MEDIUM"
            asset_type = (f.get("asset_type") if isinstance(f, dict) else getattr(f, "asset_type", None))

            # Determine lifecycle boundary
            boundary = asset_type or "SYSTEM"
            if asset_type:
                pass
            elif "DUPLICATE" in finding_type or "LABEL" in finding_type or "IMBALANCE" in finding_type or "MALFORMED" in finding_type:
                boundary = "DATASET"
            elif "TRIGGER" in finding_type or "MODEL" in finding_type or "BEHAVIORAL" in finding_type:
                boundary = "MODEL"
            elif "SIGNATURE" in finding_type or "REPLAY" in finding_type or "SEQUENCE" in finding_type:
                boundary = "INFERENCE"
            elif "SHIFT" in finding_type or "DRIFT" in finding_type:
                boundary = "RUNTIME"

            implicated_assets.setdefault(asset_id, set()).add(boundary)
            supporting_paths.append({
                "asset_id": asset_id,
                "lifecycle_boundary": boundary,
                "finding_type": finding_type,
                "severity": severity
            })

        # Check convergence
        all_boundaries = set()
        for b_set in implicated_assets.values():
            all_boundaries.update(b_set)

        converged = len(all_boundaries) >= 2

        return {
            "converged": converged,
            "target_assets": list(implicated_assets.keys()),
            "lifecycle_boundaries": sorted(list(all_boundaries)),
            "supporting_paths": supporting_paths,
            "convergence_summary": (
                f"Multi-path convergence CONFIRMED across {len(all_boundaries)} boundaries ({', '.join(sorted(list(all_boundaries)))})."
                if converged else "Single-boundary findings observed; no cross-lifecycle convergence."
            )
        }
