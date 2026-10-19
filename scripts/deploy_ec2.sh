#!/usr/bin/env bash
# ==============================================================================
# Smart Energy Monitor - EC2 Deployment Script (Idempotent & Safe)
# Target: Ubuntu 24.04 LTS (AWS Mumbai)
# ==============================================================================
set -Eeuo pipefail

IMAGE_TAR="/home/ubuntu/smart-energy-monitor-11.tar"
EXPECTED_IMAGE_ID="sha256:25dea133bfb0987908475e6b66f0dd7873fd4282247c5f14ce2dcbbd5a271b99"
CONTAINER_NAME="smart-energy-monitor"
IMAGE_TAG="smart-energy-monitor:11"
DATA_DIR="/var/data/energy"
APP_PORT=8501

echo "============================================================"
echo "⚡ Starting Smart Energy Monitor Deployment on EC2"
echo "============================================================"

# ------------------------------------------------------------------------------
# 1. Ensure Docker is installed and running
# ------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    echo "📦 Docker not detected. Installing docker.io and ca-certificates..."
    sudo apt-get update -y
    sudo apt-get install -y docker.io ca-certificates curl
    sudo systemctl enable --now docker
    sudo usermod -aG docker ubuntu || true
else
    echo "✅ Docker is already installed: $(docker --version)"
    sudo systemctl start docker
fi

# ------------------------------------------------------------------------------
# 2. Check and load Docker image from archive
# ------------------------------------------------------------------------------
if [ ! -f "${IMAGE_TAR}" ]; then
    echo "❌ ERROR: Image archive not found at ${IMAGE_TAR}"
    exit 1
fi

echo "🐳 Loading Docker image from archive: ${IMAGE_TAR}..."
sudo docker load -i "${IMAGE_TAR}"

# ------------------------------------------------------------------------------
# 3. Validate image ID and configuration before replacing anything
# ------------------------------------------------------------------------------
LOADED_ID=$(sudo docker inspect --format='{{.Id}}' "${IMAGE_TAG}" 2>/dev/null || true)
echo "🔍 Validating Loaded Image ID: ${LOADED_ID}"

if [ -z "${LOADED_ID}" ]; then
    echo "❌ ERROR: Failed to inspect image tag '${IMAGE_TAG}'."
    exit 1
fi

if [ "${LOADED_ID}" != "${EXPECTED_IMAGE_ID}" ]; then
    echo "❌ ERROR: Image ID mismatch!"
    echo "   Expected: ${EXPECTED_IMAGE_ID}"
    echo "   Actual:   ${LOADED_ID}"
    echo "Deployment aborted before modifying any running container."
    exit 1
fi
echo "✅ Image ID verified successfully."

# Tag as latest for local reference
sudo docker tag "${IMAGE_TAG}" "smart-energy-monitor:latest"

# Validate image configuration (User, Exposed Port, Healthcheck)
IMAGE_USER=$(sudo docker inspect --format='{{.Config.User}}' "${IMAGE_TAG}")
IMAGE_PORT=$(sudo docker inspect --format='{{json .Config.ExposedPorts}}' "${IMAGE_TAG}")
echo "📋 Image Config - User: ${IMAGE_USER:-root}, Exposed Ports: ${IMAGE_PORT}"

# ------------------------------------------------------------------------------
# 4. Safe persistent database directory setup (preserving existing data)
# ------------------------------------------------------------------------------
echo "📁 Checking persistent storage directory at ${DATA_DIR}..."
if [ ! -d "${DATA_DIR}" ]; then
    echo "Creating persistent directory ${DATA_DIR}..."
    sudo mkdir -p "${DATA_DIR}"
fi

# Check existing files
if [ -f "${DATA_DIR}/energy.db" ]; then
    echo "💾 Existing database detected: $(ls -lh "${DATA_DIR}/energy.db")"
    echo "   Preserving existing database file and WAL logs intact."
else
    echo "ℹ️ No existing database file found; it will be initialized by the application."
fi

