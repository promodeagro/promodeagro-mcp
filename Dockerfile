# Multi-stage build for Alert Engine - Optimized for GitHub Actions
FROM python:3.12-slim AS builder

# Install minimal build dependencies 
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt pyproject.toml ./

# Optimize for GitHub Actions - use parallel builds and prefer wheels
ENV MAKEFLAGS="-j$(nproc)"
ENV NPY_NUM_BUILD_JOBS="$(nproc)"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        --prefer-binary \
        --timeout=1200 \
        -r requirements.txt

# Production stage - Slim image for smaller size but GitHub Actions compatibility  
FROM python:3.12-slim AS production

# Install only essential runtime dependencies and create user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1001 alertengine \
    && useradd -u 1001 -g alertengine -s /bin/sh alertengine

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chown -R alertengine:alertengine /app/logs

# Copy only necessary application files
COPY --chown=alertengine:alertengine src/ ./src/
COPY --chown=alertengine:alertengine data/ ./data/
COPY --chown=alertengine:alertengine *.py ./

# Set environment variables
ENV PYTHONPATH=/app/src \
    ALERT_DATA_PATH=/app/data \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_LEVEL=INFO \
    LOG_DIR=/app/logs \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER alertengine

# Health check with minimal footprint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "mcp_http_server.py"]