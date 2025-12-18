"""
RQ Worker bootstrap
"""

import os
from rq import Worker, Queue, Connection
from app.infrastructure.redis_client import get_redis
from app.workers.jobs import send_welcome_email  # Import jobs to register them

listen = ["default"]

if __name__ == "__main__":
    redis_conn = get_redis()
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()



