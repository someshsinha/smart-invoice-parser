# Dockerfile for Smart Invoice Header Extraction Service
# Alternative execution path adhering to constraints C1, C2, C3, C4, C5

FROM python:3.11-slim

# Set environment variables for clean container execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install minimal system dependencies (curl for container healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pinned Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY app/ app/
COPY static/ static/
COPY samples/ samples/
COPY generator/fonts/ generator/fonts/

# Expose service port 8000
EXPOSE 8000

# Container healthcheck against /health endpoint
HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=5s \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn ASGI server on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
