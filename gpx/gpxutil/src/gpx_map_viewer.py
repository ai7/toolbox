#!/usr/bin/env python
"""
GPX Map Viewer - Display GPX coordinates on OpenStreetMap in browser
"""

import os
import webbrowser
from typing import List, Tuple, Union, Optional
import json
from datetime import datetime

# Import from existing modules if available
try:
    from wpmodel import MyWaypoint
    from gpxutil import read_gpx_file, read_yaml_file, MyParams
    import gpxpy
    from gpxpy.gpx import GPXWaypoint, GPX
    HAS_GPX_UTILS = True
except ImportError:
    HAS_GPX_UTILS = False
    print("Warning: GPX utilities not available. Using basic coordinate handling.")


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
    template_path = os.path.join(os.path.dirname(__file__), 'map', 'map_template.html')
    if not os.path.exists(template_path):
        raise FileNotFoundError("HTML template file not found: map/map_template.html")
    return template_path


def create_html_with_coordinates(coordinates: Union[List[Tuple[float, float, str]], List['MyWaypoint']]) -> str:
    """
    Create HTML file with coordinates using placeholder replacement.
    
    Args:
        coordinates: Either:
            - List of (latitude, longitude, name) tuples
            - List of MyWaypoint objects

    Returns:
        Path to the HTML file created
    """
    # Convert MyWaypoint objects to coordinate tuples if needed
    if coordinates and isinstance(coordinates[0], MyWaypoint):
        # It's a list of MyWaypoint objects
        coordinates = [(wp.latitude, wp.longitude, wp.name) for wp in coordinates]
    
    # Calculate center point and zoom level
    avg_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    avg_lon = sum(coord[1] for coord in coordinates) / len(coordinates)
    
    if len(coordinates) > 1:
        lat_range = max(coord[0] for coord in coordinates) - min(coord[0] for coord in coordinates)
        lon_range = max(coord[1] for coord in coordinates) - min(coord[1] for coord in coordinates)
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
    
    # Prepare coordinates for JavaScript
    js_coordinates = []
    for i, (lat, lon, name) in enumerate(coordinates):
        marker_name = name if name else f"Point {i+1}"
        js_coordinates.append({
            'lat': lat,
            'lon': lon,
            'name': marker_name,
            'popup': f"<b>{marker_name}</b><br>Lat: {lat:.6f}<br>Lon: {lon:.6f}"
        })
    
    # Read the template
    template_path = get_template_path()
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace placeholders
    html_content = html_content.replace('{{COORDINATES}}', json.dumps(js_coordinates))
    html_content = html_content.replace('{{CENTER_LAT}}', f'{avg_lat:.6f}')
    html_content = html_content.replace('{{CENTER_LON}}', f'{avg_lon:.6f}')
    html_content = html_content.replace('{{ZOOM}}', str(zoom))
    
    # Update paths to use absolute file paths
    map_dir = os.path.join(os.path.dirname(__file__), 'map')
    html_content = html_content.replace('href="map_styles.css"', f'href="file://{os.path.join(map_dir, "map_styles.css")}"')
    html_content = html_content.replace('src="map_script.js"', f'src="file://{os.path.join(map_dir, "map_script.js")}"')
    
    # Write to a fixed temporary HTML file (reuse same file)
    import tempfile
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
