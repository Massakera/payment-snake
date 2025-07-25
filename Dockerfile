# Multi-stage build for minimal image size and maximum performance
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create a non-root user to run the application
RUN useradd -m -d /home/app -u 1000 app

# Set PATH to include user's local bin directory, must be done before switching user
ENV PATH="/home/app/.local/bin:${PATH}"

# Switch to the new user. All subsequent commands run as 'app'
USER app
WORKDIR /home/app

# Copy Python packages from builder stage, and set ownership
COPY --chown=app:app --from=builder /root/.local /home/app/.local

# Copy application code, and set ownership
COPY --chown=app:app app/ ./app/
COPY --chown=app:app gunicorn.conf.py .

# Pre-compile Python bytecode for faster startup
RUN python -m compileall .

# Health check using http.client to avoid extra dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys, http.client; conn = http.client.HTTPConnection('localhost', 8000); \
    try: conn.request('GET', '/health'); r = conn.getresponse(); sys.exit(0) if r.status == 200 else sys.exit(1); \
    finally: conn.close()"

# Expose port
EXPOSE 8000

# Run with Gunicorn for maximum performance
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"] 