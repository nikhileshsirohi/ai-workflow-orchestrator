from __future__ import annotations

import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_orchestrator.db")
# DATABASE_URL="postgresql://localhost/ai_orchestrator_db"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "job_queue")

# Worker reliability defaults
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TOOL_TIMEOUT_SEC = float(os.getenv("TOOL_TIMEOUT_SEC", "2.0"))

# Reaper
REAPER_STALE_MINUTES = int(os.getenv("REAPER_STALE_MINUTES", "2"))