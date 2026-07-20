"""Fixed-window rate limiting for `/auth/login` (docs/DECISIONS.md ADR-0013): per-IP and
per-username counters, whichever trips first, reusing ADR-0005's Redis instance.
"""

import redis

MAX_ATTEMPTS = 10
WINDOW_SECONDS = 300


def is_rate_limited(redis_client: redis.Redis, key: str) -> bool:
    count = redis_client.get(key)
    return count is not None and int(count) >= MAX_ATTEMPTS


def record_failed_attempt(redis_client: redis.Redis, key: str) -> None:
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, WINDOW_SECONDS, nx=True)  # nx: don't push the window out on every attempt
    pipe.execute()
