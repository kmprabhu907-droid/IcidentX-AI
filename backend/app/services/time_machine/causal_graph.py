"""
INCIDENTX AI - Causal Dependency Graph Engine (NetworkX)
Builds topological dependency graphs, traces failure propagation paths,
and measures blast radius scores.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import networkx as nx

from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.time_machine.models import (
    CausalEdge,
    CausalGraphState,
    CausalNode,
)


class CausalGraphBuilder:
    """
    Constructs and analyzes topological causal graphs using NetworkX.
    """

    @classmethod
    def get_base_topology_graph(cls) -> nx.DiGraph:
        """Constructs base directed dependency graph from DemoMesh topology."""
        g = nx.DiGraph()

        # Add nodes with metadata
        for svc_name, defn in demo_mesh.SERVICE_DEFINITIONS.items():
            g.add_node(
                svc_name,
                service_type=defn.get("type", "microservice"),
                label=svc_name,
            )

        # Add directed edges
        for item in demo_mesh.DEPENDENCY_TOPOLOGY:
            src, tgt = item[0], item[1]
            proto = item[2] if len(item) > 2 else "HTTP"
            crit = item[3] if len(item) > 3 else True
            g.add_edge(src, tgt, relationship="calls", protocol=proto, is_critical=crit)

        return g

    @classmethod
    def analyze_incident_causality(
        cls,
        primary_service: str,
        affected_services: List[str],
        phase: str = "INVESTIGATION",
        timestamp: Optional[str] = None,
    ) -> CausalGraphState:
        """
        Calculates failure propagation paths, identifies root cause candidates,
        and scores the structural blast radius across the topology.
        """
        g = cls.get_base_topology_graph()
        aff_set = set(affected_services) | {primary_service}

        # Find failure propagation path using NetworkX
        impacted_path: List[str] = []
        if "api-gateway" in g and primary_service in g:
            try:
                # Find shortest path from entry gateway to root fault
                shortest = nx.shortest_path(g, source="api-gateway", target=primary_service)
                impacted_path = shortest
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                impacted_path = [primary_service]
        else:
            impacted_path = [primary_service]

        # Calculate blast radius: descendants (downstream) + ancestors (upstream affected)
        descendants: Set[str] = set()
        ancestors: Set[str] = set()
        if primary_service in g:
            descendants = nx.descendants(g, primary_service)
            ancestors = nx.ancestors(g, primary_service)

        total_nodes = len(g.nodes)
        blast_nodes = set(aff_set) | descendants | ancestors
        blast_radius_score = min(100.0, (len(blast_nodes) / max(1, total_nodes)) * 100.0)

        # Build annotated nodes
        nodes: List[CausalNode] = []
        for n in g.nodes:
            is_root = (n == primary_service)
            is_aff = (n in aff_set)
            is_path = (n in impacted_path)

            if is_root:
                health = "FAILING"
                anomaly = 95.0
            elif is_aff or is_path:
                health = "DEGRADED"
                anomaly = 65.0
            else:
                health = "HEALTHY"
                anomaly = 5.0

            svc_defn = demo_mesh.SERVICE_DEFINITIONS.get(n, {})
            nodes.append(
                CausalNode(
                    id=n,
                    label=n,
                    service_type=svc_defn.get("type", "microservice"),
                    health_status=health,
                    anomaly_score=anomaly,
                    is_root_cause_candidate=is_root,
                )
            )

        # Build annotated edges
        edges: List[CausalEdge] = []
        for u, v in g.edges:
            # An edge is part of the impact path if both ends are in the impacted path or affected set
            is_imp = (u in impacted_path and v in impacted_path) or (u in aff_set and v in aff_set)
            latency = 180.0 if is_imp else 35.0
            edges.append(
                CausalEdge(
                    source=u,
                    target=v,
                    relationship="calls",
                    latency_ms=latency,
                    is_impact_path=is_imp,
                )
            )

        now_iso = timestamp or datetime.now(timezone.utc).isoformat()
        return CausalGraphState(
            phase=phase,
            timestamp=now_iso,
            nodes=nodes,
            edges=edges,
            impacted_path=impacted_path,
            blast_radius_score=blast_radius_score,
        )
