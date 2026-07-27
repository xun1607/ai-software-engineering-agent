import matplotlib.pyplot as plt
from typing import List, Dict, Any

class BenchmarkVisualizer:
    """
    Handles plotting performance comparison charts for Agent Benchmarks.
    Single Responsibility Principle (SRP): Dedicated visualization module.
    """
    @staticmethod
    def plot_comparison(results: List[Dict[str, Any]], output_file: str = "benchmark_comparison.png") -> str:
        scenarios = [r["Scenario"] for r in results]
        prompt_tokens = [r["Prompt Tokens"] for r in results]
        total_tokens = [r["Total Tokens"] for r in results]
        latencies = [r["Latency (ms)"] for r in results]
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Chart 1: Token Usage
        axes[0].bar(scenarios, prompt_tokens, label="Prompt Tokens", color="#a3b18a", width=0.4)
        axes[0].bar(
            scenarios, 
            [t - p for t, p in zip(total_tokens, prompt_tokens)], 
            bottom=prompt_tokens, 
            label="Completion Tokens", 
            color="#588157", 
            width=0.4
        )
        axes[0].set_ylabel("Tokens")
        axes[0].set_title("Token Consumption Comparison")
        axes[0].legend()
        axes[0].grid(axis="y", linestyle="--", alpha=0.7)
        
        # Chart 2: Latency
        axes[1].bar(scenarios, latencies, color=["#e07a5f", "#3d5a80"], width=0.4)
        axes[1].set_ylabel("Latency (ms)")
        axes[1].set_title("Total Execution Latency")
        axes[1].grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        plt.close(fig)
        return output_file
