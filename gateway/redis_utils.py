# gateway/redis_utils.py
import logging
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


def delete_keys_by_pattern(pattern: str) -> int:
    """
    Delete all Redis keys matching *pattern* using SCAN + DEL.

    Args:
        pattern: Redis glob pattern (e.g. ``test_graphql:*categories*``).

    Returns:
        Number of deleted keys.
    """
    conn = get_redis_connection("default")
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = conn.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            conn.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break
    return deleted
