# ==============================================================================
# BASE IMAGE
# Use Python 3.11 slim image for a lightweight runtime footprint (~150MB base)
# compared to full Debian images, reducing attack surface and container download time.
# ==============================================================================
FROM python:3.11-slim

# ==============================================================================
# ENVIRONMENT VARIABLES
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc files to disk.
# PYTHONUNBUFFERED=1: Disables stdout/stderr buffering so log output streams
# directly to standard output (`docker logs`) in real-time.
# ==============================================================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ==============================================================================
# WORKSPACE DIRECTORY
# Set working directory inside the container to /app.
# ==============================================================================
WORKDIR /app

# ==============================================================================
# OPTIMIZED LAYER CACHING: DEPENDENCIES STEP
# Copy requirements.txt and run `pip install` BEFORE copying application code.
# Docker caches layer outputs. Since requirements change far less frequently than
# source code, placing this step first ensures `pip install` is cached across 
# subsequent code edits, dramatically speeding up docker rebuild times.
# `--no-cache-dir` prevents pip from storing cache wheels, minimizing image size.
# ==============================================================================
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# APPLICATION SOURCE CODE
# Copy application code into the /app/app directory inside the container.
# ==============================================================================
COPY app/ ./app/

# ==============================================================================
# NON-ROOT USER CREATION (SECURITY BEST PRACTICE)
# Create a dedicated non-root user `appuser` and grant ownership of /app.
# Why? Running container processes as root violates the Principle of Least Privilege.
# If an application vulnerability is exploited, running as non-root prevents host system
# privilege escalation and host filesystem compromise.
# ==============================================================================
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/models && \
    chown -R appuser:appuser /app

USER appuser

# ==============================================================================
# EXPOSE PORT
# Document that the container listens on port 8000.
# ==============================================================================
EXPOSE 8000

# ==============================================================================
# CONTAINER HEALTHCHECK
# Why use Python's built-in `urllib` instead of installing `curl` via apt-get?
# Using Python's standard library avoids installing extra system packages (`apt-get install curl`),
# keeping the container image size minimal, eliminating OS package CVE surface, and speeding up builds.
# ==============================================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ==============================================================================
# CONTAINER ENTRYPOINT COMMAND
# Launch Uvicorn ASGI server bound to 0.0.0.0 (all container interfaces) on port 8000.
# `--reload` is intentionally omitted because this is a production container image.
# ==============================================================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
