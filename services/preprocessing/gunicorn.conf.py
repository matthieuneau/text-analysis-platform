import os

# Gunicorn configuration file

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv("NUM_WORKERS", 4))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# TODO: app must be fork safe. not 100% sure it's the case. Enable later
preload_app = False

# Restart workers after this many requests, with up to 100 jitter
# This helps prevent memory leaks
timeout = 30
keepalive = 2

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "preprocessing-service"

# Graceful shutdown
graceful_timeout = 30

# Performance tuning
enable_stdio_inheritance = True


# Health check endpoint for load balancers
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")
