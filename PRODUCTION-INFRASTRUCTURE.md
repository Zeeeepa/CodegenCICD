# CodegenCICD Production Infrastructure

## 🚀 Overview

This document describes the comprehensive production infrastructure implemented for CodegenCICD, transforming it from a prototype into a production-ready AI-driven development workflow automation system.

## 📋 Infrastructure Components

### 🐳 Containerization & Orchestration

**Docker Infrastructure:**
- Multi-stage Dockerfile with optimized layers
- Production-ready base images with security updates
- System dependencies for browser automation (Playwright)
- Non-root user execution for security
- Health checks and proper signal handling

**Docker Compose Stack:**
- Application server (FastAPI + Gunicorn)
- PostgreSQL database with connection pooling
- Redis for caching and task queues
- Celery workers for background processing
- Nginx reverse proxy with load balancing
- Prometheus + Grafana monitoring stack
- ELK stack for log aggregation (optional)

### 🔐 Security & Authentication

**Authentication System:**
- JWT-based authentication with configurable expiration
- Role-based access control (Admin, User, ReadOnly)
- Password hashing with bcrypt (configurable rounds)
- Token revocation and session management
- Rate limiting and abuse protection

**Security Measures:**
- Input validation and sanitization
- SQL injection prevention
- XSS protection with security headers
- CORS configuration for production
- API endpoint protection
- Secrets management with environment variables

### 📊 Monitoring & Observability

**Metrics Collection:**
- Prometheus metrics for all components
- Custom application metrics (agent runs, API calls)
- System metrics (CPU, memory, disk usage)
- External service monitoring
- Performance tracking with histograms

**Logging:**
- Structured logging with correlation IDs
- Request/response logging with timing
- Error tracking and categorization
- Log aggregation with ELK stack
- Configurable log levels

**Health Checks:**
- Comprehensive health check endpoints
- Database and Redis connectivity checks
- External service validation
- System resource monitoring
- Graceful degradation indicators

### 🛡️ Resilience & Error Recovery

**Circuit Breaker Pattern:**
- Automatic failure detection
- Configurable failure thresholds
- Recovery timeout management
- Half-open state testing
- Service isolation

**Retry Mechanisms:**
- Multiple retry strategies (Fixed, Exponential, Linear, Jitter)
- Configurable retry attempts and delays
- Exception-specific retry logic
- Backoff algorithms with jitter

**Bulkhead Pattern:**
- Resource isolation with semaphores
- Concurrent request limiting
- Timeout management
- Resource pool statistics

**Timeout Management:**
- Operation-level timeouts
- Async operation protection
- Graceful timeout handling
- Resource cleanup

### 🌐 Load Balancing & Reverse Proxy

**Nginx Configuration:**
- SSL/TLS termination (ready for certificates)
- Load balancing across application instances
- Static file serving with caching
- Rate limiting at proxy level
- Security headers injection
- WebSocket support for real-time features

### 📈 Performance Optimization

**Application Performance:**
- Async/await throughout the stack
- Connection pooling for databases
- Redis caching for frequently accessed data
- Optimized Docker images with multi-stage builds
- Gunicorn with multiple workers

**Frontend Optimization:**
- Static asset caching with appropriate headers
- Gzip compression for text assets
- CDN-ready configuration
- Bundle optimization support

## 🏗️ Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Monitoring    │    │   Log Aggregation│
│     (Nginx)     │    │  (Prometheus)   │    │     (ELK)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Application    │    │    Grafana      │    │    Kibana       │
│   (FastAPI)     │    │   Dashboard     │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │     Cache       │    │  Task Queue     │
│ (PostgreSQL)    │    │    (Redis)      │    │   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Deployment Guide

### Prerequisites

1. **System Requirements:**
   - Docker 20.10+ and Docker Compose 2.0+
   - 4GB+ RAM, 20GB+ disk space
   - Linux/macOS/Windows with WSL2

2. **Environment Variables:**
   ```bash
   # Required API tokens
   CODEGEN_API_TOKEN=your_codegen_token
   CODEGEN_ORG_ID=your_org_id
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_key
   
   # Optional Cloudflare (for advanced features)
   CLOUDFLARE_API_KEY=your_cloudflare_key
   CLOUDFLARE_ACCOUNT_ID=your_account_id
   
   # Security
   JWT_SECRET_KEY=your_jwt_secret
   
   # Environment
   ENVIRONMENT=production
   ```

### Quick Start

