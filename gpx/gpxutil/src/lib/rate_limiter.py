#!/usr/bin/env python
"""
Rate limiting decorator for controlling API request frequency.

The RateLimiter from geopy didn't work.

From VS/Cline.
"""

import time
import threading
from functools import wraps
from typing import Dict, Callable, Any
import click


class RateLimiter:
    """Thread-safe rate limiter that tracks function call times."""

    def __init__(self):
        self._call_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def rate_limit(self, max_calls: int = 1, time_window: float = 1.0, verbose: bool = False):
        """
        Decorator to rate limit function calls.

        Args:
            max_calls: Maximum number of calls allowed (currently only supports 1)
            time_window: Time window in seconds
            verbose: Whether to print rate limiting messages

        Returns:
            Decorated function with rate limiting applied
        """
        def decorator(func: Callable) -> Callable:
            func_name = f"{func.__module__}.{func.__name__}"

            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                with self._lock:
                    current_time = time.time()
                    last_call_time = self._call_times.get(func_name, 0.0)

                    time_since_last_call = current_time - last_call_time

                    if time_since_last_call < time_window:
                        sleep_time = time_window - time_since_last_call
                        if verbose:
                            click.echo(f"Rate limiting {func_name}: sleeping for {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)

                    # Update the last call time
                    self._call_times[func_name] = time.time()

                # Call the original function
                return func(*args, **kwargs)

            return wrapper
        return decorator


# Global rate limiter instance
_rate_limiter = RateLimiter()

# Convenience function to access the rate_limit decorator
def rate_limit(max_calls: int = 1, time_window: float = 1.0, verbose: bool = False):
    """
    Rate limiting decorator.

    Usage:
        @rate_limit(max_calls=1, time_window=2.0, verbose=True)
        def my_api_function():
            # function code here

    Args:
        max_calls: Maximum number of calls allowed in the time window (currently only supports 1)
        time_window: Time window in seconds
        verbose: Whether to print rate limiting messages
    """
    return _rate_limiter.rate_limit(max_calls=max_calls, time_window=time_window, verbose=verbose)
