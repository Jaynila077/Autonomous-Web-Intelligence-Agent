# src/api/arq_worker.py
import os
from arq.connections import RedisSettings
from dotenv import load_dotenv

load_dotenv()

from src.api.worker import execute_agent_pipeline

# Connection DSN for Upstash Redis (or local Redis for development)
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379"))


class WorkerSettings:
    """
    arq worker configuration.
    Executes in a separate process from the FastAPI server.
    """
    functions = [execute_agent_pipeline]
    redis_settings = RedisSettings.from_dsn(UPSTASH_REDIS_URL)
    max_jobs = 10
    job_timeout = 1200  # 20 minutes max per OSINT research job