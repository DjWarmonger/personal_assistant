# UV-based Dockerfile for NotionAgent REST Server
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Create the exact same venv name used in development
RUN uv venv /opt/.venv_uv_tz
ENV PATH="/opt/.venv_uv_tz/bin:$PATH"

# Copy dependency manifests first for better layer caching
COPY Agents/NotionAgent/pyproject.toml ./
COPY Agents/NotionAgent/requirements.txt ./

# Install runtime dependencies via uv into the venv
RUN uv pip install -r requirements.txt

# Copy tz_common source code with proper structure
COPY common/src ./tz_common/src
COPY common/pyproject.toml ./tz_common/pyproject.toml
COPY common/setup.py ./tz_common/setup.py
COPY common/README.md ./tz_common/README.md

# Copy NotionAgent source code (maintaining directory structure)
COPY Agents/NotionAgent/Agent ./Agent
COPY Agents/NotionAgent/operations ./operations
COPY Agents/NotionAgent/launcher ./launcher
COPY Agents/NotionAgent/README.md .
COPY Agents/NotionAgent/setup.py .

# Create a production-optimized pyproject.toml without tests in packages
RUN sed 's/, "tests"//g; s/"tests", //g' pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml

# Install both packages in editable mode using uv
# tz_common needs to be installed from the directory containing pyproject.toml
RUN uv pip install -e ./tz_common
RUN uv pip install -e .

# Create logs directory
RUN mkdir -p logs

# Set Python path to ensure imports work
ENV PYTHONPATH=/app:/app/tz_common

# Expose port
EXPOSE 8000

# Health check (venv already active via PATH)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# Run the REST server (keep in launcher/ directory, venv already active)
CMD ["python", "launcher/rest_server.py"]