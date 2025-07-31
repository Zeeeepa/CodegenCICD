# 🚀 CodegenCICD Integrated Deployment Guide

## 📋 Overview

This guide covers the deployment of the fully integrated CodegenCICD system with all four library integrations:

1. **Grainchain** - Sandbox management and code execution
2. **Graph-sitter** - Code analysis and quality assurance  
3. **Web-eval-agent** - UI testing and browser automation
4. **Codegen SDK** - Agent orchestration and API integration

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Nginx Load Balancer]
    end
    
    subgraph "Application Layer"
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
        API3[FastAPI Instance 3]
    end
    
    subgraph "Service Layer"
        GC[Grainchain Service]
        GS[Graph-sitter Service]
        WE[Web-eval Service]
        CS[Codegen SDK Service]
        IAM[Integrated Agent Manager]
    end
    
    subgraph "Infrastructure Layer"
        PG[(PostgreSQL)]
        RD[(Redis)]
        PR[Prometheus]
        GR[Grafana]
    end
    
    subgraph "External Services"
        E2B[E2B Sandboxes]
        GEM[Gemini API]
        CGN[Codegen API]
        GH[GitHub API]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> IAM
    API2 --> IAM
    API3 --> IAM
    
    IAM --> GC
    IAM --> GS
    IAM --> WE
    IAM --> CS
    
    API1 --> PG
    API1 --> RD
    API2 --> PG
    API2 --> RD
    API3 --> PG
    API3 --> RD
    
    GC --> E2B
    WE --> GEM
    CS --> CGN
    GS --> GH
    
    PR --> API1
    PR --> API2
    PR --> API3
    GR --> PR
```

## 🔧 Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ or CentOS 8+
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB+ SSD
- **Network**: Stable internet connection with outbound HTTPS access

### Required Software

```bash
# Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Node.js (for Playwright)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3.13 and uv
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv python3.13-dev
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Environment Variables

Create a `.env` file with all required configuration:

```bash
# Core Application
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/codegendb
REDIS_URL=redis://localhost:6379/0

# Codegen API Integration
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99
CODEGEN_API_HOST=https://api.codegen.com

# External API Keys
GEMINI_API_KEY=AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0
GITHUB_TOKEN=your-github-token-here

# Cloudflare Configuration
CLOUDFLARE_API_KEY=eae82cf159577a8838cc83612104c09c5a0d6
CLOUDFLARE_ACCOUNT_ID=2b2a1d3effa7f7fe4fe2a8c4e48681e3
CLOUDFLARE_WORKER_NAME=webhook-gateway
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev

# Sandbox Providers
GRAINCHAIN_DEFAULT_PROVIDER=local
E2B_API_KEY=your-e2b-api-key-here
DAYTONA_API_KEY=your-daytona-api-key-here
MORPH_API_KEY=your-morph-api-key-here

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=secure-grafana-password

# Security
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

## 🐳 Docker Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Main Application
  app:
    build:
      context: .
      dockerfile: Dockerfile.integrated
      target: production
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock  # For Grainchain local provider
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: codegendb
      POSTGRES_USER: codegenuser
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U codegenuser -d codegendb"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/ssl:/etc/nginx/ssl
      - ./frontend/build:/usr/share/nginx/html
    depends_on:
      - app
    restart: unless-stopped

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/provisioning:/etc/grafana/provisioning
      - ./docker/grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
```

### Deployment Commands

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/CodegenCICD.git
cd CodegenCICD

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check service health
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs app

