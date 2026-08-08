"""Minimal Redis client — kept separate from db.py since it's a different
concern (cache/pub-sub, not the tasks database). Not used for anything yet;
this is here so week 4 has a warm Redis connection to build on."""

import os
import time

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_client() -> redis.Redis:
    return redis.from_url(REDIS_URL)


def ping() -> bool:
    return get_client().ping()


def ping_with_retry(retries: int = 10, delay: float = 1.0) -> None:
    """Same reasoning as db.init_db()'s retry loop: depends_on only waits
    for the redis container to start, not for it to accept connections."""
    last_error = None
    for _ in range(retries):
        try:
            ping()
            return
        except redis.exceptions.ConnectionError as exc:
            last_error = exc
            time.sleep(delay)
    raise last_error
