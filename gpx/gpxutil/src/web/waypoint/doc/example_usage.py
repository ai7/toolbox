#!/usr/bin/env python3
"""
Example usage of the GPX Map Viewer
"""

import sys
import os
sys.path.append('..')

from gpx_map_viewer import display_gpx_coordinates_in_browser

def example_basic_coordinates():
    """Example using basic coordinate tuples"""
    print("Example 1: Basic coordinates (lat, lon)")
    
    # Simple coordinate pairs
    coordinates = [
        (37.7749, -122.4194),  # San Francisco
        (40.7128, -74.0060),   # New York
        (34.0522, -118.2437)   # Los Angeles
    ]
    
    html_file = display_gpx_coordinates_in_browser(
        coordinates, 
        "Example 1: US Cities",
        auto_open=False  # Don't auto-open for this example
    )
    
    print(f"Generated: {html_file}")
    return html_file


def example_named_coordinates():
    """Example using coordinates with names"""
    print("\nExample 2: Named coordinates (lat, lon, name)")
    
    # Coordinates with names
    coordinates = [
        (48.8566, 2.3522, "Paris, France"),
        (51.5074, -0.1278, "London, UK"),
        (52.5200, 13.4050, "Berlin, Germany"),
        (41.9028, 12.4964, "Rome, Italy"),
        (40.4168, -3.7038, "Madrid, Spain")
    ]
    
    html_file = display_gpx_coordinates_in_browser(
        coordinates, 
        "Example 2: European Capitals",
        auto_open=False
    )
    
    print(f"Generated: {html_file}")
    return html_file


def example_single_point():
    """Example with a single coordinate"""
    print("\nExample 3: Single coordinate")
    
    # Single point
    coordinates = [
        (35.6762, 139.6503, "Tokyo, Japan")
    ]
    
    html_file = display_gpx_coordinates_in_browser(
        coordinates, 
        "Example 3: Tokyo Location",
        auto_open=False
    )
    
    print(f"Generated: {html_file}")
    return html_file


def example_hiking_trail():
    """Example simulating a hiking trail - great for testing topographic map"""
    print("\nExample 4: Simulated hiking trail (try the Topographic Map toggle!)")
    
    # Simulate a hiking trail with multiple waypoints
    coordinates = [
        (37.8651, -119.5383, "Trailhead"),
        (37.8701, -119.5401, "Creek Crossing"),
        (37.8751, -119.5445, "Viewpoint 1"),
        (37.8801, -119.5489, "Rest Area"),
        (37.8851, -119.5533, "Summit")
    ]
    
    html_file = display_gpx_coordinates_in_browser(
        coordinates, 
        "Example 4: Yosemite Trail - Toggle to Topo Map!",
        auto_open=True  # Open this one in browser
    )
    
    print(f"Generated: {html_file}")
    print("💡 Tip: Look for the layer control in the top-right corner to switch to Topographic Map!")
    print("📍 Coordinates are now loaded from coordinates.json file!")
    return html_file


if __name__ == "__main__":
    print("GPX Map Viewer - Usage Examples")
    print("=" * 40)
    
    # Run all examples
    example_basic_coordinates()
    example_named_coordinates()
    example_single_point()
    example_hiking_trail()
    
    print("\nAll examples completed!")
    print("The last example (hiking trail) should have opened in your browser.")
