"""
Gunicorn configuration for CodegenCICD production deployment
"""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 120
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "/app/logs/gunicorn-access.log"
errorlog = "/app/logs/gunicorn-error.log"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "codegencd"

# Server mechanics
daemon = False
pidfile = "/app/data/gunicorn.pid"
user = None
group = None
tmp_upload_dir = "/app/tmp"

# SSL (if certificates are provided)
keyfile = os.environ.get("SSL_KEYFILE")
certfile = os.environ.get("SSL_CERTFILE")

# Worker timeout
timeout = 120
graceful_timeout = 30

# Memory management
worker_tmp_dir = "/dev/shm"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("🚀 CodegenCICD server is ready to accept connections")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("👷 Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"👶 Worker {worker.pid} is being forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"🎯 Worker {worker.pid} has been forked")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("🔄 New master process is being forked")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("👋 CodegenCICD server is shutting down")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 Reloading workers")

# Environment-specific overrides
if os.environ.get("ENVIRONMENT") == "development":
    reload = True
    workers = 1
    loglevel = "debug"
    accesslog = "-"  # Log to stdout
    errorlog = "-"   # Log to stderr

