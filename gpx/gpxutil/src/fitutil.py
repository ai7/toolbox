#!/usr/bin/env python
"""
FIT file utility - read and display information from Garmin FIT tracklog files.
"""

import sys
import os
import re
import json
import tempfile
import webbrowser
from datetime import timedelta
import pytz
from garmin_fit_sdk import Decoder, Stream
import click
import gpxpy
import gpxpy.gpx

import yaml

from lib.timefix import TimeZoneGps
from lib.geocache import set_verbose
from lib.rename import (
    build_new_filename_fit as _build_new_filename_fit,
    build_new_filename_gpx as _build_new_filename_gpx,
)

SEMICIRCLE_TO_DEG = 180.0 / 2**31


def load_settings():
    settings_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.yaml')
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('fitutil', {})
    return {}


_settings = load_settings()

GARMIN_PRODUCTS = {
    int(k): (v['name'], v['short'])
    for k, v in _settings.get('garmin_products', {}).items()
}

CREATOR_DEVICE_MAP = _settings.get('creator_device_map', {})

# Build keyword -> canonical activity lookup from settings
_activity_cfg = _settings.get('activity_keywords', {})
ACTIVITY_KEYWORDS = {}
for canonical, aliases in _activity_cfg.items():
    for alias in aliases:
        ACTIVITY_KEYWORDS[alias] = canonical

GENERIC_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in _settings.get('generic_name_patterns', [])
]

GAP_THRESHOLD = timedelta(minutes=_settings.get('gap_threshold_minutes', 30))



def semicircles_to_deg(sc):
    return sc * SEMICIRCLE_TO_DEG


def format_duration(seconds):
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if d > 0:
        return f"{d}d {h}h {m:02d}m" if h > 0 else f"{d}d {m:02d}m"
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def format_distance(meters):
    km = meters / 1000
    miles = meters / 1609.344
    return f"{km:.2f} km ({miles:.2f} mi)"


def read_fit_file(filepath):
    stream = Stream.from_file(filepath)
    decoder = Decoder(stream)
    messages, errors = decoder.read()
    if errors:
        click.echo(f"  Errors decoding {filepath}: {errors}")
    return messages


def get_start_coords(messages):
    """Get first GPS coordinate from trackpoints."""
    for r in messages.get('record_mesgs', []):
        if 'position_lat' in r and 'position_long' in r:
            lat = semicircles_to_deg(r['position_lat'])
            lon = semicircles_to_deg(r['position_long'])
            return lat, lon
    session = messages.get('session_mesgs', [{}])[0]
    if 'start_position_lat' in session:
        lat = semicircles_to_deg(session['start_position_lat'])
        lon = semicircles_to_deg(session['start_position_long'])
        return lat, lon
    return None, None


def get_end_coords(messages):
    """Get last GPS coordinate from trackpoints."""
    for r in reversed(messages.get('record_mesgs', [])):
        if 'position_lat' in r and 'position_long' in r:
            lat = semicircles_to_deg(r['position_lat'])
            lon = semicircles_to_deg(r['position_long'])
            return lat, lon
    session = messages.get('session_mesgs', [{}])[0]
    if 'end_position_lat' in session:
        lat = semicircles_to_deg(session['end_position_lat'])
        lon = semicircles_to_deg(session['end_position_long'])
        return lat, lon
    return None, None


def get_device_name(messages):
    """Get device manufacturer and product name."""
    device = messages.get('device_info_mesgs', [{}])[0]
    manufacturer = device.get('manufacturer', 'unknown')
    numeric_id = device.get('product')
    entry = GARMIN_PRODUCTS.get(numeric_id)
    garmin_product = device.get('garmin_product')
    if entry:
        product_name = entry[0]
    elif garmin_product:
        product_name = str(garmin_product)
    elif numeric_id:
        product_name = str(numeric_id)
    else:
        product_name = 'unknown'
    product_id_str = f" [{numeric_id}]" if numeric_id else ''
    sw = device.get('software_version', '')
    return f"{manufacturer} {product_name}{product_id_str} (fw {sw})"


def get_device_short_name(messages):
    """Get short device name for filenames."""
    device = messages.get('device_info_mesgs', [{}])[0]
    numeric_id = device.get('product')
    entry = GARMIN_PRODUCTS.get(numeric_id)
    return entry[1] if entry else None


def get_elevation_stats(messages):
    """Check if elevation data exists and return min/max."""
    records = messages.get('record_mesgs', [])
    elevations = [r['enhanced_altitude'] for r in records if 'enhanced_altitude' in r]
    if not elevations:
        return None
    return {
        'min': min(elevations),
        'max': max(elevations),
        'count': len(elevations),
    }


