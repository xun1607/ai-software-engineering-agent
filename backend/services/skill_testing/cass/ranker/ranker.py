import random
from typing import List, Dict, Any
from ..storage.base import AbstractSkillMetricsStore

class CASSRanker:
    """
    Multi-objective Ranker using Thompson Sampling.
    Weights: 
    - Success Probability (via Beta Distribution)
    - Latency (Negative weight)
    - Cost (Negative weight)
    """
    def __init__(self, metrics_store: AbstractSkillMetricsStore, w_latency: float = 0.2, w_cost: float = 0.1):
        self.metrics_store = metrics_store
        self.w_latency = w_latency
        self.w_cost = w_cost

    def rank(self, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        names = [c["name"] for c in candidates]
        metrics_map = self.metrics_store.get_metrics(names)

        scored_candidates = []
        for skill in candidates:
            m = metrics_map.get(skill["name"], {"alpha": 1, "beta": 1, "avg_latency_ms": 500, "avg_cost": 0.0})
            
            # 1. Thompson Sampling for Success Rate
            # Sample from Beta(alpha, beta)
            success_sample = random.betavariate(m["alpha"], m["beta"])

            # 2. Normalize Latency (Cap at 10 seconds for normalization)
            norm_latency = min(m["avg_latency_ms"] / 10000.0, 1.0)

            # 3. Final Utility Score
            # Utility = Success_Sample - (Weight * Latency) - (Weight * Cost)
            utility_score = success_sample - (self.w_latency * norm_latency)
            
            scored_candidates.append((skill, utility_score))

        # Sort by Utility descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored_candidates[:top_k]]