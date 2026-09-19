# Dockerfile for NFT Minting Engine CLI

FROM python:3.11-slim

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

# Copy CLI code
COPY cli/ /app/cli/
COPY tests/ /app/tests/

# Set entrypoint to bash for interactive use or directly to the CLI
CMD ["/bin/bash"]
