from typing import Any
from ..storage.base import AbstractTelemetryStore, AbstractSkillMetricsStore, ExecutionRecord

class PerformanceObserver:
    """
    Coordinates telemetry data flow. 
    Receives raw records and triggers both logging and metric updates.
    """
    def __init__(self, telemetry_store: AbstractTelemetryStore, metrics_store: AbstractSkillMetricsStore):
        self.telemetry_store = telemetry_store
        self.metrics_store = metrics_store

    def report_execution(self, record: ExecutionRecord) -> None:
        """Saves logs and updates aggregated reputation metrics."""
        self.telemetry_store.save_log(record)
        
        self.metrics_store.update_metrics(
            skill_name=record.skill_name,
            latency_ms=record.latency_ms,
            cost=record.cost,
            success=record.success
        )