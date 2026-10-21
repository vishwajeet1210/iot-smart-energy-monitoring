# ==============================================================================
# Dockerfile - IoT-Based Smart Energy Monitoring and Management System
# Simple, readable single-stage production image for Streamlit application
# Base: Python 3.12 slim on Debian 13 (Trixie)
# ==============================================================================

FROM python:3.12-slim

# Set environment variables for Python and Streamlit
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Apply available security upgrades and clean package caches
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Create application directory and unprivileged user for security (Least Privilege)
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Install Python dependencies
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock

# Copy application source code and configuration
COPY alerts.py analytics.py app.py config.py database.py iot_simulator.py ./

# Prepare data directory for SQLite persistence with appuser ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Declare persistent volume mount point for SQLite database
VOLUME ["/app/data"]

# Switch to non-root user
USER appuser

# Expose Streamlit default web port
EXPOSE 8501

# Healthcheck to verify the web server is responsive (uses Python stdlib urllib)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').getcode() == 200 else 1)"

# Launch the Streamlit dashboard
ENTRYPOINT ["streamlit", "run", "app.py"]
