# Multi-stage Dockerfile for CodegenCICD production deployment
FROM node:18-bullseye-slim as node-base

# Install system dependencies for browser automation
RUN apt-get update && apt-get install -y \
    # Browser dependencies
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # Additional dependencies
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libgconf-2-4 \
    # System utilities
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    # Python build dependencies
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome/Chromium
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Python stage
FROM node-base as python-stage

# Set Python environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python requirements first for better caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -r backend/requirements.txt

# Install additional production dependencies
RUN pip3 install --no-cache-dir \
    gunicorn \
    uvicorn[standard] \
    prometheus-client \
    structlog \
    python-json-logger \
    redis \
    celery \
    psycopg2-binary

# Frontend build stage
FROM node-base as frontend-build

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Final production stage
FROM python-stage as production

# Copy application code
COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy configuration files
COPY docker/ /app/docker/
COPY scripts/ /app/scripts/

# Install Playwright and browsers
RUN pip3 install playwright \
    && playwright install chromium \
    && playwright install-deps

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R appuser:appuser /app

# Copy entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Health check
COPY docker/healthcheck.py /app/healthcheck.py
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 /app/healthcheck.py

# Expose ports
EXPOSE 8000 8001 8002

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV ENVIRONMENT=production

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/docker/gunicorn.conf.py", "backend.main:app"]

