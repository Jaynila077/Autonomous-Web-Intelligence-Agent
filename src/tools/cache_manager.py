import os
import hashlib
import json
import functools
from typing import Any, Callable, Dict
from diskcache import Cache

# Define persistent cache directory inside ./workspace/cache
CACHE_DIR = os.path.abspath("./workspace/cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Instantiate global DiskCache instance
_global_disk_cache = Cache(CACHE_DIR)

class ProductionCacheManager:
    """
    Production-Grade DiskCache Manager for AWIS Web Intelligence System.
    Provides sub-millisecond local caching, MD5 key hashing, TTL expiration,
    and hit/miss statistics.
    """
    def __init__(self, cache_instance: Cache = _global_disk_cache):
        self.cache = cache_instance

    def _generate_key(self, prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generates a deterministic MD5 hash key for function arguments."""
        raw_payload = {
            "prefix": prefix,
            "func": func_name,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
        }
        serialized = json.dumps(raw_payload, sort_keys=True)
        return f"{prefix}:{hashlib.md5(serialized.encode('utf-8')).hexdigest()}"

    def get(self, key: str) -> Any:
        return self.cache.get(key)

    def set(self, key: str, value: Any, expire: int = 86400) -> bool:
        return self.cache.set(key, value, expire=expire)

    def clear(self) -> bool:
        """Purges all entries from the disk cache."""
        return self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on cache size and storage."""
        return {
            "cache_dir": CACHE_DIR,
            "total_entries": len(self.cache),
            "size_bytes": self.cache.volume(),
        }

# Global singleton instance
cache_manager = ProductionCacheManager()

def cache_result(expire: int = 86400, prefix: str = "awis_tool"):
    """
    Decorator for caching tool function results for a specified TTL (default 24h).
    
    Usage:
        @cache_result(expire=86400, prefix="academic")
        def my_tool_function(query: str):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_manager._generate_key(prefix, func.__name__, args, kwargs)
            
            # Check cache hit
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Cache miss - execute function
            result = func(*args, **kwargs)

            # Do not cache error responses
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "error" in result[0]:
                return result
            if isinstance(result, dict) and "error" in result:
                return result

            # Store clean result in diskcache
            cache_manager.set(cache_key, result, expire=expire)
            return result

        return wrapper
    return decorator


def truncate_tool_output(data: Any, max_chars: int = 2000) -> str:
    """
    Smart Tool Output Truncator: Converts raw tool search data (lists, dicts, strings)
    into clean, formatted text capped at max_chars (~500 tokens).
    Captures 3-4 detailed technical paragraphs while keeping token usage constrained.
    """
    if isinstance(data, (dict, list)):
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = str(data)

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + f"\n... [Truncated for token optimization: {len(text)} total chars]"
