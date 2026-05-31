#!/usr/bin/env python
"""
GPX Map Viewer - Display GPX coordinates on OpenStreetMap in browser
"""

import os
import tempfile
import webbrowser
from dataclasses import dataclass
from typing import List, Tuple, Union, Optional
import json
from datetime import datetime

# Import from existing modules if available
try:
    from .wpmodel import MyWaypoint
    from gpxutil import read_gpx_file, read_yaml_file, MyParams
    import gpxpy
    from gpxpy.gpx import GPXWaypoint, GPX
    HAS_GPX_UTILS = True
except ImportError:
    HAS_GPX_UTILS = False
    print("Warning: GPX utilities not available. Using basic coordinate handling.")


def decimal_to_dms(deg, is_lat):
    direction = ('N' if deg >= 0 else 'S') if is_lat else ('E' if deg >= 0 else 'W')
    deg = abs(deg)
    d = int(deg)
    decimal_minutes = (deg - d) * 60
    m = int(decimal_minutes)
    s = (decimal_minutes - m) * 60
    return f'{d:3d}°{m:02d}\'{s:05.2f}"{direction} ({decimal_minutes:7.4f}\')'


def extract_coordinates_from_gpx_file(gpx_file_path: str) -> List[Tuple[float, float, Optional[str]]]:
    """
    Extract coordinates from a GPX file.
    Returns list of (latitude, longitude, name) tuples.
    """
    if not HAS_GPX_UTILS:
        raise ImportError("GPX utilities not available. Please ensure gpxpy is installed.")

    coordinates = []

    try:
        with open(gpx_file_path, 'r') as f:
            if gpx_file_path.endswith('.yaml'):
                params = MyParams(set(), set(), None, None, None, False, False)
                waypoints = read_yaml_file(f, params)
                for wp in waypoints:
                    coordinates.append((wp.latitude, wp.longitude, wp.name))
            else:
                params = MyParams(set(), set(), None, None, None, False, False)
                gpx = read_gpx_file(f, params)
                for waypoint in gpx.waypoints:
                    coordinates.append((waypoint.latitude, waypoint.longitude, waypoint.name))
    except Exception as e:
        print(f"Error reading GPX file: {e}")
        return []

    return coordinates


def get_template_path() -> str:
    """
    Get the path to the HTML template file.

    Returns:
        Path to the HTML template file
    """
    project_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    template_path = os.path.join(project_root, 'web', 'waypoint', 'template.html')
    if not os.path.exists(template_path):
        raise FileNotFoundError("HTML template file not found: web/waypoint/template.html")
    return template_path


@dataclass
class MapCoordinate:
    lat: float
    lon: float
    name: Optional[str]
    time: Optional[datetime]
    tz: Optional[str]
    lvl4: Optional[str]
    country_code: Optional[str]
    country: Optional[str]
    state: Optional[str]
    city: Optional[str]
    elevation: Optional[float]
    source: Optional[str]
    address: Optional[str]


def convert_waypoints(waypoints):
    """Convert MyWaypoint objects to MapCoordinate list."""
    results = []
    for wp in waypoints:
        addr = wp.get_address()
        results.append(MapCoordinate(
            lat=wp.latitude,
            lon=wp.longitude,
            name=wp.name,
            time=wp.time,
            tz=getattr(addr, 'TimeZone', None) if addr else None,
            lvl4=getattr(addr, 'LvL4', None) if addr else None,
            country_code=getattr(addr, 'CountryCode', None) if addr else None,
            country=getattr(addr, 'Country', None) if addr else None,
            state=getattr(addr, 'State', None) if addr else None,
            city=getattr(addr, 'City', None) if addr else None,
            elevation=wp.elevation,
            source=wp.source,
            address=getattr(addr, 'Address', None) if addr else None,
        ))
    return results


def calculate_zoom(coordinates: List[MapCoordinate]):
    """Calculate center point and zoom level for a set of coordinates."""
    avg_lat = sum(c.lat for c in coordinates) / len(coordinates)
    avg_lon = sum(c.lon for c in coordinates) / len(coordinates)

    if len(coordinates) > 1:
        lat_range = max(c.lat for c in coordinates) - min(c.lat for c in coordinates)
        lon_range = max(c.lon for c in coordinates) - min(c.lon for c in coordinates)
        max_range = max(lat_range, lon_range)

        if max_range > 10:
            zoom = 5
        elif max_range > 1:
            zoom = 8
        elif max_range > 0.1:
            zoom = 11
        elif max_range > 0.01:
            zoom = 14
        else:
            zoom = 16
    else:
        zoom = 13

    return avg_lat, avg_lon, zoom


