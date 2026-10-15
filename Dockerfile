# ==============================================================================
# Dockerfile - IoT-Based Smart Energy Monitoring and Management System
# DevSecOps Hardened Multi-Stage Production Image
# Base: Python 3.12 slim on Debian 13 (Trixie Stable)
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Builder Stage
# Installs runtime dependencies into an isolated virtual environment
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install OS updates and any essential packaging prerequisites
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools in builder stage ONLY for secure wheel resolution
RUN pip install --no-cache-dir --upgrade pip "setuptools>=70.0.0" "wheel>=0.46.2"

# Create a dedicated virtual environment for runtime dependencies
RUN python -m venv /opt/venv

# Install application dependencies into the virtual environment using builder's pip
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Remove build/package management tools from the virtual environment before copying
RUN /opt/venv/bin/pip uninstall -y pip setuptools wheel 2>/dev/null || true && \
    rm -rf /opt/venv/bin/pip* \
           /opt/venv/lib/python3.12/site-packages/pip* \
           /opt/venv/lib/python3.12/site-packages/setuptools* \
           /opt/venv/lib/python3.12/site-packages/wheel*

# ------------------------------------------------------------------------------
# STAGE 2: Runtime Stage
# Hardened, minimal execution environment free of build tools and package managers
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Metadata
LABEL maintainer="Vishwajeet <https://github.com/vishwajeet1210>" \
      description="IoT-Based Smart Energy Monitoring and Management System" \
      version="1.0.0"

# Environment Variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install security patches for Debian OS packages and curl for health check
# Purge base image pip, ensurepip, and build tool remnants from runtime image
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /usr/local/lib/python3.12/site-packages/pip* \
           /usr/local/lib/python3.12/ensurepip \
           /usr/local/bin/pip*

# Create dedicated non-root user and group (Least Privilege Principle)
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -m -d /app -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy isolated virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code and UI configuration into container
COPY config.py database.py iot_simulator.py analytics.py alerts.py app.py ./
COPY .streamlit/ .streamlit/

# Prepare data directory for SQLite persistence with correct permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app && \
    chmod 755 /app/data

# Declare volume for SQLite data persistence across container restarts
VOLUME ["/app/data"]

# Switch to unprivileged non-root user
USER appuser

# Expose Streamlit default web port
EXPOSE 8501

# Container Healthcheck queries Streamlit internal health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Container entrypoint
ENTRYPOINT ["streamlit", "run", "app.py"]