def fmt_time_local(dt, coord_lat, coord_lon):
    """Format a datetime in the local timezone at the given coordinates."""
    if not dt:
        return None
    if coord_lat and coord_lon:
        tz_name = TimeZoneGps.get_timezone(coord_lat, coord_lon)
        if tz_name:
            local_dt = dt.astimezone(pytz.timezone(tz_name))
            return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} ({tz_name})"
    return f"{dt} UTC"


def print_track_info(filepath, activity, source,
                     start_time, start_lat, start_lon,
                     end_time, end_lat, end_lon,
                     duration_secs, moving_secs,
                     distance_m,
                     avg_speed_ms, max_speed_ms,
                     ascent_m, descent_m, elev_min, elev_max,
                     point_count, segment_count,
                     extra_lines=None):
    """Print formatted track info — shared by FIT and GPX."""
    click.echo(f"{'─' * 60}")
    click.echo(f"File: {os.path.basename(filepath)}")
    click.echo(f"{'─' * 60}")

    if activity:
        click.echo(f"  Activity:  {activity}")
    if source:
        click.echo(f"  Source:    {source}")

    if start_time:
        click.echo(f"  Start:     {fmt_time_local(start_time, start_lat, start_lon)}")
    if end_time:
        click.echo(f"  End:       {fmt_time_local(end_time, end_lat, end_lon)}")

    if moving_secs:
        click.echo(f"  Duration:  {format_duration(moving_secs)} (moving)")
        if duration_secs and (duration_secs - moving_secs) > 60:
            click.echo(f"  Elapsed:   {format_duration(duration_secs)} (total)")
    elif duration_secs:
        click.echo(f"  Duration:  {format_duration(duration_secs)}")

    if distance_m:
        click.echo(f"  Distance:  {format_distance(distance_m)}")

    if avg_speed_ms:
        avg_kmh = avg_speed_ms * 3.6
        avg_mph = avg_speed_ms * 2.23694
        speed_str = f"{avg_kmh:.1f} km/h ({avg_mph:.1f} mph)"
        if max_speed_ms:
            speed_str += f", max {max_speed_ms * 3.6:.1f} km/h"
        click.echo(f"  Speed:     {speed_str}")

    if ascent_m or descent_m:
        parts = []
        if ascent_m:
            parts.append(f"+{ascent_m:.0f}m")
        if descent_m:
            parts.append(f"-{descent_m:.0f}m")
        if elev_min is not None and elev_max is not None:
            parts.append(f"range {elev_min:.0f}–{elev_max:.0f}m")
        click.echo(f"  Elevation: {', '.join(parts)}")

    if start_lat and start_lon:
        click.echo(f"  Start GPS: {start_lat:.6f}, {start_lon:.6f}")

    if point_count is not None:
        click.echo(f"  Points:    {point_count}")
    click.echo(f"  Segments:  {segment_count}")

    if extra_lines:
        for line in extra_lines:
            click.echo(line)

    click.echo()


def print_fit_info(filepath):
    """Read and display information about a FIT file."""
    messages = read_fit_file(filepath)
    session = messages.get('session_mesgs', [{}])[0]

    sport = session.get('sport', 'unknown')
    sub_sport = session.get('sub_sport', '')
    activity = sport if sub_sport == 'generic' else f"{sport}/{sub_sport}"

    start_lat, start_lon = get_start_coords(messages)
    end_lat, end_lon = get_end_coords(messages)
    records = messages.get('record_mesgs', [])
    gps_count = sum(1 for r in records if 'position_lat' in r)
    segments = extract_track_segments_fit(messages)
    elev_stats = get_elevation_stats(messages)

    # for debugging device fields:
    # device = messages.get('device_info_mesgs', [{}])[0]
    # for k, v in device.items():
    #     click.echo(f"  {k}: {v}")

    print_track_info(
        filepath=filepath,
        activity=activity,
        source=get_device_name(messages),
        start_time=session.get('start_time'),
        start_lat=start_lat, start_lon=start_lon,
        end_time=session.get('timestamp'),
        end_lat=end_lat, end_lon=end_lon,
        duration_secs=session.get('total_elapsed_time'),
        moving_secs=session.get('total_timer_time'),
        distance_m=session.get('total_distance'),
        avg_speed_ms=session.get('enhanced_avg_speed'),
        max_speed_ms=session.get('enhanced_max_speed'),
        ascent_m=session.get('total_ascent'),
        descent_m=session.get('total_descent'),
        elev_min=elev_stats['min'] if elev_stats else None,
        elev_max=elev_stats['max'] if elev_stats else None,
        point_count=f"{len(records)} records ({gps_count} with GPS)",
        segment_count=len(segments),
    )


