import hashlib

from django.core.cache import cache
from django.utils.encoding import force_str
from rest_framework.request import Request


def get_version(prefix: str) -> int:
    """Get the current version for a cache prefix."""
    return cache.get_or_set(f"{prefix}:version", 1)  # type: ignore[return-value]


def increment_version(prefix: str) -> None:
    """Increment the version for a cache prefix, effectively invalidating all related keys."""
    try:
        cache.incr(f"{prefix}:version")
    except ValueError:
        cache.set(f"{prefix}:version", 1)


def build_list_cache_key(prefix: str, request: Request) -> str:
    """
    Build a versioned cache key for a list view.
    Includes:
    - Prefix (resource name)
    - Current version
    - User ID (or 'anon') for permission/data segregation
    - Hash of query parameters (filtering, pagination, sorting)
    """
    version = get_version(prefix)

    # Create a hash of query parameters
    query_string = force_str(request.META.get("QUERY_STRING", ""))
    query_hash = hashlib.md5(query_string.encode("utf-8"), usedforsecurity=False).hexdigest()

    # Include user ID to handle vary_on_cookie / permissions
    user_part = f"u{request.user.id}" if request.user.is_authenticated else "anon"

    return f"{prefix}:v{version}:{user_part}:q{query_hash}"
