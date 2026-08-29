"""
Decode Garmin FIT 'location' messages (saved locations / favorites), FIT global
mesg num 29.

The installed garmin_fit_sdk profile (through at least 21.208.0) has no entry
for mesg num 29, so the decoder can't resolve field names and returns raw
records under the numeric key '29' instead of a friendly 'location_mesgs' key.
The field layout below was reverse engineered from real device output and
matches Garmin's public FIT SDK location_mesg definition:
  0   name (string)
  1   position_lat (sint32, semicircles)
  2   position_long (sint32, semicircles)
  3   symbol (uint16)
  4   altitude (uint16, scale 5, offset 500)
  254 message_index
"""

from typing import Any, Dict, List, Optional

from .wpmodel import MyWaypoint

SEMICIRCLE_TO_DEG = 180.0 / 2**31
ALTITUDE_SCALE = 5
ALTITUDE_OFFSET = 500

_FIELD_NAME = 0
_FIELD_LAT = 1
_FIELD_LON = 2
_FIELD_SYMBOL = 3
_FIELD_ALTITUDE = 4
_FIELD_INDEX = 254


def extract_locations(messages: Dict[str, Any]) -> List[Dict[str, Optional[float]]]:
    """
    Extract saved locations from decoded FIT messages.
    Checks the named 'location_mesgs' key first in case a future SDK profile
    resolves it, otherwise falls back to the raw numeric mesg num 29.
    """
    records = messages.get('location_mesgs') or messages.get('29') or []

    locations = []
    for r in records:
        if _FIELD_LAT not in r or _FIELD_LON not in r:
            continue
        altitude = r.get(_FIELD_ALTITUDE)
        locations.append({
            'name': r.get(_FIELD_NAME),
            'lat': r[_FIELD_LAT] * SEMICIRCLE_TO_DEG,
            'lon': r[_FIELD_LON] * SEMICIRCLE_TO_DEG,
            'altitude': altitude / ALTITUDE_SCALE - ALTITUDE_OFFSET if altitude is not None else None,
            'symbol': r.get(_FIELD_SYMBOL),
            'index': r.get(_FIELD_INDEX),
        })
    return locations


def location_to_waypoint(location: Dict[str, Optional[float]]) -> MyWaypoint:
    """Convert an extracted location dict to a MyWaypoint for YAML export."""
    return MyWaypoint(wpt_yaml={
        'name': location.get('name'),
        '_lat': location.get('lat'),
        '_lon': location.get('lon'),
        'ele': location.get('altitude'),
        'src': 'fit-location',
    })
