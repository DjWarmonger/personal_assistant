# Multi-stage Dockerfile for NotionAgent REST Server
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install tz_common dependency first
COPY common/src ./tz_common/src
COPY common/pyproject.toml ./tz_common/pyproject.toml
COPY common/setup.py ./tz_common/setup.py

# Install tz_common in editable mode
RUN pip install -e ./tz_common

# Copy requirements and install NotionAgent dependencies
COPY Agents/NotionAgent/requirements.txt .
RUN pip install -r requirements.txt

# Copy NotionAgent source code (maintaining directory structure)
COPY Agents/NotionAgent/Agent ./Agent
COPY Agents/NotionAgent/operations ./operations
COPY Agents/NotionAgent/launcher ./launcher
COPY Agents/NotionAgent/README.md .
COPY Agents/NotionAgent/pyproject.toml .
COPY Agents/NotionAgent/setup.py .

# Install NotionAgent in editable mode
RUN pip install -e .

# Create logs directory
RUN mkdir -p logs

# Set Python path to ensure imports work
ENV PYTHONPATH=/app:/app/tz_common

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# Run the REST server (keep in launcher/ directory)
CMD ["python", "launcher/rest_server.py"]