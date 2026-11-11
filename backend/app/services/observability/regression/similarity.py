"""
INCIDENTX AI - Incident Similarity Engine
Implements weighted Jaccard set similarity, cosine metric vector similarity,
topological graph similarity, and error signature token matching.
Combines scores into an explainable similarity metric in [0.0, 1.0].
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.services.observability.regression.fingerprint import IncidentFingerprint


@dataclass
class SimilarityResult:
    """Detailed explainable breakdown of multi-dimensional similarity."""
    overall_similarity_score: float
    services_similarity: float
    metric_vector_similarity: float
    root_cause_similarity: float
    topology_path_similarity: float
    error_signature_similarity: float
    weights_used: Dict[str, float]
    shared_services: List[str] = field(default_factory=list)
    shared_metrics: List[str] = field(default_factory=list)
    shared_root_causes: List[str] = field(default_factory=list)
    shared_error_signatures: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_similarity_score": round(self.overall_similarity_score, 3),
            "services_similarity": round(self.services_similarity, 3),
            "metric_vector_similarity": round(self.metric_vector_similarity, 3),
            "root_cause_similarity": round(self.root_cause_similarity, 3),
            "topology_path_similarity": round(self.topology_path_similarity, 3),
            "error_signature_similarity": round(self.error_signature_similarity, 3),
            "weights_used": self.weights_used,
            "shared_services": self.shared_services,
            "shared_metrics": self.shared_metrics,
            "shared_root_causes": self.shared_root_causes,
            "shared_error_signatures": self.shared_error_signatures,
            "explanation": self.explanation,
        }


class IncidentSimilarityEngine:
    """
    Computes explainable, multi-dimensional similarity between incident fingerprints.
    """

    DEFAULT_WEIGHTS = {
        "services": 0.25,
        "metrics": 0.25,
        "root_cause": 0.20,
        "topology": 0.15,
        "errors": 0.15,
    }

    @staticmethod
    def weighted_jaccard(
        set_a: Set[str],
        set_b: Set[str],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Computes weighted Jaccard similarity.
        Rule: If both sets are empty, returns 0.0 (missing data is NOT matching evidence).
        """
        if not set_a and not set_b:
            return 0.0
        if not set_a or not set_b:
            return 0.0

        intersection = set_a & set_b
        union = set_a | set_b

        if not union:
            return 0.0

        if weights:
            num = sum(weights.get(item, 1.0) for item in intersection)
            den = sum(weights.get(item, 1.0) for item in union)
            return (num / den) if den > 0 else 0.0

        return len(intersection) / len(union)

    @staticmethod
    def cosine_similarity(
        vec_a: Dict[str, float],
        vec_b: Dict[str, float],
    ) -> float:
        """
        Computes cosine similarity between two numerical metric anomaly vectors.
        Rule: If either vector is empty or has zero magnitude, returns 0.0.
        """
        if not vec_a or not vec_b:
            return 0.0

        common_keys = set(vec_a.keys()) & set(vec_b.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(vec_a[k] * vec_b[k] for k in common_keys)
        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a <= 1e-9 or mag_b <= 1e-9:
            return 0.0

        # Bound to [0.0, 1.0] for non-negative anomaly magnitudes
        sim = dot_product / (mag_a * mag_b)
        return max(0.0, min(1.0, sim))

    @staticmethod
    def dependency_graph_similarity(
        subgraph_a: Dict[str, List[str]],
        subgraph_b: Dict[str, List[str]],
        path_a: List[str],
        path_b: List[str],
    ) -> float:
        """
        Computes graph structural similarity combining topological edge overlap
        and propagation sequence alignment.
        """
        if (not subgraph_a and not subgraph_b) and (not path_a and not path_b):
            return 0.0

        # 1. Edge Set Jaccard
        edges_a: Set[Tuple[str, str]] = set()
        for src, targets in subgraph_a.items():
            for tgt in targets:
                edges_a.add((src, tgt))

        edges_b: Set[Tuple[str, str]] = set()
        for src, targets in subgraph_b.items():
            for tgt in targets:
                edges_b.add((src, tgt))

        edge_sim = 0.0
        if edges_a or edges_b:
            inter = len(edges_a & edges_b)
            union = len(edges_a | edges_b)
            edge_sim = inter / union if union > 0 else 0.0

        # 2. Propagation Sequence Alignment (LCS overlap)
        path_sim = 0.0
        if path_a and path_b:
            set_pa = set(path_a)
            set_pb = set(path_b)
            node_overlap = len(set_pa & set_pb) / len(set_pa | set_pb) if (set_pa | set_pb) else 0.0
            
            # Position order alignment
            order_matches = sum(1 for i, node in enumerate(path_a) if i < len(path_b) and path_b[i] == node)
            order_sim = order_matches / max(len(path_a), len(path_b)) if max(len(path_a), len(path_b)) > 0 else 0.0
            path_sim = 0.6 * node_overlap + 0.4 * order_sim

        return (0.5 * edge_sim + 0.5 * path_sim)

    @classmethod
    def compare_fingerprints(
        cls,
        fp_a: IncidentFingerprint,
        fp_b: IncidentFingerprint,
        weights: Optional[Dict[str, float]] = None,
    ) -> SimilarityResult:
        """
        Evaluates full multi-dimensional fingerprint similarity between two incidents.
        """
        w = weights or cls.DEFAULT_WEIGHTS

        # 1. Services similarity
        sim_services = cls.weighted_jaccard(fp_a.affected_services, fp_b.affected_services)
        shared_services = sorted(list(fp_a.affected_services & fp_b.affected_services))

        # Primary service match bonus: if primary culprits match, enhance service similarity
        if fp_a.primary_service and fp_b.primary_service and fp_a.primary_service == fp_b.primary_service:
            sim_services = min(1.0, sim_services * 0.7 + 0.3)

        # 2. Metric anomaly vector similarity (cosine)
        sim_metrics = cls.cosine_similarity(fp_a.metric_anomaly_vector, fp_b.metric_anomaly_vector)
        shared_metrics = sorted(list(set(fp_a.metric_anomaly_vector.keys()) & set(fp_b.metric_anomaly_vector.keys())))

        # 3. Root cause category similarity
        sim_root_cause = cls.weighted_jaccard(fp_a.root_cause_categories, fp_b.root_cause_categories)
        shared_causes = sorted(list(fp_a.root_cause_categories & fp_b.root_cause_categories))

        # 4. Topology and propagation path similarity
        sim_topology = cls.dependency_graph_similarity(
            fp_a.dependency_subgraph,
            fp_b.dependency_subgraph,
            fp_a.failure_propagation_path,
            fp_b.failure_propagation_path,
        )

        # 5. Error signature similarity
        sim_errors = cls.weighted_jaccard(fp_a.error_signatures, fp_b.error_signatures)
        shared_errors = sorted(list(fp_a.error_signatures & fp_b.error_signatures))

        # Compute weighted overall similarity score
        overall = (
            w["services"] * sim_services
            + w["metrics"] * sim_metrics
            + w["root_cause"] * sim_root_cause
            + w["topology"] * sim_topology
            + w["errors"] * sim_errors
        )
        overall = max(0.0, min(1.0, overall))

        # Formulate narrative explanation
        reasons: List[str] = []
        if sim_services >= 0.7:
            reasons.append(f"Strong service overlap on [{', '.join(shared_services)}]")
        elif sim_services > 0.0:
            reasons.append(f"Partial service overlap on [{', '.join(shared_services)}]")

        if sim_metrics >= 0.7:
            reasons.append(f"Concordant anomaly vectors across metrics [{', '.join(shared_metrics)}]")
        elif sim_metrics > 0.0:
            reasons.append(f"Partially shared metric departures on [{', '.join(shared_metrics)}]")

        if sim_root_cause >= 0.6:
            reasons.append(f"Matching root cause taxonomy ({', '.join(shared_causes)})")

        if sim_errors >= 0.5:
            reasons.append(f"Overlapping canonical error signatures ({len(shared_errors)} matching patterns)")

        explanation = "; ".join(reasons) if reasons else "Distinct incident profiles with minimal architectural overlap."

        return SimilarityResult(
            overall_similarity_score=overall,
            services_similarity=sim_services,
            metric_vector_similarity=sim_metrics,
            root_cause_similarity=sim_root_cause,
            topology_path_similarity=sim_topology,
            error_signature_similarity=sim_errors,
            weights_used=w,
            shared_services=shared_services,
            shared_metrics=shared_metrics,
            shared_root_causes=shared_causes,
            shared_error_signatures=shared_errors,
            explanation=explanation,
        )
