# ==============================================================================
# Dockerfile - IoT-Based Smart Energy Monitoring and Management System
# DevSecOps Hardened Production Image
# Base: Python 3.12 slim on Debian 13 (Trixie Stable)
# ==============================================================================

# 1. Base Image: Supported official Python 3.12 slim image (Debian 13 Trixie Stable)
# Eliminates Debian 12 unpatched CRITICAL CVEs (libsqlite3-0 and zlib1g)
FROM python:3.12-slim

# Metadata
LABEL maintainer="Vishwajeet <https://github.com/vishwajeet1210>" \
      description="IoT-Based Smart Energy Monitoring and Management System" \
      version="1.0.0"

# 2. Environment Variables
# Prevents Python from writing pyc files to disk and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 3. Install security patches and runtime dependencies
# Upgrades installed base system packages to remediate Debian OS vulnerabilities
# curl is used for the container healthcheck
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. Create dedicated non-root user and group (Least Privilege Principle)
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -m -d /app -s /sbin/nologin appuser

# 5. Set working directory
WORKDIR /app

# 6. Copy production requirements first to leverage Docker build cache
COPY requirements.txt .

# 7. Upgrade packaging tools to remediate CVE-2026-24049 (wheel) and CVE-2026-23949 (jaraco.context)
RUN pip install --no-cache-dir --upgrade \
    pip \
    "setuptools>=70.0.0" \
    "wheel>=0.46.2" \
    "jaraco.context>=6.1.0"

# 8. Install Python application runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 9. Copy application code and UI configuration into container
COPY config.py database.py iot_simulator.py analytics.py alerts.py app.py ./
COPY .streamlit/ .streamlit/

# 10. Prepare data directory for SQLite persistence with correct permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app && \
    chmod 755 /app/data

# 11. Declare volume for SQLite data persistence across container restarts
VOLUME ["/app/data"]

# 12. Switch to unprivileged non-root user
USER appuser

# 13. Expose Streamlit default web port
EXPOSE 8501

# 14. Container Healthcheck
# Queries Streamlit internal health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 15. Container entrypoint
ENTRYPOINT ["streamlit", "run", "app.py"]
