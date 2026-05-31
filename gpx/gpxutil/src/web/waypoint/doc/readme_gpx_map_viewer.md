# GPX Map Viewer

A Python function that displays GPX coordinates on OpenStreetMap in your default browser using the Leaflet.js library.

## Features

- Display coordinates on interactive OpenStreetMap
- Support for multiple coordinate formats
- Automatic map centering and zoom level calculation
- Markers with popup information
- Polyline connecting multiple waypoints
- Clean separation of HTML template and JavaScript
- Integration with existing GPX utilities (optional)

## Files

- `gpx_map_viewer.py` - Main Python module with the display function
- `map_template.html` - HTML template for the map page
- `map_script.js` - JavaScript functions for map initialization
- `example_usage.py` - Usage examples and demos

## Installation

No additional installation required beyond Python 3. The function uses:
- Built-in Python libraries (`os`, `tempfile`, `webbrowser`, `json`, `datetime`)
- Leaflet.js (loaded from CDN in the HTML template)
- OpenStreetMap tiles (free to use)

Optional: If you have the existing GPX utilities (`gpxpy`, `wpmodel`, etc.), the function can also read GPX and YAML files directly.

## Usage

### Basic Usage

```python
from gpx_map_viewer import display_gpx_coordinates_in_browser

# Simple coordinate pairs (latitude, longitude)
coordinates = [
    (37.7749, -122.4194),  # San Francisco
    (40.7128, -74.0060),   # New York
    (34.0522, -118.2437)   # Los Angeles
]

# Display in browser
html_file = display_gpx_coordinates_in_browser(
    coordinates, 
    "My Locations",
    auto_open=True
)
```

### Named Coordinates

```python
# Coordinates with names (latitude, longitude, name)
coordinates = [
    (48.8566, 2.3522, "Paris, France"),
    (51.5074, -0.1278, "London, UK"),
    (52.5200, 13.4050, "Berlin, Germany")
]

display_gpx_coordinates_in_browser(coordinates, "European Capitals")
```

### Single Point

```python
# Single coordinate
coordinates = [(35.6762, 139.6503, "Tokyo, Japan")]
display_gpx_coordinates_in_browser(coordinates, "Tokyo Location")
```

### From GPX File (if GPX utilities available)

```python
# Load from GPX file
display_gpx_coordinates_in_browser("my_waypoints.gpx", "My GPX Track")
```

## Function Parameters

```python
display_gpx_coordinates_in_browser(
    coordinates,           # Required: coordinates data
    title="GPX Coordinates Map",  # Optional: page title
    auto_open=True        # Optional: auto-open browser
)
```

### Coordinates Parameter

The `coordinates` parameter accepts:

1. **List of (lat, lon) tuples**: `[(37.7749, -122.4194), (40.7128, -74.0060)]`
2. **List of (lat, lon, name) tuples**: `[(37.7749, -122.4194, "San Francisco")]`
3. **Path to GPX/YAML file**: `"my_waypoints.gpx"` (requires GPX utilities)

## Map Features

- **Interactive Map**: Pan, zoom, click on markers
- **Markers**: Each coordinate gets a marker with popup showing name and coordinates
- **Polyline**: Multiple points are connected with a red line
- **Auto-fit**: Map automatically adjusts to show all waypoints
- **Responsive**: Works on desktop and mobile browsers

## Examples

Run the example script to see different usage patterns:

```bash
python3 example_usage.py
```

This will generate several example maps demonstrating:
1. Basic coordinates
2. Named coordinates  
3. Single point
4. Simulated hiking trail (opens in browser)

## Technical Details

### File Structure

The function creates temporary files:
- HTML file using `map_template.html` as template
- JavaScript file (`map_script.js`) for map functionality
- Files are created in system temp directory

### Template System

The HTML template uses placeholder replacement:
- `{{TITLE}}` - Page title
- `{{WAYPOINT_COUNT}}` - Number of waypoints
- `{{TIMESTAMP}}` - Generation timestamp
- `{{CENTER_LAT}}`, `{{CENTER_LON}}` - Map center coordinates
- `{{ZOOM}}` - Zoom level
- `{{COORDINATES}}` - JSON array of coordinate data

### Zoom Level Calculation

Automatic zoom level based on coordinate spread:
- Range > 10°: Zoom 5 (continental view)
- Range > 1°: Zoom 8 (regional view)
- Range > 0.1°: Zoom 11 (city view)
- Range > 0.01°: Zoom 14 (neighborhood view)
- Range ≤ 0.01°: Zoom 16 (street view)

## Integration with Existing GPX Tools

The function integrates with your existing GPX utilities:
- Reads GPX files using `read_gpx_file()`
- Reads YAML files using `read_yaml_file()`
- Uses `MyWaypoint` and `MyParams` classes
- Falls back gracefully if utilities not available

## Browser Compatibility

Works with all modern browsers that support:
- HTML5
- CSS3
- JavaScript ES5+
- Leaflet.js library

## Troubleshooting

### "GPX utilities not available" Warning
This is normal if you don't have the GPX utility modules installed. The function will still work with coordinate tuples.

### Browser Doesn't Open Automatically
If `webbrowser.open()` fails, the function will print the HTML file path. You can open it manually in any browser.

### Map Doesn't Load
Check your internet connection - the function requires access to:
- Leaflet.js CDN (unpkg.com)
- OpenStreetMap tiles (tile.openstreetmap.org)

## License

Uses OpenStreetMap data (© OpenStreetMap contributors) and Leaflet.js library.
