import sys
import os
import csv

# Add backend folder to sys.path to resolve imports cleanly
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from shared.db import get_session
from services.skill_testing.models import AgentExecutionLog

def main():
    print("[INFO] [EXPORT RESULTS] Querying SQLite for Execution Logs...")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, "benchmark_results")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, "execution_logs.csv")
    
    try:
        with get_session() as session:
            # Query all logs ordered by creation time
            logs = session.query(AgentExecutionLog).order_by(AgentExecutionLog.created_at.desc()).all()
            
            if not logs:
                print("[WARNING] No logs found in agent_execution_logs table.")
                return
                
            fields = [
                "id", "task_id", "task_type", "skill_name", "baseline_mode", 
                "success", "quality", "latency_ms", "total_tokens", "cost", "created_at"
            ]
            
            # Write while session is open to avoid detached instance errors
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fields)
                for log in logs:
                    writer.writerow([
                        log.id, log.task_id, log.task_type, log.skill_name, log.baseline_mode,
                        log.success, f"{log.quality:.4f}", log.latency_ms, log.total_tokens,
                        f"{log.cost:.6f}", log.created_at.isoformat() if log.created_at else ""
                    ])
                    
        print(f"[SUCCESS] Exported {len(logs)} execution records to: {csv_path}")
        
    except Exception as e:
        print(f"[ERROR] Failed to export logs: {e}")

if __name__ == "__main__":
    main()
