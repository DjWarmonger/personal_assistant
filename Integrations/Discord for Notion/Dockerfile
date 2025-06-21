FROM python:3.12-slim

WORKDIR /bot

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy bot source code
COPY bot.py .

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /bot
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8081/health')" || exit 1

CMD ["python", "bot.py"] 