def build_popup_html(coord: MapCoordinate, time_str: str):
    """Build the HTML popup content for a single waypoint."""
    name = coord.name or "Unnamed"
    popup = f"<b>{name}</b>"
    if time_str:
        popup += f"<br>{time_str}"
        if coord.tz:
            popup += f" ({coord.tz})"
    dms_lat = decimal_to_dms(coord.lat, is_lat=True)
    dms_lon = decimal_to_dms(coord.lon, is_lat=False)
    popup += f'<pre style="margin:4px 0; font-size:13px">'
    gps_str = f"{coord.lat:.6f}, {coord.lon:.6f}"
    copy_btn = (f'<a href="#" class="copy-btn" title="Copy to clipboard"'
                f' onclick="event.stopPropagation();copyToClipboard(\'{gps_str}\',this);return false;">'
                f'</a>')
    popup += f"GPS: {coord.lat:10.6f}, {coord.lon:.6f}  {copy_btn}\n"
    popup += f"Lat: {dms_lat}\n"
    popup += f"Lon: {dms_lon}\n"
    if coord.elevation is not None:
        feet = coord.elevation * 3.28084
        popup += f"Ele: {coord.elevation:,.1f} m ({feet:,.1f} ft)\n"
    if coord.source:
        popup += f"Src: {coord.source}\n"
    if coord.address:
        popup += f"Addr: {coord.address}\n"
    popup += "</pre>"
    return popup


def build_js_coordinates(coordinates: List[MapCoordinate]):
    """Convert MapCoordinate list into JS-ready dict list."""
    js_coordinates = []
    for i, coord in enumerate(coordinates):
        marker_name = coord.name if coord.name else f"Point {i+1}"
        time_str = f"{coord.time} [{coord.time.strftime('%a')}]" if coord.time else ""
        js_coordinates.append({
            'lat': coord.lat,
            'lon': coord.lon,
            'name': marker_name,
            'time': time_str,
            'date': coord.time.strftime('%Y-%m-%d') if coord.time else '',
            'src': coord.source or '',
            'lvl4': coord.lvl4 or '',
            'country_code': coord.country_code or '',
            'city': coord.city or '',
            'state': coord.state or '',
            'country': coord.country or '',
            'popup': build_popup_html(coord, time_str)
        })
    return js_coordinates


def create_html_with_coordinates(coordinates: Union[List[MapCoordinate], List['MyWaypoint']]) -> str:
    """
    Create HTML file with coordinates using placeholder replacement.

    Args:
        coordinates: List of MyWaypoint objects or MapCoordinate objects

    Returns:
        Path to the HTML file created
    """
    if coordinates and isinstance(coordinates[0], MyWaypoint):
        coordinates = convert_waypoints(coordinates)

    avg_lat, avg_lon, zoom = calculate_zoom(coordinates)
    js_coordinates = build_js_coordinates(coordinates)

    template_path = get_template_path()
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace('{{COORDINATES}}', json.dumps(js_coordinates))
    html_content = html_content.replace('{{CENTER_LAT}}', f'{avg_lat:.6f}')
    html_content = html_content.replace('{{CENTER_LON}}', f'{avg_lon:.6f}')
    html_content = html_content.replace('{{ZOOM}}', str(zoom))

    web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'web', 'waypoint')
    html_content = html_content.replace('href="styles.css"', f'href="file://{os.path.join(web_dir, "styles.css")}"')
    html_content = html_content.replace('src="filter.js"', f'src="file://{os.path.join(web_dir, "filter.js")}"')
    html_content = html_content.replace('src="script.js"', f'src="file://{os.path.join(web_dir, "script.js")}"')

    temp_dir = tempfile.gettempdir()
    html_file_path = os.path.join(temp_dir, 'gpx_map_viewer.html')

    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_file_path


def display_gpx_coordinates_in_browser(coordinates: Union[List[Tuple[float, float, str]],
                                                        List['MyWaypoint']],
                                      title: str = "GPX Coordinates Map",
                                      auto_open: bool = True) -> str:
    """
    Display GPX coordinates on OpenStreetMap in the default browser.

    Args:
        coordinates: Either:
            - List of (latitude, longitude, name) tuples
            - List of MyWaypoint objects
        title: Title for the map page
        auto_open: Whether to automatically open the browser

    Returns:
        Path to the generated HTML file

    Examples:
        # Using coordinate tuples with names
        coords = [(37.7749, -122.4194, "San Francisco"), (40.7128, -74.0060, "New York")]
        display_gpx_coordinates_in_browser(coords, "Cities")

        # Using MyWaypoint objects
        waypoints = [MyWaypoint(...), MyWaypoint(...)]
        display_gpx_coordinates_in_browser(waypoints, "My Waypoints")
    """

    if not coordinates:
        raise ValueError("No coordinates provided")

    # Create HTML file with embedded coordinates
    html_file_path = create_html_with_coordinates(coordinates)

    print(f"Generated map HTML file: {html_file_path}")
    print(f"Map contains {len(coordinates)} waypoint(s)")

    # Open HTML file in default browser
    if auto_open:
        try:
            webbrowser.open(f'file://{html_file_path}')
            print("Map opened in default browser")
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print(f"Please open this file manually: {html_file_path}")

    return html_file_path


def demo_map():
    """
    Demo function showing how to use the GPX map viewer with sample coordinates.
    """
    # Sample coordinates (some famous locations)
    sample_coordinates = [
        (37.7749, -122.4194, "San Francisco"),
        (40.7128, -74.0060, "New York City"),
        (51.5074, -0.1278, "London"),
        (48.8566, 2.3522, "Paris"),
        (35.6762, 139.6503, "Tokyo")
    ]

    print("Running GPX Map Viewer demo...")
    html_file = display_gpx_coordinates_in_browser(
        sample_coordinates,
        "Demo: World Cities",
        auto_open=True
    )

    return html_file


if __name__ == "__main__":
    # Run demo if script is executed directly
    demo_map()
