# Dockerfile for NFT Minting Engine CLI

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements (if any, will add later) and install dependencies
# check for requirements.txt existence before COPY or just create dummy for now?
# I'll create a setup.py or pyproject.toml later. For now, just copy the cli folder.

# Copy CLI code
COPY cli/ /app/cli/
COPY tests/ /app/tests/

# Install python dependencies (placeholder for now, will use pip install)
# RUN pip install -r requirements.txt
RUN pip install click requests websockets cardano-clusterlib pycardano

# Set entrypoint to bash for interactive use or directly to the CLI
CMD ["/bin/bash"]
