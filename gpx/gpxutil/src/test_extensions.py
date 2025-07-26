#!/usr/bin/env python3
"""
Test script to verify that MyWaypoint constructor properly handles extensions from YAML data
"""

from wpmodel import MyWaypoint, WaypointExtension, MyAddress

def test_yaml_extensions():
    """Test that YAML waypoint data with extensions is properly parsed"""

    # Sample YAML waypoint data with extensions
    wpt_yaml_data = {
        'name': 'Test Waypoint',
        '_lat': 47.6062,
        '_lon': -122.3321,
        'ele': 100.0,
        'extensions': [
            {
                'WaypointExtension': {
                    'Address': {
                        'StreetAddress': '123 Main St',
                        'City': 'Seattle',
                        'State': 'WA',
                        'PostalCode': '98101',
                        'Country': 'USA',
                        'CountryCode': 'US'
                    }
                }
            }
        ]
    }

    # Create MyWaypoint from YAML data
    waypoint = MyWaypoint(wpt_yaml=wpt_yaml_data)

    # Verify basic waypoint data
    assert waypoint.name == 'Test Waypoint'
    assert waypoint.latitude == 47.6062
    assert waypoint.longitude == -122.3321
    assert waypoint.elevation == 100.0

    # Verify extensions were parsed
    assert waypoint.extensions is not None
    assert len(waypoint.extensions) == 1

    # Verify WaypointExtension was created
    ext = waypoint.extensions[0]
    assert isinstance(ext, WaypointExtension)

    # Verify MyAddress was created and populated
    assert hasattr(ext, 'address')
    assert isinstance(ext.address, MyAddress)
    assert ext.address.StreetAddress == '123 Main St'
    assert ext.address.City == 'Seattle'
    assert ext.address.State == 'WA'
    assert ext.address.PostalCode == '98101'
    assert ext.address.Country == 'USA'
    assert ext.address.CountryCode == 'US'

    print("✓ YAML extensions parsing test passed!")

def test_yaml_no_extensions():
    """Test that YAML waypoint data without extensions works correctly"""

    wpt_yaml_data = {
        'name': 'Simple Waypoint',
        '_lat': 47.6062,
        '_lon': -122.3321,
    }

    waypoint = MyWaypoint(wpt_yaml=wpt_yaml_data)

    assert waypoint.name == 'Simple Waypoint'
    assert waypoint.latitude == 47.6062
    assert waypoint.longitude == -122.3321
    assert waypoint.extensions is None

    print("✓ YAML no extensions test passed!")

def test_yaml_empty_extensions():
    """Test that YAML waypoint data with empty extensions list works correctly"""

    wpt_yaml_data = {
        'name': 'Empty Extensions Waypoint',
        '_lat': 47.6062,
        '_lon': -122.3321,
        'extensions': []
    }

    waypoint = MyWaypoint(wpt_yaml=wpt_yaml_data)

    assert waypoint.name == 'Empty Extensions Waypoint'
    assert waypoint.extensions is None

    print("✓ YAML empty extensions test passed!")

if __name__ == '__main__':
    test_yaml_extensions()
    test_yaml_no_extensions()
    test_yaml_empty_extensions()
    print("\n🎉 All tests passed! YAML extensions parsing is working correctly.")
