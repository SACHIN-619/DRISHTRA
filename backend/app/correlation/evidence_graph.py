"""
DRISHTRA Correlation Engine - Cross-Lifecycle Evidence Graph
Constructs a typed, epistemically rigorous knowledge graph connecting:
Contributor -> Dataset -> Batch -> Model -> Runtime -> Inference -> Findings -> Evidence

Epistemic Status Categories:
- OBSERVED: Directly recorded telemetry / cryptographic record
- DERIVED: Algorithmically computed from raw data (e.g. hash, feature centroid)
- SUPPORTS: Evidence reinforces an integrity hypothesis
- CORRELATES: Statistical or temporal co-occurrence without direct causality
- UNKNOWN: Unverified or missing connection
"""
from typing import Dict, Any, List, Optional
import networkx as nx
from app.schemas.all_schemas import GraphNode, GraphEdge, EvidenceGraphResponse

class EvidenceGraphBuilder:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.graph = nx.DiGraph()

    def add_node(self, node_id: str, label: str, node_type: str, status: str = "NORMAL", details: Optional[Dict[str, Any]] = None):
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
        Reconstructs the explanatory path for:
        "WHY WAS THIS RESULT FLAGGED?"
        Dynamically extracts all ancestor contributors, datasets, models, and correlated findings.
        """
        if target_node_id not in self.graph:
            return {"error": f"Node {target_node_id} not in evidence graph"}

        # Ancestors via reverse BFS / lineage
        ancestors = nx.ancestors(self.graph, target_node_id)
        sub_nodes = set(ancestors)
        sub_nodes.add(target_node_id)
        
        # Also include any direct findings connected to these nodes
        for n in list(sub_nodes):
            for neighbor in self.graph.neighbors(n):
                if self.graph.nodes[neighbor].get("type") in ["Finding", "Evidence"]:
                    sub_nodes.add(neighbor)

        subgraph = self.graph.subgraph(sub_nodes)
        
        nodes_out = [
            {
                "id": n,
                "label": subgraph.nodes[n].get("label", n),
                "type": subgraph.nodes[n].get("type"),
                "status": subgraph.nodes[n].get("status"),
                "details": subgraph.nodes[n].get("details")
            }
            for n in subgraph.nodes()
        ]
        
        edges_out = [
            {
                "source": u,
                "target": v,
                "relationship": subgraph.edges[u, v].get("relationship"),
                "epistemic_status": subgraph.edges[u, v].get("epistemic_status"),
                "evidence_ids": subgraph.edges[u, v].get("evidence_ids")
            }
            for u, v in subgraph.edges()
        ]

        return {
            "target": target_node_id,
            "nodes": nodes_out,
            "edges": edges_out,
            "trace_summary": f"Lineage trace reconstructed {len(nodes_out)} correlated assets and findings."
        }