1. **Clone and Setup:**
   ```bash
   git clone <repository>
   cd CodegenCICD
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy:**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

3. **Verify:**
   ```bash
   ./scripts/test-infrastructure.sh
   ```

### Manual Deployment

1. **Build and Start Services:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

2. **Initialize Database:**
   ```bash
   docker-compose exec app python -c "
   import asyncio
   from backend.database import init_db
   asyncio.run(init_db())
   "
   ```

3. **Verify Health:**
   ```bash
   curl http://localhost:8000/health
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `development` | No |
| `DATABASE_URL` | PostgreSQL connection string | Auto-generated | No |
| `REDIS_URL` | Redis connection string | Auto-generated | No |
| `JWT_SECRET_KEY` | JWT signing secret | `dev-secret` | Yes (prod) |
| `JWT_EXPIRATION_HOURS` | Token expiration time | `24` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` | No |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | `100` | No |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `3600` | No |

### Service Configuration

**Application (Gunicorn):**
- Workers: `CPU_COUNT * 2 + 1`
- Worker class: `uvicorn.workers.UvicornWorker`
- Timeout: 120 seconds
- Keep-alive: 2 seconds

**Database (PostgreSQL):**
- Connection pooling enabled
- Health checks every 10 seconds
- Automatic failover support
- Backup-ready configuration

**Cache (Redis):**
- Memory limit: 256MB
- Eviction policy: `allkeys-lru`
- Persistence enabled
- Health checks every 10 seconds

## 📊 Monitoring & Alerting

### Available Dashboards

1. **Application Dashboard** (http://localhost:3000)
   - Request rates and response times
   - Error rates and status codes
   - Active agent runs and queue status
   - Database and Redis performance

2. **System Dashboard**
   - CPU, memory, and disk usage
   - Network I/O and connections
   - Container resource utilization
   - Service health status

3. **Business Metrics**
   - Agent run success rates
   - User activity and authentication
   - API usage patterns
   - External service dependencies

### Key Metrics

**Application Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `agent_runs_total` - Total agent runs
- `agent_runs_active` - Active agent runs
- `errors_total` - Error counts by type

**System Metrics:**
- `system_cpu_usage_percent` - CPU utilization
- `system_memory_usage_bytes` - Memory usage
- `database_connections_active` - DB connections
- `redis_connections_active` - Redis connections

### Alerting Rules

**Critical Alerts:**
- Application down (health check fails)
- Database connection failures
- High error rates (>5% for 5 minutes)
- Memory usage >90%
- Disk space <10%

**Warning Alerts:**
- Response time >2 seconds (95th percentile)
- Error rate >1% for 10 minutes
- Memory usage >80%
- Disk space <20%

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Change default passwords and secrets
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable audit logging
- [ ] Configure backup encryption
- [ ] Set up intrusion detection
- [ ] Regular security updates
- [ ] Penetration testing

### Security Headers

The application automatically sets these security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: [configured]`

## 🔄 Backup & Recovery

### Automated Backups

The deployment script automatically creates backups:
- Database dumps before deployments
- Application data snapshots
- Configuration backups
- Log archives

### Recovery Procedures

1. **Database Recovery:**
   ```bash
   docker-compose exec postgres psql -U codegencd -d codegencd < backup.sql
   ```

2. **Application Data Recovery:**
   ```bash
   cp -r backup/data/* ./data/
   docker-compose restart app
   ```

3. **Full System Recovery:**
   ```bash
   ./scripts/deploy.sh restore backup_20240130_120000
   ```

## 📈 Scaling Considerations

### Horizontal Scaling

**Application Tier:**
- Add more app containers behind load balancer
- Configure session affinity if needed
- Scale Celery workers independently

**Database Tier:**
- PostgreSQL read replicas
- Connection pooling optimization
- Query optimization and indexing

**Cache Tier:**
- Redis clustering for high availability
- Cache partitioning strategies
- Memory optimization

### Vertical Scaling

**Resource Allocation:**
- Monitor CPU and memory usage
- Adjust container resource limits
- Optimize worker processes

## 🐛 Troubleshooting

### Common Issues

1. **Application Won't Start:**
   ```bash
   # Check logs
   docker-compose logs app
   
   # Verify environment variables
   docker-compose exec app env | grep CODEGEN
   
   # Test database connection
   docker-compose exec app python -c "from backend.database import test_connection; test_connection()"
   ```

2. **High Memory Usage:**
   ```bash
   # Check container stats
   docker stats
   
   # Analyze memory usage
   docker-compose exec app python -c "import psutil; print(psutil.virtual_memory())"
   ```

3. **Database Connection Issues:**
   ```bash
   # Check PostgreSQL status
   docker-compose exec postgres pg_isready -U codegencd
   
   # View connection logs
   docker-compose logs postgres
   ```

### Performance Tuning

1. **Database Optimization:**
   - Analyze slow queries with `pg_stat_statements`
   - Optimize indexes based on query patterns
   - Tune PostgreSQL configuration

2. **Application Optimization:**
   - Profile with `py-spy` in production
   - Optimize async operations
   - Cache frequently accessed data

3. **System Optimization:**
   - Monitor resource usage patterns
   - Adjust container resource limits
   - Optimize Docker image layers

## 📚 Additional Resources

- [FastAPI Production Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Best Practices](https://redis.io/docs/manual/admin/)
- [Prometheus Monitoring](https://prometheus.io/docs/practices/naming/)
- [Docker Security](https://docs.docker.com/engine/security/)

## 🤝 Contributing

When contributing to the infrastructure:

1. Test changes locally with `./scripts/test-infrastructure.sh`
2. Update documentation for any configuration changes
3. Follow security best practices
4. Add monitoring for new components
5. Update backup procedures if needed

## 📞 Support

For infrastructure issues:
1. Check the troubleshooting guide above
2. Review application logs: `docker-compose logs app`
3. Run infrastructure tests: `./scripts/test-infrastructure.sh`
4. Check monitoring dashboards for system health
5. Create an issue with detailed logs and system information

