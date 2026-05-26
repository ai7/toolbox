#!/usr/bin/env python
"""
Convert maps.me KML waypoints to YAML format compatible with gpxutil.
Extracts: name, coordinates (lat/lon), description (user notes with timestamp).
"""

import sys
import xml.etree.ElementTree as ET
import yaml
from datetime import datetime, timezone


KML_NAMESPACES = [
    '{http://earth.google.com/kml/2.2}',   # maps.me
    '{http://www.opengis.net/kml/2.2}',     # Organic Maps
]


def fix_kml_timestamp(time_str: str) -> dict:
    """
    Parse KML timestamp and detect maps.me ms-as-seconds bug.
    Older waypoints have timestamps stored as ms but exported as seconds,
    resulting in dates in January 1970. Corrects by multiplying by 1000.
    Returns dict with 'time' and optionally 'time_raw' (original junk value).
    """
    ts = datetime.fromisoformat(time_str.replace('Z', '+00:00')).replace(microsecond=0)
    if ts.year < 1971:
        corrected = datetime.fromtimestamp(ts.timestamp() * 1000, tz=timezone.utc).replace(microsecond=0)
        return {
            'time': corrected,
            'cmt': time_str,
        }
    return {'time': ts}


def detect_namespace(root) -> str:
    """Detect KML namespace from root element tag."""
    for ns in KML_NAMESPACES:
        if root.tag.startswith(ns):
            return ns
    return ''


def parse_kml(kml_file: str) -> list:
    """Parse a KML file (maps.me or Organic Maps) and extract Placemark data."""
    tree = ET.parse(kml_file)
    root = tree.getroot()
    ns = detect_namespace(root)

    waypoints = []
    for placemark in root.iter(f'{ns}Placemark'):
        name_el = placemark.find(f'{ns}name')
        desc_el = placemark.find(f'{ns}description')
        point_el = placemark.find(f'{ns}Point/{ns}coordinates')
        time_el = placemark.find(f'{ns}TimeStamp/{ns}when')

        if point_el is None:
            continue

        # coordinates are lon,lat[,alt]
        parts = point_el.text.strip().split(',')
        lon = float(parts[0])
        lat = float(parts[1])
        ele = float(parts[2]) if len(parts) > 2 else None

        wp = {
            'name': name_el.text.strip() if name_el is not None else 'Unnamed',
            '_lat': lat,
            '_lon': lon,
        }
        if ele and ele != 0:
            wp['ele'] = ele
        if desc_el is not None and desc_el.text and desc_el.text.strip():
            wp['desc'] = desc_el.text.strip()
        if time_el is not None and time_el.text:
            wp.update(fix_kml_timestamp(time_el.text))
        # extract icon/category from extended data (Organic Maps / maps.me)
        for el in placemark.iter():
            if el.tag in ('{https://omaps.app}icon', '{https://maps.me}icon'):
                if el.text and el.text.strip():
                    wp['sym'] = el.text.strip()
                break

        waypoints.append(wp)

    return waypoints


def write_yaml(waypoints: list, output_file: str):
    """Write waypoints to YAML in gpxutil format."""
    data = {'gpx': {'wpt': waypoints}}

    with open(output_file, 'w', encoding='utf-8') as f:
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        f.write(f"# Converted from KML (maps.me)\n")
        f.write(f"# {timestamp}\n")
        f.write(f"# {len(waypoints)} waypoints\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Wrote {len(waypoints)} waypoints to {output_file}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.kml> [output.yaml]")
        print(f"  If output not specified, uses input filename with .yaml extension")
        sys.exit(1)

    input_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = input_file.rsplit('.', 1)[0] + '.yaml'

    waypoints = parse_kml(input_file)
    if not waypoints:
        print(f"No waypoints found in {input_file}")
        sys.exit(1)

    print(f"Parsed {len(waypoints)} waypoints from {input_file}")
    write_yaml(waypoints, output_file)


if __name__ == '__main__':
    main()
