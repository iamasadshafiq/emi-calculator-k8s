# gunicorn settings for the emi-web container
bind = "0.0.0.0:8080"
worker_class = "gthread"
workers = 2
threads = 8
worker_connections = 24    # at most 24 open connections per worker and a short backlog, so an
backlog = 32               # overloaded pod does not collect a long queue of requests nobody waits for
timeout = 30
graceful_timeout = 20      # finish running requests when the pod is stopped
keepalive = 5
worker_tmp_dir = "/dev/shm"   # heartbeat file in memory, so slow disk I/O cannot block the workers
accesslog = None           # no access log, it only costs CPU during the load tests
errorlog = "-"
