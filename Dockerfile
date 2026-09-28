# Dockerfile for HydraLite v1.0.0

FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ /app/api/
COPY cli/ /app/cli/
COPY autoscaler/ /app/autoscaler/

# Set Python path so modules can be imported
ENV PYTHONPATH=/app

# Create a non-root user for security
RUN groupadd -r hydralite && useradd -r -g hydralite hydralite \
    && chown -R hydralite:hydralite /app

USER hydralite

# Add healthcheck targeting the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Default command starts the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
