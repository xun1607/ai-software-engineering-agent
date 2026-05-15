FROM python:3.11-slim

WORKDIR /app

COPY services/agent_orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/agent_orchestrator/ /app/services/agent_orchestrator/

# (Tùy chọn) có thư mục "shared" dùng chung cho các service, copy nốt vào
# COPY shared/ /app/shared/

CMD ["uvicorn", "services.agent_orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]