"""
Persistent caching decorator for geocoding functions.
Provides file-based caching with hybrid JSON + base64 binary serialization for geopy.Location objects.
Cache updates are kept in memory and only saved to disk on program exit.

From VS/Cline.
"""

import functools
import pickle
import base64
import json
import os
import atexit
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import click

# Global registry to track all cache instances that need to be saved on exit
_cache_registry = []


def persistent_cache(cache_file: str = "geocoding_cache.json"):
    """
    Decorator that adds persistent file-based caching to a function using hybrid JSON + base64 binary format.
    Cache updates are kept in memory and only saved to disk on program exit.

    Args:
        cache_file: Path to the JSON cache file (.json extension recommended)

    Returns:
        Decorated function with caching capability

    Usage:
        @persistent_cache("my_cache.json")
        def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        # Create cache file in the same directory as geocache.py
        if not os.path.isabs(cache_file):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cache_path = os.path.join(script_dir, cache_file)
        else:
            cache_path = cache_file
        cache_updated = False  # Track if cache has been modified

        # Load existing cache on first use
        def _load_cache():
            nonlocal cache
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        cache = data.get('entries', {})
                        click.echo(f"  [CACHE] Loaded {len(cache)} entries from {cache_path}")
                except (json.JSONDecodeError, IOError) as e:
                    click.echo(f"  [CACHE] Warning: Could not load cache file {cache_path}: {e}")
                    cache = {}  # Start fresh if cache is corrupted

        def _save_cache():
            """Save cache to JSON file with base64-encoded binary data"""
            if not cache_updated:
                return  # Don't save if cache hasn't been updated

            cache_data = {
                "cache_version": "1.0",
                "format": "hybrid_json_binary",
                "created_by": "gpxutil geocoding cache",
                "entries": cache,
                "metadata": {
                    "total_entries": len(cache),
                    "last_updated": datetime.now().isoformat(),
                    "cache_file": cache_path
                }
            }
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                click.echo(f"  [CACHE] Saved {len(cache)} entries to {cache_path}")
            except (json.JSONDecodeError, IOError) as e:
                click.echo(f"  [CACHE] Warning: Could not save cache file {cache_path}: {e}")

        def _make_cache_key(*args, **kwargs) -> str:
            """Generate cache key from function arguments"""
            # For get_address_from_coordinates(latitude, longitude)
            if len(args) >= 2:
                return f"{args[0]},{args[1]}"
            # Generic fallback for other functions
            return str(args) + str(sorted(kwargs.items()))

        def _serialize_location(location) -> Dict[str, Any]:
            """
            Serialize geopy.Location object as base64-encoded pickle within JSON structure.
            """
            try:
                # Pickle the location object
                pickled_data = pickle.dumps(location)
                # Encode as base64 string for JSON storage
                encoded_data = base64.b64encode(pickled_data).decode('utf-8')

                return {
                    "type": "geopy.Location",
                    "data": encoded_data,
                    "cached_at": datetime.now().isoformat()
                }
            except Exception as e:
                click.echo(f"  [CACHE] Warning: Could not serialize location: {e}")
                # Fallback for non-serializable objects
                return {
                    "type": "string",
                    "data": str(location),
                    "cached_at": datetime.now().isoformat()
                }

        def _deserialize_location(data: Dict[str, Any]):
            """
            Deserialize base64-encoded pickle back to geopy.Location object.
            """
            if data.get("type") == "geopy.Location":
                try:
                    # Decode base64 and unpickle
                    pickled_data = base64.b64decode(data["data"].encode('utf-8'))
                    return pickle.loads(pickled_data)
                except Exception as e:
                    click.echo(f"  [CACHE] Warning: Could not deserialize location: {e}")
                    return None
            else:
                # Handle string or other simple types
                return data.get("data")

        # Load cache when decorator is applied
        _load_cache()

        # Register this cache instance for saving on exit
        cache_instance = {
            'save_func': _save_cache,
            'cache_path': cache_path,
            'cache_ref': lambda: cache,
            'updated_ref': lambda: cache_updated
        }
        _cache_registry.append(cache_instance)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache_updated

            # Generate cache key
            cache_key = _make_cache_key(*args, **kwargs)

            # Check cache first
            if cache_key in cache:
                click.echo(f"  [CACHE HIT] Using cached result for {cache_key}")
                return _deserialize_location(cache[cache_key])

            # Call original function
            click.echo(f"  [CACHE MISS] Calling function for {cache_key}")
            result = func(*args, **kwargs)

            # Cache the result (if not an error) - only in memory
            if result and not str(result).startswith("Error:"):
                try:
                    cache[cache_key] = _serialize_location(result)
                    cache_updated = True  # Mark cache as updated
                    click.echo(f"  [CACHE] Stored result in memory for {cache_key}")
                except Exception as e:
                    click.echo(f"  [CACHE] Warning: Could not cache result for {cache_key}: {e}")

            return result

        # Add cache management methods to the wrapper
        def clear_cache():
            nonlocal cache, cache_updated
            cache.clear()
            cache_updated = True
            _save_cache()
            click.echo(f"  [CACHE] Cleared cache")

        def cache_info():
            return {
                "entries": len(cache),
                "cache_file": cache_path,
                "keys": list(cache.keys()),
                "format": "hybrid_json_binary",
                "updated": cache_updated
            }

        def force_save():
            """Force save cache to disk immediately"""
            _save_cache()

        wrapper.clear_cache = clear_cache
        wrapper.cache_info = cache_info
        wrapper.force_save = force_save

        return wrapper
    return decorator


def _save_all_caches():
    """Save all registered caches to disk. Called on program exit."""
    click.echo("  [CACHE] Saving all updated caches to disk...")
    saved_count = 0
    for cache_instance in _cache_registry:
        if cache_instance['updated_ref']():  # Only save if updated
            cache_instance['save_func']()
            saved_count += 1
    if saved_count > 0:
        click.echo(f"  [CACHE] Saved {saved_count} cache file(s) on exit")


# Register the exit handler to save all caches
atexit.register(_save_all_caches)


# Convenience functions for cache management
def clear_geocoding_cache(cache_file: str = "geocoding_cache.json"):
    """Clear the geocoding cache file"""
    try:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            click.echo(f"  [CACHE] Cleared cache file: {cache_file}")
        else:
            click.echo(f"  [CACHE] Cache file does not exist: {cache_file}")
    except OSError as e:
        click.echo(f"  [CACHE] Error clearing cache file: {e}")


def force_save_all_caches():
    """Force save all caches to disk immediately (useful for testing)"""
    _save_all_caches()


def get_cache_stats(cache_file: str = "geocoding_cache.json") -> Dict[str, Any]:
    """Get statistics about the cache file"""
    if not os.path.exists(cache_file):
        return {"exists": False, "entries": 0, "format": "hybrid_json_binary"}

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "exists": True,
                "entries": len(data.get('entries', {})),
                "cache_version": data.get('cache_version'),
                "format": data.get('format', 'hybrid_json_binary'),
                "last_updated": data.get('metadata', {}).get('last_updated'),
                "file_size": os.path.getsize(cache_file)
            }
    except (json.JSONDecodeError, IOError):
        return {"exists": True, "entries": 0, "error": "Could not read cache file", "format": "hybrid_json_binary"}


def inspect_cache(cache_file: str = "geocoding_cache.json"):
    """Debug utility to inspect cache contents"""
    if not os.path.exists(cache_file):
        click.echo("Cache file does not exist")
        return

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        click.echo(f"Cache version: {cache_data.get('cache_version')}")
        click.echo(f"Format: {cache_data.get('format')}")
        click.echo(f"Created by: {cache_data.get('created_by')}")

        metadata = cache_data.get('metadata', {})
        click.echo(f"Last updated: {metadata.get('last_updated')}")
        click.echo(f"Total entries: {metadata.get('total_entries')}")

        entries = cache_data.get('entries', {})
        click.echo(f"\nCache entries:")
        for key, value in entries.items():
            if isinstance(value, dict) and value.get("type") == "geopy.Location":
                click.echo(f"  {key}: geopy.Location (base64 encoded) - cached at {value.get('cached_at')}")
            else:
                click.echo(f"  {key}: {type(value).__name__} - {str(value)[:50]}...")

    except Exception as e:
        click.echo(f"Error reading cache: {e}")
