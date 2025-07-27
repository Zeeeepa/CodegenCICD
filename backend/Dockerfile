# =============================================================================
# CodegenCICD Backend - Multi-stage Docker Build
# Optimized for production deployment with security and performance
# =============================================================================

# =============================================================================
# Build Stage - Dependencies and Application Setup
# =============================================================================
FROM python:3.11-slim as builder

# Set build arguments
ARG CONFIG_TIER=basic
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .
COPY . /app/

# Set proper permissions
RUN chown -R appuser:appuser /app

# =============================================================================
# Production Stage - Minimal Runtime Image
# =============================================================================
FROM python:3.11-slim as production

# Set build arguments
ARG CONFIG_TIER=basic
ARG BUILD_DATE
ARG VERSION=latest
ARG VCS_REF

# Add metadata labels
LABEL maintainer="CodegenCICD Team" \
      org.opencontainers.image.title="CodegenCICD Backend" \
      org.opencontainers.image.description="Backend service for CodegenCICD Dashboard" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/Zeeeepa/CodegenCICD" \
      config.tier="${CONFIG_TIER}"

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    CONFIG_TIER=${CONFIG_TIER} \
    ENVIRONMENT=production \
    PORT=8000

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Create application directories
RUN mkdir -p /app /tmp/grainchain_workspaces /tmp/validation_workspaces && \
    chown -R appuser:appuser /app /tmp/grainchain_workspaces /tmp/validation_workspaces

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY --from=builder --chown=appuser:appuser /app /app

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Development Stage - Extended with development tools
# =============================================================================
FROM production as development

# Switch back to root for installing dev dependencies
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    bandit \
    debugpy \
    ipython

# Switch back to appuser
USER appuser

# Override command for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# =============================================================================
# Testing Stage - Optimized for CI/CD testing
# =============================================================================
FROM development as testing

# Switch to root for test setup
USER root

# Install additional testing tools
RUN pip install --no-cache-dir \
    coverage \
    pytest-xdist \
    pytest-mock \
    httpx \
    faker

# Copy test files
COPY tests/ /app/tests/

# Set proper permissions
RUN chown -R appuser:appuser /app/tests

# Switch back to appuser
USER appuser

# Default test command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=backend", "--cov-report=xml", "--cov-report=html"]

# =============================================================================
# Build Instructions and Usage Examples
# =============================================================================

# Build production image:
# docker build --target production -t codegencd-backend:latest backend/

# Build development image:
# docker build --target development -t codegencd-backend:dev backend/

# Build testing image:
# docker build --target testing -t codegencd-backend:test backend/

# Run with different configurations:
# docker run -e CONFIG_TIER=basic codegencd-backend:latest
# docker run -e CONFIG_TIER=intermediate codegencd-backend:latest
# docker run -e CONFIG_TIER=advanced codegencd-backend:latest

# Development with volume mounting:
# docker run -v $(pwd):/app -p 8000:8000 codegencd-backend:dev

# Run tests:
# docker run --rm codegencd-backend:test