# Ensure correct non-root permissions for appuser (UID 1001)
DIR_OWNER=$(stat -c '%u:%g' "${DATA_DIR}" 2>/dev/null || echo "unknown")
if [ "${DIR_OWNER}" != "1001:1001" ]; then
    echo "Setting ownership of ${DATA_DIR} to 1001:1001 (appuser)..."
    sudo chown 1001:1001 "${DATA_DIR}"
fi
sudo chmod 755 "${DATA_DIR}"

# Ensure files inside DATA_DIR are writable by appuser if they exist
if compgen -G "${DATA_DIR}/*" >/dev/null; then
    sudo chown 1001:1001 "${DATA_DIR}"/* || true
fi

# ------------------------------------------------------------------------------
# 5. Idempotently replace existing container
# ------------------------------------------------------------------------------
if sudo docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    OLD_STATUS=$(sudo docker inspect --format='{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
    echo "🔄 Existing container '${CONTAINER_NAME}' found (Status: ${OLD_STATUS}). Stopping and removing..."
    sudo docker stop "${CONTAINER_NAME}" || true
    sudo docker rm -f "${CONTAINER_NAME}" || true
fi

# ------------------------------------------------------------------------------
# 6. Launch new container with security settings & persistence
# ------------------------------------------------------------------------------
echo "🚀 Launching container '${CONTAINER_NAME}' on port ${APP_PORT}..."
sudo docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${APP_PORT}:8501" \
    -v "${DATA_DIR}:/app/data" \
    -e ENERGY_DB_DIR=/app/data \
    -e ENERGY_DB_PATH=/app/data/energy.db \
    "${IMAGE_TAG}"

# ------------------------------------------------------------------------------
# 7. Poll container health status
# ------------------------------------------------------------------------------
echo "⏳ Waiting for container to report healthy status (max 60s)..."
HEALTH_OK=false
for i in $(seq 1 30); do
    STATUS=$(sudo docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || true)
    RUNNING=$(sudo docker inspect --format='{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)

    if [ "${STATUS}" = "healthy" ]; then
        echo "✅ Container is healthy after ${i} checks (~$((i * 2))s)."
        HEALTH_OK=true
        break
    fi

    if [ "${RUNNING}" != "true" ]; then
        echo "❌ Container exited unexpectedly during startup!"
        break
    fi

    echo "   [Check ${i}/30] Status: ${STATUS:-starting} (waiting 2s)..."
    sleep 2
done

if [ "${HEALTH_OK}" != "true" ]; then
    echo "❌ ERROR: Container failed healthcheck. Final health status: ${STATUS:-unknown}"
    echo "--- Last 50 lines of container logs ---"
    sudo docker logs --tail 50 "${CONTAINER_NAME}" || true
    echo "--- Persistent storage state ---"
    sudo ls -la "${DATA_DIR}" || true
    echo "Persistent data remains preserved."
    exit 1
fi

# ------------------------------------------------------------------------------
# 8. Verify local HTTP health endpoint
# ------------------------------------------------------------------------------
echo "🌐 Verifying local HTTP health endpoint (http://127.0.0.1:${APP_PORT}/_stcore/health)..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${APP_PORT}/_stcore/health" || echo "failed")
if [ "${HTTP_RESPONSE}" = "200" ]; then
    echo "✅ Local HTTP health endpoint returned HTTP 200 OK."
else
    echo "❌ Local HTTP health endpoint returned unexpected response: ${HTTP_RESPONSE}"
    sudo docker logs --tail 30 "${CONTAINER_NAME}" || true
    exit 1
fi

# ------------------------------------------------------------------------------
# 9. Final Deployment Summary
# ------------------------------------------------------------------------------
echo "============================================================"
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "============================================================"
sudo docker inspect --format='Container: {{.Name}} | Status: {{.State.Status}} | Health: {{.State.Health.Status}} | ImageID: {{.Image}}' "${CONTAINER_NAME}"
echo "Port mappings:"
sudo docker port "${CONTAINER_NAME}"
echo "Persistent storage listing:"
sudo ls -la "${DATA_DIR}"
echo "Local healthcheck response:"
curl -s "http://127.0.0.1:${APP_PORT}/_stcore/health" || true
echo ""
echo "============================================================"
