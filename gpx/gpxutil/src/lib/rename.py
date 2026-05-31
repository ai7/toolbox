"""
Rename logic for FIT and GPX track files.
Builds descriptive filenames from GPS metadata and geocoding.
"""

import os
import re
import gpxpy
import pytz

from .timefix import TimeZoneGps
from .geocode import get_address_from_coordinates


def sanitize_city(city):
    """Lowercase city name, remove spaces and special characters."""
    if not city:
        return None
    city = re.sub(r'\s+(District|City|County|Prefecture|Municipality)$', '', city, flags=re.IGNORECASE)
    city = city.lower()
    city = re.sub(r'[^a-z0-9]', '', city)
    return city[:15] if city else None


def geocode_location(lat, lon):
    """Reverse geocode coordinates to (lvl4_part, city_part)."""
    if not lat or not lon:
        return None, None
    location = get_address_from_coordinates(lat, lon)
    if not location or not location.raw or 'address' not in location.raw:
        return None, None
    raw_addr = location.raw['address']
    lvl4 = raw_addr.get('ISO3166-2-lvl4', '')
    lvl4_part = lvl4.replace('-', '').lower() if lvl4 else None
    city = raw_addr.get('city') or raw_addr.get('town') or raw_addr.get('municipality')
    city_part = sanitize_city(city)
    if not city_part and raw_addr.get('county'):
        city_part = sanitize_city(raw_addr['county']) + '_co'
    return lvl4_part, city_part


def append_end_city(city_part, end_lat, end_lon):
    """Append end city to city_part if different from start."""
    if not end_lat or not end_lon or not city_part:
        return city_part
    _, end_city_part = geocode_location(end_lat, end_lon)
    if end_city_part and end_city_part != city_part:
        return city_part + '_' + end_city_part
    return city_part


def format_time_part(start_time, lat, lon):
    """Format start timestamp in local time as YYYYMMDD_HHMM."""
    if not start_time or not lat or not lon:
        return None
    tz_name = TimeZoneGps.get_timezone(lat, lon)
    if tz_name:
        local_start = start_time.astimezone(pytz.timezone(tz_name))
        return local_start.strftime('%Y%m%d_%H%M')
    return None


def format_duration_part(seconds):
    """Format duration for filename: XhXXm or XdXh."""
    if not seconds:
        return None
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    if d > 0:
        return f"{d}d{h}h" if h > 0 else f"{d}d"
    return f"{h}h{m:02d}m"


def format_distance_part(meters):
    """Format distance for filename: XX.Xmi."""
    if not meters:
        return None
    mi = meters / 1609.344
    return f"{mi:04.1f}mi"


def assemble_filename(parts, ext):
    """Join non-None parts with dashes and append extension."""
    filtered = [p for p in parts if p]
    if not filtered:
        return None
    return '-'.join(filtered) + ext


def extract_activity_from_name(name, activity_keywords, canonical_names):
    """Extract activity keyword from filename. Returns (activity, cleaned_name)."""
    words = re.split(r'[_\s]+', name.lower())
    activity = None
    remaining = []
    for w in words:
        if not activity:
            if w in activity_keywords:
                activity = activity_keywords[w]
            elif w in canonical_names:
                activity = w
            else:
                remaining.append(w)
        else:
            remaining.append(w)
    cleaned = '_'.join(remaining) if remaining else None
    return activity, cleaned


def clean_original_name(filename, generic_patterns, activity_keywords, canonical_names):
    """Clean original filename for appending. Returns None if generic."""
    name = os.path.splitext(filename)[0]
    for pattern in generic_patterns:
        if pattern.match(name):
            return None
    _, cleaned = extract_activity_from_name(name, activity_keywords, canonical_names)
    if cleaned:
        cleaned = re.sub(r'_?\d+$', '', cleaned)
    return cleaned if cleaned else None


def get_device_from_creator(creator, creator_device_map, garmin_products):
    """Map GPX creator string to a device short name."""
    if not creator:
        return None
    creator_lower = creator.lower()
    for key, name in creator_device_map.items():
        if key in creator_lower:
            return name
    for device_id, (full_name, short_name) in garmin_products.items():
        if full_name.lower() == creator_lower:
            return short_name
    return None


def build_new_filename_fit(filepath, messages, garmin_products,
                           get_start_coords_fn, get_end_coords_fn,
                           get_device_short_name_fn, device_override=None):
    """Build a descriptive filename from FIT file data."""
    session = messages.get('session_mesgs', [{}])[0]
    ext = os.path.splitext(filepath)[1]

    start_time = session.get('start_time')
    lat, lon = get_start_coords_fn(messages)
    end_lat, end_lon = get_end_coords_fn(messages)

    time_part = format_time_part(start_time, lat, lon)
    duration_part = format_duration_part(session.get('total_elapsed_time'))
    distance_part = format_distance_part(session.get('total_distance'))
    device_part = device_override or get_device_short_name_fn(messages)
    lvl4_part, city_part = geocode_location(lat, lon)
    city_part = append_end_city(city_part, end_lat, end_lon)
    sport_part = session.get('sport') or None

    return assemble_filename(
        [time_part, duration_part, distance_part, device_part, lvl4_part, city_part, sport_part], ext
    )


def build_new_filename_gpx(filepath, creator_device_map, garmin_products,
                           generic_patterns, activity_keywords, canonical_names,
                           device_override=None):
    """Build a descriptive filename from GPX track data."""
    ext = os.path.splitext(filepath)[1]
    with open(filepath, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    if not gpx.tracks:
        return None

    start_time = end_time = None
    first_lat = first_lon = last_lat = last_lon = None
    for track in gpx.tracks:
        for seg in track.segments:
            if seg.points:
                if not first_lat:
                    first_lat = seg.points[0].latitude
                    first_lon = seg.points[0].longitude
                if seg.points[0].time and (not start_time or seg.points[0].time < start_time):
                    start_time = seg.points[0].time
                if seg.points[-1].time and (not end_time or seg.points[-1].time > end_time):
                    end_time = seg.points[-1].time
                last_lat = seg.points[-1].latitude
                last_lon = seg.points[-1].longitude

    time_part = format_time_part(start_time, first_lat, first_lon)
    duration_secs = (end_time - start_time).total_seconds() if start_time and end_time else None
    duration_part = format_duration_part(duration_secs)

    moving_data = gpx.get_moving_data()
    total_dist = (moving_data.moving_distance + moving_data.stopped_distance) if moving_data else None
    distance_part = format_distance_part(total_dist)

    device_part = device_override or get_device_from_creator(gpx.creator, creator_device_map, garmin_products)
    lvl4_part, city_part = geocode_location(first_lat, first_lon)
    city_part = append_end_city(city_part, last_lat, last_lon)

    sport_part = None
    for track in gpx.tracks:
        if track.type:
            sport_part = track.type.lower()
            break
    if not sport_part:
        name_activity, _ = extract_activity_from_name(
            os.path.splitext(os.path.basename(filepath))[0], activity_keywords, canonical_names
        )
        sport_part = name_activity or 'activity'

    orig_part = clean_original_name(os.path.basename(filepath), generic_patterns, activity_keywords, canonical_names)
    if orig_part and city_part and orig_part in city_part:
        orig_part = None

    parts = [time_part, duration_part, distance_part, device_part, lvl4_part, city_part, sport_part]
    if orig_part:
        parts.append(orig_part)
    return assemble_filename(parts, ext)
