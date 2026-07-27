import sqlite3
import threading
from typing import List, Dict, Any, Optional
from .base import AbstractTelemetryStore, AbstractSkillMetricsStore, ExecutionRecord

class SQLiteDBManager(AbstractTelemetryStore, AbstractSkillMetricsStore):
    """
    SQLite manager for CASS
    Uses Write-Ahead Logging (WAL) and thread-locking for safe concurrent access
    """

    def __init__(self, db_path: str = "cass_experience.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a new connection with row factory enabled"""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self):
        """Sets up tables for raw logs and cumulative metrics"""
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA journal_mode=WAL;")  # Enable concurrent read/write
            # Table 1: Raw History
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    cost REAL NOT NULL,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Table 2: Cumulative Metrics 
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_reputation (
                    skill_name TEXT PRIMARY KEY,
                    alpha INTEGER DEFAULT 1,     -- Success count + 1 (Prior)
                    beta INTEGER DEFAULT 1,      -- Failure count + 1 (Prior)
                    avg_latency_ms REAL DEFAULT 0.0,
                    avg_cost REAL DEFAULT 0.0,
                    total_runs INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_log(self, record: ExecutionRecord) -> None:
        """Saves detailed event to history."""
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    "INSERT INTO execution_history (session_id, skill_name, latency_ms, cost, success, error_message) VALUES (?, ?, ?, ?, ?, ?)",
                    (record.session_id, record.skill_name, record.latency_ms, record.cost, 1 if record.success else 0, record.error_message)
                )
                conn.commit()
            finally:
                conn.close()

    def get_metrics(self, skill_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Retrieves reputation data for ranking."""
        if not skill_names:
            return {}
        
        placeholders = ",".join("?" for _ in skill_names)
        query = f"SELECT * FROM skill_reputation WHERE skill_name IN ({placeholders})"
        
        result = {}
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, skill_names)
            for row in cursor.fetchall():
                result[row["skill_name"]] = dict(row)
        finally:
            conn.close()
        return result

    def update_metrics(self, skill_name: str, latency_ms: float, cost: float, success: bool) -> None:
        """
        Atomic update of reputation scores.
        Uses Bayesian Beta distribution updates (Success -> Alpha++, Failure -> Beta++).
        """
        s_inc = 1 if success else 0
        f_inc = 0 if success else 1
        
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                        INSERT INTO skill_reputation (skill_name, alpha, beta, avg_latency_ms, avg_cost, total_runs)
                        VALUES (?, 1+?, 1+?, ?, ?, 1)
                        ON CONFLICT(skill_name) DO UPDATE SET
                            alpha = alpha + ?,
                            beta = beta + ?,
                            avg_latency_ms = (avg_latency_ms * total_runs + ?) / (total_runs + 1),
                            avg_cost = (avg_cost * total_runs + ?) / (total_runs + 1),
                            total_runs = total_runs + 1
                    """, (skill_name, s_inc, f_inc, latency_ms, cost, s_inc, f_inc, latency_ms, cost))
                conn.commit()
            finally:
                conn.close()

    def get_recent_logs(self, skill_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM execution_history WHERE skill_name = ? ORDER BY timestamp DESC LIMIT ?",
                (skill_name, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()