def print_gpx_info(filepath):
    """Read and display information about a GPX track file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    activity = next((t.type for t in gpx.tracks if t.type), None)

    start_time = end_time = None
    first_point = last_point = None
    for track in gpx.tracks:
        for segment in track.segments:
            if not segment.points:
                continue
            if not first_point:
                first_point = segment.points[0]
            last_point = segment.points[-1]
            t0 = segment.points[0].time
            t1 = segment.points[-1].time
            if t0 and (not start_time or t0 < start_time):
                start_time = t0
            if t1 and (not end_time or t1 > end_time):
                end_time = t1

    start_lat = first_point.latitude if first_point else None
    start_lon = first_point.longitude if first_point else None
    end_lat = last_point.latitude if last_point else None
    end_lon = last_point.longitude if last_point else None

    duration_secs = (end_time - start_time).total_seconds() if start_time and end_time else None
    moving_data = gpx.get_moving_data()
    total_dist = (moving_data.moving_distance + moving_data.stopped_distance) if moving_data else None
    uphill, downhill = gpx.get_uphill_downhill()
    elev_extremes = gpx.get_elevation_extremes()
    point_count = sum(len(seg.points) for track in gpx.tracks for seg in track.segments)
    segments = extract_track_segments_gpx(filepath)

    print_track_info(
        filepath=filepath,
        activity=activity,
        source=gpx.creator,
        start_time=start_time,
        start_lat=start_lat, start_lon=start_lon,
        end_time=end_time,
        end_lat=end_lat, end_lon=end_lon,
        duration_secs=duration_secs,
        moving_secs=None,
        distance_m=total_dist,
        avg_speed_ms=None,
        max_speed_ms=None,
        ascent_m=uphill,
        descent_m=downhill,
        elev_min=elev_extremes.minimum if elev_extremes else None,
        elev_max=elev_extremes.maximum if elev_extremes else None,
        point_count=point_count,
        segment_count=len(segments),
    )


def convert_to_gpx(filepath, output_path=None):
    """Convert a FIT file to GPX format with elevation data."""
    messages = read_fit_file(filepath)
    records = messages.get('record_mesgs', [])
    session = messages.get('session_mesgs', [{}])[0]

    gpx = gpxpy.gpx.GPX()
    gpx.creator = 'fitutil.py'

    track = gpxpy.gpx.GPXTrack()
    track.name = os.path.splitext(os.path.basename(filepath))[0]
    sport = session.get('sport')
    if sport:
        track.type = sport
    gpx.tracks.append(track)

    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for r in records:
        if 'position_lat' not in r or 'position_long' not in r:
            continue
        lat = semicircles_to_deg(r['position_lat'])
        lon = semicircles_to_deg(r['position_long'])
        ele = round(r['enhanced_altitude'], 1) if 'enhanced_altitude' in r else None
        time = r.get('timestamp')
        point = gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=ele, time=time)
        segment.points.append(point)

    if not output_path:
        output_path = os.path.splitext(filepath)[0] + '.gpx'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(gpx.to_xml())

    click.echo(f"  Converted: {os.path.basename(filepath)} -> {os.path.basename(output_path)} ({len(segment.points)} trackpoints)")


def extract_track_segments_fit(messages):
    """Extract GPS trackpoints from FIT messages, split into segments at time gaps."""
    segments = [{'points': [], 'start_time': None, 'end_time': None}]
    prev_time = None
    for r in messages.get('record_mesgs', []):
        if 'position_lat' not in r or 'position_long' not in r:
            continue
        lat = semicircles_to_deg(r['position_lat'])
        lon = semicircles_to_deg(r['position_long'])
        ele = round(r['enhanced_altitude'], 1) if 'enhanced_altitude' in r else None
        cur_time = r.get('timestamp')
        if prev_time and cur_time and (cur_time - prev_time) > GAP_THRESHOLD:
            segments[-1]['end_time'] = prev_time
            segments.append({'points': [], 'start_time': cur_time, 'end_time': None})
        if not segments[-1]['start_time'] and cur_time:
            segments[-1]['start_time'] = cur_time
        segments[-1]['points'].append([lat, lon, ele])
        prev_time = cur_time
    if segments and prev_time:
        segments[-1]['end_time'] = prev_time
    return [s for s in segments if s['points']]


def extract_track_segments_gpx(filepath):
    """Extract GPS trackpoints from a GPX file, split into segments at time gaps."""
    with open(filepath, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
    segments = []
    for track in gpx.tracks:
        for segment in track.segments:
            current_seg = {'points': [], 'start_time': None, 'end_time': None}
            prev_time = None
            for p in segment.points:
                ele = round(p.elevation, 1) if p.elevation is not None else None
                if prev_time and p.time and (p.time - prev_time) > GAP_THRESHOLD:
                    current_seg['end_time'] = prev_time
                    if current_seg['points']:
                        segments.append(current_seg)
                    current_seg = {'points': [], 'start_time': p.time, 'end_time': None}
                if not current_seg['start_time'] and p.time:
                    current_seg['start_time'] = p.time
                current_seg['points'].append([p.latitude, p.longitude, ele])
                prev_time = p.time
            if current_seg['points']:
                current_seg['end_time'] = prev_time
                segments.append(current_seg)
    return segments


def format_time_local(dt, lat, lon):
    """Format a UTC datetime to local time with offset and day of week."""
    if not dt:
        return ''
    tz_name = TimeZoneGps.get_timezone(lat, lon)
    if tz_name:
        local_tz = pytz.timezone(tz_name)
        dt = dt.astimezone(local_tz)
    return dt.strftime('%Y-%m-%d %H:%M:%S%z') + ' [' + dt.strftime('%a') + ']'


def get_track_summary_fit(messages):
    """Extract summary info from FIT messages for map display."""
    session = messages.get('session_mesgs', [{}])[0]
    start_time = session.get('start_time')
    end_time = session.get('timestamp')
    distance = session.get('total_distance')
    timer = session.get('total_timer_time')

    lat, lon = get_start_coords(messages)
    start_str = format_time_local(start_time, lat, lon) if lat else ''
    end_str = format_time_local(end_time, lat, lon) if lat else ''
    dist_str = format_distance(distance) if distance else ''
    duration_str = format_duration(timer) if timer else ''

    return {
        'start_time': start_str,
        'end_time': end_str,
        'distance': dist_str,
        'duration': duration_str,
    }


def get_track_summary_gpx(filepath):
    """Extract summary info from GPX file for map display."""
    with open(filepath, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
    start_time = None
    end_time = None
    first_point = None
    for track in gpx.tracks:
        for segment in track.segments:
            if segment.points:
                if not first_point:
                    first_point = segment.points[0]
                if segment.points[0].time and (not start_time or segment.points[0].time < start_time):
                    start_time = segment.points[0].time
                if segment.points[-1].time and (not end_time or segment.points[-1].time > end_time):
                    end_time = segment.points[-1].time

    lat = first_point.latitude if first_point else None
    lon = first_point.longitude if first_point else None

    start_str = format_time_local(start_time, lat, lon) if lat else ''
    end_str = format_time_local(end_time, lat, lon) if lat else ''

    duration_str = ''
    if start_time and end_time:
        duration_str = format_duration((end_time - start_time).total_seconds())

    moving_data = gpx.get_moving_data()
    dist_str = format_distance(moving_data.moving_distance + moving_data.stopped_distance) if moving_data else ''

    return {
        'start_time': start_str,
        'end_time': end_str,
        'distance': dist_str,
        'duration': duration_str,
    }


def show_tracks_on_map(files):
    """Display tracklogs on a map in the browser. Supports .fit and .gpx files."""
    tracks = []
    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.fit':
            messages = read_fit_file(filepath)
            segments = extract_track_segments_fit(messages)
            summary = get_track_summary_fit(messages)
        elif ext == '.gpx':
            segments = extract_track_segments_gpx(filepath)
            summary = get_track_summary_gpx(filepath)
        else:
            click.echo(f"  Skipping unsupported file: {filepath}")
            continue
        if segments:
            name = os.path.splitext(os.path.basename(filepath))[0]
            lat, lon = segments[0]['points'][0][0], segments[0]['points'][0][1]
            js_segments = []
            for idx, seg in enumerate(segments):
                seg_data = {'points': seg['points']}
                if seg['start_time']:
                    seg_data['start_time'] = format_time_local(seg['start_time'], lat, lon)
                if seg['end_time']:
                    seg_data['end_time'] = format_time_local(seg['end_time'], lat, lon)
                if seg['start_time'] and seg['end_time']:
                    seg_data['duration'] = format_duration((seg['end_time'] - seg['start_time']).total_seconds())
                if idx > 0 and segments[idx - 1]['end_time'] and seg['start_time']:
                    gap = (seg['start_time'] - segments[idx - 1]['end_time']).total_seconds()
                    seg_data['gap_duration'] = format_duration(gap)
                    seg_data['gap_secs'] = gap
                js_segments.append(seg_data)
            track_data = {'name': name, 'segments': js_segments}
            track_data.update(summary)
            tracks.append(track_data)

    if not tracks:
        click.echo("No GPS data found in the provided files.")
        return

    web_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'web', 'track')
    template_path = os.path.join(web_dir, 'template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace('{{TRACKS}}', json.dumps(tracks))
    html_content = html_content.replace('href="styles.css"', f'href="file://{os.path.join(web_dir, "styles.css")}"')
    html_content = html_content.replace('src="script.js"', f'src="file://{os.path.join(web_dir, "script.js")}"')

    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        html_file = f.name

    webbrowser.open('file://' + html_file)
    click.echo(f"  Opened map with {len(tracks)} track(s) in browser")


def build_new_filename(filepath, messages, device_override=None):
    return _build_new_filename_fit(
        filepath, messages, GARMIN_PRODUCTS,
        get_start_coords, get_end_coords, get_device_short_name,
        device_override=device_override,
    )


def build_new_filename_gpx(filepath, device_override=None):
    return _build_new_filename_gpx(
        filepath, CREATOR_DEVICE_MAP, GARMIN_PRODUCTS,
        GENERIC_NAME_PATTERNS, ACTIVITY_KEYWORDS, set(_activity_cfg.keys()),
        device_override=device_override,
    )


def rename_files(files, execute=False, device_override=None, sort=False):
    """Preview or execute renames for FIT and GPX files."""
    renames = []
    results = []
    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.fit':
            messages = read_fit_file(filepath)
            new_name = build_new_filename(filepath, messages, device_override=device_override)
        elif ext == '.gpx':
            new_name = build_new_filename_gpx(filepath, device_override=device_override)
        else:
            click.echo(f"  Skipping unsupported file: {filepath}")
            continue
        if not new_name:
            click.echo(f"  Could not determine name for: {filepath}")
            continue
        old_name = os.path.basename(filepath)
        dir_path = os.path.dirname(filepath)
        new_path = os.path.join(dir_path, new_name)
        if old_name == new_name:
            results.append((old_name, '(unchanged)'))
        else:
            renames.append((filepath, new_path))
            results.append((old_name, new_name))

    if results:
        if sort:
            results.sort(key=lambda r: r[1])
        max_old = max(len(r[0]) for r in results)
        for old_name, new_name in results:
            click.echo(f"  {old_name:<{max_old}}  ->  {new_name}")

    if not renames:
        return

    if execute:
        for old_path, new_path in renames:
            if os.path.exists(new_path):
                click.echo(f"  SKIP (exists): {new_path}")
                continue
            os.rename(old_path, new_path)
        click.echo(f"  Renamed {len(renames)} file(s)")
    else:
        click.echo(f"\n  {len(renames)} file(s) to rename. Use --yes to apply.")


@click.command()
@click.argument('fit_files', nargs=-1, type=click.Path(exists=True))
@click.option('--gpx', is_flag=True, help='Convert FIT files to GPX format.')
@click.option('--map', 'show_map', is_flag=True, help='Display tracks on a map in the browser.')
@click.option('--rename', is_flag=True, help='Preview descriptive renames for FIT files.')
@click.option('--yes', is_flag=True, help='Execute renames (use with --rename).')
@click.option('--device', type=str, default=None, help='Override device short name for rename.')
@click.option('--sort', is_flag=True, help='Sort rename output by target filename.')
def main(fit_files, gpx, show_map, rename, yes, device, sort):
    """Display information about Garmin FIT files."""
    if not fit_files:
        click.echo("Usage: fitutil.py [--gpx|--map|--rename] <file.fit> [file2.fit ...]")
        sys.exit(1)

    set_verbose(False)

    if show_map:
        show_tracks_on_map(fit_files)
    elif rename:
        rename_files(fit_files, execute=yes, device_override=device, sort=sort)
    else:
        for filepath in fit_files:
            ext = os.path.splitext(filepath)[1].lower()
            if gpx:
                convert_to_gpx(filepath)
            elif ext == '.gpx':
                print_gpx_info(filepath)
            else:
                print_fit_info(filepath)


if __name__ == '__main__':
    main()