# Run database migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Create initial admin user
docker-compose -f docker-compose.prod.yml exec app python -m backend.scripts.create_admin_user
```

## 🔧 Manual Installation

### 1. System Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    postgresql-client \
    redis-tools \
    nginx \
    supervisor \
    htop \
    vim

# Install Python 3.13
sudo apt-get install -y python3.13 python3.13-venv python3.13-dev

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### 2. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash codegenapp
sudo usermod -aG docker codegenapp

# Clone repository
sudo -u codegenapp git clone https://github.com/Zeeeepa/CodegenCICD.git /home/codegenapp/app
cd /home/codegenapp/app

# Set up Python environment
sudo -u codegenapp python3.13 -m venv venv
sudo -u codegenapp source venv/bin/activate

# Install dependencies
sudo -u codegenapp uv pip install -r backend/requirements-integrated.txt

# Install integrated libraries
sudo -u codegenapp uv pip install git+https://github.com/Zeeeepa/grainchain.git
sudo -u codegenapp uv pip install git+https://github.com/Zeeeepa/graph-sitter.git
sudo -u codegenapp uv pip install git+https://github.com/Zeeeepa/codegen-api-client.git

# Install web-eval-agent
sudo -u codegenapp uvx --from git+https://github.com/Zeeeepa/web-eval-agent.git playwright install

# Install Playwright browsers
sudo -u codegenapp npx playwright install --with-deps
```

### 3. Database Setup

```bash
# Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE codegendb;
CREATE USER codegenuser WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE codegendb TO codegenuser;
ALTER USER codegenuser CREATEDB;
\q
EOF

# Run migrations
cd /home/codegenapp/app
sudo -u codegenapp source venv/bin/activate
sudo -u codegenapp alembic upgrade head
```

### 4. Redis Setup

```bash
# Install Redis
sudo apt-get install -y redis-server

# Configure Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Test Redis connection
redis-cli ping
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/codegenapp`:

```nginx
upstream codegenapp {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # API Routes
    location /api/ {
        proxy_pass http://codegenapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static Files
    location /static/ {
        alias /home/codegenapp/app/frontend/build/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Frontend
    location / {
        root /home/codegenapp/app/frontend/build;
        try_files $uri $uri/ /index.html;
    }
    
    # Health Check
    location /health {
        proxy_pass http://codegenapp/api/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/codegenapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Supervisor Configuration

Create `/etc/supervisor/conf.d/codegenapp.conf`:

```ini
[group:codegenapp]
programs=codegenapp-8000,codegenapp-8001,codegenapp-8002

[program:codegenapp-8000]
command=/home/codegenapp/app/venv/bin/gunicorn backend.main:app -c /home/codegenapp/app/docker/gunicorn.conf.py --bind 127.0.0.1:8000
directory=/home/codegenapp/app
user=codegenapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/codegenapp/app-8000.log
environment=ENVIRONMENT=production

[program:codegenapp-8001]
command=/home/codegenapp/app/venv/bin/gunicorn backend.main:app -c /home/codegenapp/app/docker/gunicorn.conf.py --bind 127.0.0.1:8001
directory=/home/codegenapp/app
user=codegenapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/codegenapp/app-8001.log
environment=ENVIRONMENT=production

[program:codegenapp-8002]
command=/home/codegenapp/app/venv/bin/gunicorn backend.main:app -c /home/codegenapp/app/docker/gunicorn.conf.py --bind 127.0.0.1:8002
directory=/home/codegenapp/app
user=codegenapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/codegenapp/app-8002.log
environment=ENVIRONMENT=production
```

Start services:

```bash
sudo mkdir -p /var/log/codegenapp
sudo chown codegenapp:codegenapp /var/log/codegenapp
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start codegenapp:*
```

## 📊 Monitoring Setup

### Prometheus Configuration

Create `docker/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'codegenapp'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards

Create monitoring dashboards for:

1. **Application Metrics**
   - Request rate and latency
   - Error rates by endpoint
   - Pipeline execution metrics
   - Service health status

2. **Infrastructure Metrics**
   - CPU and memory usage
   - Database performance
   - Redis cache hit rates
   - Network I/O

3. **Business Metrics**
   - Pipeline success rates
   - Library usage statistics
   - User activity metrics
   - Cost tracking

## 🔒 Security Configuration

### SSL/TLS Setup

```bash
# Install Certbot for Let's Encrypt
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Set up auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Security Hardening

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Set up fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Configure automatic security updates
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 🧪 Testing Deployment

### Health Checks

```bash
# Test application health
curl -f http://localhost:8000/api/health

# Test integrated services
curl -X POST http://localhost:8000/api/integrated/health

# Test individual services
curl -X POST http://localhost:8000/api/integrated/grainchain/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello World\")", "provider": "local"}'
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install -y apache2-utils

# Run load test
ab -n 1000 -c 10 http://localhost:8000/api/health

