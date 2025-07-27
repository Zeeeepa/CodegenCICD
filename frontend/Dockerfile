# =============================================================================
# CodegenCICD Frontend - Multi-stage React Build
# Optimized for production deployment with Nginx serving
# =============================================================================

# =============================================================================
# Build Stage - Node.js Build Environment
# =============================================================================
FROM node:18-alpine as builder

# Set build arguments
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_WS_URL=ws://localhost:8000
ARG BUILD_DATE
ARG VERSION=latest
ARG VCS_REF

# Set environment variables
ENV NODE_ENV=production \
    REACT_APP_API_URL=${REACT_APP_API_URL} \
    REACT_APP_WS_URL=${REACT_APP_WS_URL}

# Install system dependencies
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++

# Create app directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY frontend/ .

# Build the application
RUN npm run build

# =============================================================================
# Production Stage - Nginx Static Server
# =============================================================================
FROM nginx:alpine as production

# Set build arguments
ARG BUILD_DATE
ARG VERSION=latest
ARG VCS_REF

# Add metadata labels
LABEL maintainer="CodegenCICD Team" \
      org.opencontainers.image.title="CodegenCICD Frontend" \
      org.opencontainers.image.description="Frontend dashboard for CodegenCICD" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/Zeeeepa/CodegenCICD"

# Install additional tools
RUN apk add --no-cache \
    curl \
    ca-certificates

# Copy built application from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Create nginx user and set permissions
RUN addgroup -g 1000 -S appuser && \
    adduser -u 1000 -S appuser -G appuser && \
    chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /var/run /var/log/nginx

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# =============================================================================
# Development Stage - Node.js Development Server
# =============================================================================
FROM node:18-alpine as development

# Set environment variables
ENV NODE_ENV=development \
    CHOKIDAR_USEPOLLING=true

# Install system dependencies
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++

# Create app directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install all dependencies (including dev)
RUN npm install --silent

# Copy source code
COPY frontend/ .

# Expose port
EXPOSE 3000

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start development server
CMD ["npm", "start"]

# =============================================================================
# Testing Stage - Node.js Testing Environment
# =============================================================================
FROM development as testing

# Install additional testing tools
RUN npm install --save-dev \
    @testing-library/jest-dom \
    @testing-library/react \
    @testing-library/user-event \
    jest-environment-jsdom

# Copy test files
COPY frontend/src/ ./src/
COPY frontend/public/ ./public/

# Run tests
CMD ["npm", "test", "--", "--coverage", "--watchAll=false"]

# =============================================================================
# Build Instructions and Usage Examples
# =============================================================================

# Build production image:
# docker build --target production -t codegencd-frontend:latest frontend/

# Build development image:
# docker build --target development -t codegencd-frontend:dev frontend/

# Build testing image:
# docker build --target testing -t codegencd-frontend:test frontend/

# Run production:
# docker run -p 3000:3000 codegencd-frontend:latest

# Run development with volume mounting:
# docker run -v $(pwd)/frontend:/app -p 3000:3000 codegencd-frontend:dev

# Run tests:
# docker run --rm codegencd-frontend:test

