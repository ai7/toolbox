"""
Reverse geocoding with persistent caching.
"""

from typing import Optional
import click
import geopy
from geopy.geocoders import Nominatim

from .geocache import persistent_cache
from .rate_limiter import rate_limit

_geolocator = Nominatim(user_agent="gpxutil")


@rate_limit(max_calls=1, time_window=3.0, verbose=True)
def _reverse_geocode(latitude: float, longitude: float) -> Optional[geopy.Location]:
    return _geolocator.reverse((latitude, longitude), language='en')


@persistent_cache(cache_file="geocoding_cache.json")
def get_address_from_coordinates(latitude: float, longitude: float) -> Optional[geopy.Location]:
    try:
        return _reverse_geocode(latitude=latitude, longitude=longitude)
    except Exception as e:
        click.echo(f"failed to do reverse geo-lookup: {e}", err=True)