# Install and use wrk for more advanced testing
sudo apt-get install -y wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/health
```

### Integration Testing

```bash
# Run the integrated test suite
cd /home/codegenapp/app
source venv/bin/activate
python -m pytest tests/test_integrated_pipeline.py -v

# Run performance tests
python -m pytest tests/test_integrated_pipeline.py::TestIntegrationPerformance -v
```

## 📈 Scaling Considerations

### Horizontal Scaling

1. **Load Balancer Configuration**
   - Use multiple application instances
   - Configure session affinity if needed
   - Implement health checks

2. **Database Scaling**
   - Set up read replicas
   - Implement connection pooling
   - Consider database sharding for large datasets

3. **Cache Scaling**
   - Redis Cluster for high availability
   - Implement cache warming strategies
   - Monitor cache hit rates

### Vertical Scaling

1. **Resource Allocation**
   - Monitor CPU and memory usage
   - Scale based on pipeline execution patterns
   - Consider GPU resources for AI workloads

2. **Storage Optimization**
   - Use SSD storage for databases
   - Implement log rotation
   - Monitor disk usage patterns

## 🔄 Backup and Recovery

### Database Backups

```bash
# Create backup script
cat > /home/codegenapp/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/codegenapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump -h localhost -U codegenuser -d codegendb > $BACKUP_DIR/codegendb_$DATE.sql
gzip $BACKUP_DIR/codegendb_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /home/codegenapp/backup_db.sh

# Schedule daily backups
sudo crontab -u codegenapp -e
# Add: 0 2 * * * /home/codegenapp/backup_db.sh
```

### Application Backups

```bash
# Backup application data
rsync -av /home/codegenapp/app/data/ /backup/app-data/
rsync -av /home/codegenapp/app/logs/ /backup/app-logs/
```

## 🚨 Troubleshooting

### Common Issues

1. **Service Startup Failures**
   ```bash
   # Check logs
   sudo supervisorctl tail -f codegenapp:codegenapp-8000
   docker-compose logs app
   
   # Check service status
   sudo supervisorctl status
   docker-compose ps
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   psql -h localhost -U codegenuser -d codegendb
   
   # Check PostgreSQL logs
   sudo tail -f /var/log/postgresql/postgresql-15-main.log
   ```

3. **Library Integration Issues**
   ```bash
   # Test Grainchain
   python -c "from backend.services.grainchain_service import GrainchainService; print('OK')"
   
   # Test Graph-sitter
   python -c "from backend.services.graph_sitter_service import GraphSitterService; print('OK')"
   
   # Test Web-eval-agent
   uvx --from git+https://github.com/Zeeeepa/web-eval-agent.git webEvalAgent --help
   ```

4. **Performance Issues**
   ```bash
   # Monitor resource usage
   htop
   iotop
   
   # Check application metrics
   curl http://localhost:8000/api/metrics
   
   # Analyze slow queries
   sudo -u postgres psql -d codegendb -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   ```

### Log Analysis

```bash
# Application logs
tail -f /var/log/codegenapp/app-8000.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
journalctl -u nginx -f
journalctl -u postgresql -f
```

## 📞 Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**
   - Review application logs
   - Check disk usage
   - Verify backup integrity
   - Update security patches

2. **Monthly**
   - Review performance metrics
   - Update dependencies
   - Analyze usage patterns
   - Optimize database queries

3. **Quarterly**
   - Security audit
   - Capacity planning review
   - Disaster recovery testing
   - Documentation updates

### Monitoring Alerts

Set up alerts for:
- High error rates (>5%)
- Slow response times (>2s)
- High resource usage (>80%)
- Failed pipeline executions
- Service downtime
- SSL certificate expiration

---

## 🎯 Success Metrics

After deployment, monitor these key metrics:

- **Availability**: >99.9% uptime
- **Performance**: <500ms average response time
- **Pipeline Success Rate**: >95%
- **Error Rate**: <1%
- **Resource Utilization**: <80% CPU/Memory

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
- [PostgreSQL Administration](https://www.postgresql.org/docs/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

---

**🎉 Congratulations! Your integrated CodegenCICD system is now deployed and ready for production use.**
