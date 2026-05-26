#!/usr/bin/env python
#
# my awesome GPX utility
#
# i: info
# q: query for address based on gpx data

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Tuple, IO, Any

import click
from click_option_group import optgroup
import geopy
import yaml
import gpxpy
import re
from gpxpy.gpx import GPXWaypoint, GPX
from geopy.geocoders import Nominatim
import traceback

# my stuff
from wpmodel import MyWaypoint, WaypointExtension, MyAddress, MyWidthTracker
from cmdarg import UpdateOption, UpdateOptionType, DeleteOption, DeleteOptionType, DateRangeType, IndexRangeType, ColumnsType, MyParams
from wpfilter import filter_by_date, filter_by_location, filter_by_index, parse_relative
from timefix import TimeFix, TimeZoneGps
from geocache import persistent_cache, set_refresh_mode
from rate_limiter import rate_limit

# lazily initialized
_width_tracker: Optional[MyWidthTracker] = None

# Create a geolocator object with a custom user agent for fetching address
_geolocator = Nominatim(user_agent="gpxutil")


# Custom YAML representer for GPXWaypoint
def gpx_waypoint_representer(dumper: yaml.Dumper, data: gpxpy.gpx.GPXWaypoint) -> yaml.Node:
    """
    Custom YAML representer for GPXWaypoint objects.
    Only includes non-null fields in the output.
    """
    # Create a dictionary with all possible fields
    waypoint_dict = {
        'name': data.name,
        '_lat': data.latitude,
        '_lon': data.longitude,
        'ele': data.elevation,
        # 'time': data.time.isoformat().replace('+00:00', 'Z') if data.time else None,
        'time': data.time,
        'cmt': data.comment,
        'desc': data.description,
        'sym': data.symbol,
        'src': data.source,
        'extensions': data.extensions if data.extensions else None,
    }

    # Remove None values and empty strings for cleaner output
    waypoint_dict = {k: v for k, v in waypoint_dict.items()
                     if v is not None and v != ''}

    return dumper.represent_dict(waypoint_dict)


# Register the custom representer
yaml.add_representer(gpxpy.gpx.GPXWaypoint, gpx_waypoint_representer)



def fix_timestamp_desc(desc: str, wps_time: datetime, fix_sec: bool = False):
    """fix the timestamp in the description field, preserving data after comma or newline"""
    parts = re.split(r'([,\n])', desc, maxsplit=1)
    time_part = parts[0].strip()
    remainder = ''.join(parts[1:]) if len(parts) > 1 else ''

    t = TimeFix.read_timestamp(time_part)
    if not t:
        return
    # copy seconds from wps.time if requested and desc timestamp has none
    if fix_sec:
        if wps_time and wps_time.second != 0 and t.second == 0:
            t = t + timedelta(seconds=wps_time.second)
    new_time = TimeFix.ref_format(t)
    new_desc = new_time + remainder
    if desc != new_desc:
        return new_desc


def read_yaml_file(input_file: IO[str], params: MyParams):
    """
    read a YAML gpx file, and return the list of waypoints
    """
    # read yaml file
    # float and ISO timestamp are automatically converted appropriately
    data = yaml.safe_load(input_file)

    waypoints = []
    for wps in data.get('gpx', {}).get('wpt', {}):

        wps = MyWaypoint(wpt_yaml=wps)

        # remove certain fields if requested
        if params.no_sym:
            wps.symbol = None
        if params.no_type:
            wps.type = None
        if params.no_extension:
            wps.extensions = None
        # set source if specified
        if params.waypoint_src:
            if wps.source and wps.source != params.waypoint_src:
                click.echo(f'  [{wps.name}] src: {wps.source} -> {params.waypoint_src}')
            wps.source = params.waypoint_src

        waypoints.append(wps)

    # we'll assume yaml files needs no further transformation for now.

    return waypoints


def read_gpx_file(gpx_file: IO[str], params: MyParams) -> GPX:
    """
    read a GPX file, and return the corresponding GPX object.
    gpx_file is already opened
    """

    # parse gpx file
    gpx = gpxpy.parse(gpx_file)

    # process the waypoints if some options are specified
    for wps in gpx.waypoints:
        _width_tracker.update(wps)
        # remove certain fields if requested
        if params.no_sym:
            wps.symbol = None
        if params.no_type:
            wps.type = None
        if params.no_extension:
            wps.extensions = None
        # set source if specified
        if params.waypoint_src:
            if wps.source and wps.source != params.waypoint_src:
                click.echo(f'  [{wps.name}] src: {wps.source} -> {params.waypoint_src}')
            wps.source = params.waypoint_src

    return gpx


def update_timestamp_to_localized(wps: MyWaypoint) -> None:
    """convert wps.time from UTC to local using stored timezone info"""
    if not wps.time:
        return
    addr = wps.get_address()
    tz_zone = getattr(addr, 'TimeZone', None) if addr else None
    if not tz_zone:
        click.echo(click.style(f'  [{wps.name}] error: no timezone info (run -u addr first)', fg='red'))
        return
    localized_dt = TimeFix.localize_timestamp(wps.time, tz_zone)
    if localized_dt != wps.time:
        click.echo(f'  "{wps.time}" -> "{localized_dt}"')
        wps.time = localized_dt


@rate_limit(max_calls=1, time_window=3.0, verbose=True)
def _reverse_geocode(latitude: float, longitude: float) -> Optional[geopy.Location]:
    """Rate-limited wrapper for geolocator reverse geocoding."""
    return _geolocator.reverse((latitude, longitude), language='en')


@persistent_cache(cache_file="geocoding_cache.json")
def get_address_from_coordinates(latitude: float, longitude: float) -> Optional[geopy.Location]:
    try:
        return _reverse_geocode(latitude=latitude, longitude=longitude)
    except Exception as e:
        click.echo(f"failed to do reverse geo-lookup: {e}", err=True)
        # traceback.print_exc()  # This prints the full stacktrace


def display_width(s: str) -> int:
    """Calculate the terminal display width of a string, accounting for wide chars and emojis."""
    import unicodedata
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ('W', 'F') else 1
    return width


def pad_to_width(s: str, target: int) -> str:
    """Pad a string with spaces to reach target display width."""
    return s + ' ' * (target - display_width(s))


def _get_loc(wp):
    addr = wp.get_address()
    if not addr:
        return ''
    city = getattr(addr, 'City', '') or ''
    if city:
        return city
    street = getattr(addr, 'StreetAddress', '') or ''
    return f'{street} 📍' if street else ''


def _get_addr_field(wp, field):
    addr = wp.get_address()
    return (getattr(addr, field, '') or '') if addr else ''


def print_waypoints(waypoints: List[MyWaypoint], columns: List[str]):
    idx_width = len(str(len(waypoints)))

    # compute column widths based on requested columns
    widths = {}
    if 'name' in columns:
        widths['name'] = max(display_width(wp.name) for wp in waypoints)
    if 'coord' in columns:
        widths['lon'] = max(len(f'{wp.longitude:.6f}') for wp in waypoints)
        widths['lat'] = max(len(f'{wp.latitude:.6f}') for wp in waypoints)
    if 'ele' in columns:
        widths['ele'] = max((len(f'{wp.elevation:.1f}') for wp in waypoints if wp.elevation), default=0)
    if 'lvl4' in columns:
        widths['lvl4'] = max((len(_get_addr_field(wp, 'LvL4')) for wp in waypoints), default=5)
    if 'tz' in columns:
        widths['tz'] = max((len(_get_addr_field(wp, 'TimeZone')) for wp in waypoints), default=0)
    if 'loc' in columns:
        widths['loc'] = max(display_width(_get_loc(wp)) for wp in waypoints)
    if 'addr' in columns:
        widths['addr'] = max((display_width(_get_addr_field(wp, 'Address')) for wp in waypoints), default=0)
    if 'src' in columns:
        widths['src'] = max((len(wp.source or '') for wp in waypoints), default=0)

    for i, wp in enumerate(waypoints, 1):
        parts = [f'[{i:>{idx_width}}]']

        for col in columns:
            if col == 'name':
                parts.append(pad_to_width(wp.name, widths['name']))
            elif col == 'coord':
                parts.append(f'[{wp.longitude:>{widths["lon"]}.6f}, {wp.latitude:>{widths["lat"]}.6f}]')
            elif col == 'ele':
                if wp.elevation:
                    parts.append(f'{wp.elevation:>{widths["ele"]}.1f}m')
                else:
                    parts.append(' ' * (widths['ele'] + 1))
            elif col == 'time':
                parts.append(str(wp.time or ''))
            elif col == 'lvl4':
                parts.append(f'{_get_addr_field(wp, "LvL4"):<{widths["lvl4"]}}')
            elif col == 'tz':
                parts.append(f'{_get_addr_field(wp, "TimeZone"):<{widths["tz"]}}')
            elif col == 'loc':
                parts.append(pad_to_width(_get_loc(wp), widths['loc']))
            elif col == 'addr':
                parts.append(pad_to_width(_get_addr_field(wp, 'Address'), widths['addr']))
            elif col == 'desc':
                parts.append(wp.description or '')
            elif col == 'src':
                parts.append(f'{wp.source or "":<{widths["src"]}}')

        print(' '.join(parts))


def write_waypoints_to_gpx(waypoints: List[MyWaypoint], output_file: IO) -> None:
    """
    Save the GPX object back to file.
    """
    try:
        gpx = GPX()
        # add our extensions
        gpx.nsmap['gpxx'] = 'http://www.garmin.com/xmlschemas/GpxExtensions/v3'
        # todo: convert MyWaypoints to GPXWaypoints
        gpx.waypoints = [waypoint.to_gpx() for waypoint in waypoints]

        # Write the GPX file
        output_file.write(gpx.to_xml())
        click.echo(f"Successfully wrote {len(gpx.waypoints)} waypoints to {output_file.name}")
    except Exception as e:
        click.echo(f"Error writing to GPX file: {e}", err=True)
        traceback.print_exc()  # This prints the full stacktrace


def write_waypoints_to_yaml(waypoints: List[MyWaypoint], output_file: IO) -> None:
    """
    Write the sorted waypoints to a new YAML file.
    """
    # todo: this is done via GPX object, need to make it more generic
    try:
        # Write header comments
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        output_file.write("# GPX Waypoints Export\n")
        output_file.write("# Generated by gpx_util.py\n")
        output_file.write(f"# Date: {timestamp}\n")
        output_file.write(f"# Number of waypoints: {len(waypoints)}\n")
        output_file.write("#\n")
        yaml.dump({'gpx': {'wpt': waypoints}}, output_file,
                  default_flow_style=False, sort_keys=False, allow_unicode=True)
        click.echo(f"Successfully wrote {len(waypoints)} waypoints to {output_file.name}")
    except Exception as e:
        click.echo(f"Error writing to YAML file: {e}", err=True)
        traceback.print_exc()  # This prints the full stacktrace


# save via converting to MyWaypoints first
def write_gpx_wp_to_yaml(waypoints: List[GPXWaypoint], output_file: IO) -> None:
    """
    Write the sorted waypoints to a new YAML file.
    """
    # first convert the waypoints into a list of my arrays
    waypoints = [MyWaypoint(wpt=wps) for wps in waypoints]

    #
    try:
        # Write header comments
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        output_file.write("# GPX Waypoints Export\n")
        output_file.write("# Generated by gpx_util.py\n")
        output_file.write(f"# Date: {timestamp}\n")
        output_file.write(f"# Number of waypoints: {len(waypoints)}\n")
        output_file.write("#\n")
        yaml.dump({'gpx': {'wpt': waypoints}}, output_file,
                  default_flow_style=False, sort_keys=False, allow_unicode=True)
        click.echo(f"Successfully wrote {len(waypoints)} waypoints to {output_file.name}")
    except Exception as e:
        click.echo(f"Error writing to YAML file: {e}", err=True)


def process_waypoint_timestamp(wps, params):
    # todo: convert timestamp from desc/comment, if any
    # todo: do this based on command line parameters, not always

    if params.desctime:
        # fix timestamp in description, if any
        if wps.description:
            v = fix_timestamp_desc(wps.description, wps.time, params.fixsec)
            if v:
                click.echo(f'  "{wps.description}" -> "{v}"')
                wps.description = v

    # if timezone option specified, process time into coordinate target timezone
    if params.localtime:
        update_timestamp_to_localized(wps)

    # backfill wps.time from desc field (Garmin 60csx)
    if params.desc2time:
        backfill_time_from_desc(wps)


def backfill_time_from_desc(wps: MyWaypoint):
    """
    Backfill wps.time from the description field for Garmin 60csx waypoints.
    Requires timezone info in the waypoint's address extension (from prior -u addr).
    """
    if not wps.description:
        return

    # get timezone from waypoint address
    addr = wps.get_address()
    tz_name = getattr(addr, 'TimeZone', None) if addr else None
    if not tz_name:
        click.echo(f'  [{wps.name}] skipped: no timezone info (run -u addr first)')
        return

    # parse the desc field into a naive datetime
    naive_dt = TimeFix.parse_normalized_timestamp(wps.description)
    if not naive_dt:
        click.echo(f'  [{wps.name}] skipped: cannot parse desc "{wps.description}"')
        return

    # localize it
    localized = TimeFix.localize_naive(naive_dt, tz_name)

    # sanity check: if wps.time exists, verify it matches (may be stored as UTC)
    if wps.time:
        existing_naive = wps.time.replace(tzinfo=None)
        new_naive = localized.replace(tzinfo=None)
        if existing_naive == new_naive:
            click.echo(f'  [{wps.name}] confirmed: time matches desc (tz was missing)')
        else:
            click.echo(f'  [{wps.name}] warning: time={wps.time} differs from desc={localized}')

    wps.time = localized
    click.echo(f'  [{wps.name}] time set to {localized}')


def save_address_to_my_waypoint(wps: MyWaypoint, address: MyAddress):
    """save the address data into the waypoint extension"""
    # create the extension element
    if not wps.extensions:
        wps.extensions = [WaypointExtension(address=address)]
        return

    # find the existing WaypointExtension under wps.extensions
    ext = next((ext for ext in wps.extensions if isinstance(ext, WaypointExtension)), None)
    if ext:
        # update the address field
        ext.address = address
    else:
        # create a new WaypointExtension and append it to wps.extensions
        wps.extensions.append(WaypointExtension(address=address))


# -------------------- Major Steps --------------------


def read_input_file(gpx_files, params: MyParams):
    """Read the input GPX or YAML files, and return the list of waypoints"""
    # todo: assume we either get gpx or yaml, not a mix, haha
    click.echo(f"Reading {len(gpx_files)} files...")

    waypoints = []
    for file in gpx_files:
        click.echo(f'{file.name}:') if params.debug else None
        if file.name.endswith('.yaml'):
            # todo: finish reading yaml file, figure out what to return
            wps = read_yaml_file(file, params)
            waypoints.extend(wps)
        else:
            gpx = read_gpx_file(file, params)
            wps = gpx.waypoints
            waypoints.extend(wps)
        click.echo(f'  {file.name}: {len(wps)} waypoint(s) total') if params.debug else None

    # convert GPX waypoints into MyWaypoints if needed
    if waypoints and isinstance(waypoints[0], GPXWaypoint):
        waypoints = [MyWaypoint(wpt=wps) for wps in waypoints]

    click.echo(f"DONE.  {len(gpx_files)} files read.")
    return waypoints


def process_waypoints(waypoints: List[MyWaypoint], params: MyParams):
    """Process the list of waypoints, applying any necessary transformations."""
    verbose = params.address or params.localtime or params.tz or params.desc2time
    total_waypoints = len(waypoints)
    for index, wps in enumerate(waypoints, 1):
        if verbose:
            click.echo(f'[{index}/{total_waypoints}] {click.style(wps.name, fg="bright_green")}')

        # first fetch the address and timezone data
        address_ext = None
        if params.address:
            location = get_address_from_coordinates(wps.latitude, wps.longitude)
            if location:
                timezone = TimeZoneGps.get_timezone(wps.latitude, wps.longitude)
                address: MyAddress = MyAddress(location=location, timezone=timezone)
                save_address_to_my_waypoint(wps, address)
                click.echo(f'    {click.style(address.Address, fg="bright_white")}')
                click.echo(f'    {address}')
                click.echo(f'    TZ: {timezone}')
            else:
                click.echo(f'    {click.style("failed to get address, exiting ...", fg="bright_red")}')
                exit(1)

        # recompute timezone from GPS coords and store in extension (skip if addr already ran)
        if params.tz and not params.address:
            addr = wps.get_address()
            if not addr:
                click.echo(click.style(f'  [{wps.name}] error: no address data (run -u addr first)', fg='red'))
            else:
                tz_zone = TimeZoneGps.get_timezone(wps.latitude, wps.longitude)
                if tz_zone:
                    old_tz = getattr(addr, 'TimeZone', None)
                    if old_tz != tz_zone:
                        click.echo(f'  [{wps.name}] tz: {old_tz} -> {tz_zone}')
                    addr.TimeZone = tz_zone

        # now process the waypoint timestamp if needed
        # we do this before sort, so we can sort properly
        process_waypoint_timestamp(wps, params)

        # remove extra fields if Garmin mode
        if params.garmin:
            address_to_fix: MyAddress = wps.get_address()
            if address_to_fix:
                # address_to_fix.PostalCode = None  # garmin needs this to be after country
                address_to_fix.Address = None
                address_to_fix.CountryCode = None
                address_to_fix.TimeZone = None
                address_to_fix.LvL4 = None

    # Sort waypoints by name or time if specified
    if params.sort_by:
        if params.sort_by == 'name':
            waypoints.sort(key=lambda w: w.name)
        elif params.sort_by == 'time':
            waypoints.sort(key=lambda w: (w.time, w.name))
        elif params.sort_by == 'desc':
            waypoints.sort(key=lambda w: w.description if w.description else '')
        elif params.sort_by == 'cmt':
            waypoints.sort(key=lambda w: w.comment if w.comment else '')


def save_waypoints(waypoints, params: MyParams):
    """Write the waypoints to GPX or YAML file."""

    # when get here, params.output_file has a value
    if params.output_file.name.endswith('.gpx'):
        write_waypoints_to_gpx(waypoints, params.output_file)
    elif params.output_file.name.endswith('.yaml'):
        write_waypoints_to_yaml(waypoints, params.output_file)
    else:
        click.echo(f"Error: Unsupported output file format: {params.output_file.name}", err=True)
        return


# -------------------- Main functions / Entrypoint --------------------


@click.command(
    context_settings={'help_option_names': ['-h', '--help']},
    epilog="""\b
Update options (-u):
  localtime convert wps.time from UTC to local (requires stored tz)
  desctime  normalize timestamp format in desc field
  fixsec    copy seconds from wps.time to desc (use with desctime)
  desc2time backfill wps.time from normalized desc time
  time2cmt  save wps.time as string to comment field (backup)
  addr      fetch address/timezone from GPS coords, store in extension
  tz        recompute timezone from GPS coords (requires existing addr data)
Examples:
  gpxutil.py waypoints.gpx
  gpxutil.py waypoints.yaml --map
  gpxutil.py trip.yaml -u desctime,localtime,addr --src etrex-solar -s time -o output.yaml
  gpxutil.py trip.yaml --date 2025-04 --date 2025-09-08..2w
  gpxutil.py trip.yaml -l vancouver -l seattle --map
  gpxutil.py --query 49.2827 -123.1207""")
@click.argument('gpx_files', nargs=-1, type=click.File(), metavar='[FILES (.gpx | .yaml)]...')
@optgroup.group('Display')
@optgroup.option('-c', '--columns', type=ColumnsType(), default='name,coord,ele,time,lvl4,loc',
                 help='columns to display (name,coord,ele,time,lvl4,tz,loc,addr,src,desc)')
@optgroup.option('--map', 'show_map', is_flag=True, default=False,
                 help='open waypoints in OpenStreetMap')
@optgroup.group('Filtering')
@optgroup.option('-n', '--name', 'name_filter', multiple=True, metavar='TERM',
                 help='filter by name, case-insensitive substring match')
@optgroup.option('-d', '--date', 'date_range', type=DateRangeType(), multiple=True, metavar='RANGE',
                 help='filter by date, repeatable (2025, 2025-04, 2025-04-01..2025-04-15, '
                      '2024.., ..2023, 2025-04-01..7d, 7d..2025-04-15)')
@optgroup.option('-l', '--loc', 'location', multiple=True, metavar='TERM',
                 help='filter by location, repeatable (ca, ca-bc, vancouver)')
@optgroup.option('-i', '--index', 'index_range', type=IndexRangeType(), multiple=True, metavar='RANGE',
                 help='filter by index, repeatable (5, 5..10, 5.., ..10, 5,10,20..25)')
@optgroup.option('--missing', type=click.Choice(['lvl4', 'tz', 'addr', 'time']),
                 help='filter to waypoints missing a field')
@optgroup.group('Transform')
@optgroup.option('-u', '--update', type=UpdateOptionType(),
                 help='update waypoint fields (localtime,desctime,fixsec,desc2time,addr,tz)')
@optgroup.option('--src', 'waypoint_src',
                 help='set src field on waypoints')
@optgroup.option('--strip', 'delete', type=DeleteOptionType(),
                 help='strip waypoint fields (sym,type,extension)')
@optgroup.option('--garmin', is_flag=True, default=False,
                 help='strip custom fields (tz, countrycode, lvl4, address) for Garmin device import')
@optgroup.option('--refresh', is_flag=False, flag_value='0d', default=None, metavar='[AGE]',
                 help='re-fetch address data, use with -u addr (optionally if older than AGE, e.g. 30d, 3m, 1y)')
@optgroup.group('Output')
@optgroup.option('-s', '--sort', 'sort_by', type=click.Choice(['name', 'time', 'desc', 'cmt']),
                 help='sort waypoints by field')
@optgroup.option('-o', '--output', 'output_file', type=click.File('w'),
                 help='export to file (.gpx | .yaml)')
@optgroup.group('Utility')
@optgroup.option('--query', nargs=2, type=float, metavar='LAT LON',
                 help='reverse geocode a coordinate')
@optgroup.option('--debug', is_flag=True, default=False,
                 help='enable verbose logging')
@click.version_option('2.0.0', '-V', '--version')
def main(gpx_files,
         columns, show_map: bool,
         name_filter, date_range, location, index_range, missing,
         update: set[UpdateOption], waypoint_src: Optional[str], delete: set[DeleteOption],
         garmin: bool, refresh,
         sort_by: Optional[str], output_file,
         query, debug: bool):
    """GPX waypoint utility v2.0.0 — read, transform, and export waypoints."""

    if query:
        latitude, longitude = query
        location = get_address_from_coordinates(latitude, longitude)
        address: MyAddress = MyAddress(location=location)
        click.echo(f"    {address.Address}")
        click.echo(f"    {address}")
        return

    if not gpx_files:
        click.echo(click.get_current_context().get_help())
        return

    global _width_tracker
    _width_tracker = MyWidthTracker()  # initialize width tracker

    _params = MyParams(update, delete, waypoint_src, sort_by, output_file, garmin, show_map, debug)

    # read the input file into a list of waypoints
    waypoints = read_input_file(gpx_files, _params)
    if not waypoints:
        click.echo('No waypoints found.  Exiting.')
        return

    if name_filter:
        click.echo(f'Name filter: {click.style(", ".join(name_filter), fg="cyan")}')
        total = len(waypoints)
        lower_terms = [t.lower() for t in name_filter]
        waypoints = [wp for wp in waypoints if any(t in wp.name.lower() for t in lower_terms)]
        click.echo(f'Matched: {click.style(str(len(waypoints)), fg="green")}/{total} waypoints')
        if not waypoints:
            click.echo(click.style('No waypoints matching name.', fg='red'))
            return

    if date_range:
        for start_date, end_date in date_range:
            start_str = click.style(str(start_date), fg='cyan') if start_date else click.style('*', fg='yellow')
            end_str = click.style(str(end_date), fg='cyan') if end_date else click.style('*', fg='yellow')
            click.echo(f'Date range: {start_str} .. {end_str}')
        total = len(waypoints)
        waypoints = filter_by_date(waypoints, date_range)
        click.echo(f'Matched: {click.style(str(len(waypoints)), fg="green")}/{total} waypoints')
        if not waypoints:
            click.echo(click.style('No waypoints in date range.', fg='red'))
            return

    if location:
        click.echo(f'Location filter: {click.style(", ".join(location), fg="cyan")}')
        total = len(waypoints)
        waypoints = filter_by_location(waypoints, location)
        click.echo(f'Matched: {click.style(str(len(waypoints)), fg="green")}/{total} waypoints')
        if not waypoints:
            click.echo(click.style('No waypoints matching location.', fg='red'))
            return

    if index_range:
        # flatten: multiple=True gives tuple of lists, each list from comma-separated input
        all_ranges = [r for group in index_range for r in group]
        for start, end in all_ranges:
            start_str = click.style(str(start), fg='cyan') if start else click.style('*', fg='yellow')
            end_str = click.style(str(end), fg='cyan') if end else click.style('*', fg='yellow')
            click.echo(f'Index range: {start_str} .. {end_str}')
        total = len(waypoints)
        waypoints = filter_by_index(waypoints, all_ranges)
        click.echo(f'Matched: {click.style(str(len(waypoints)), fg="green")}/{total} waypoints')
        if not waypoints:
            click.echo(click.style('No waypoints matching index.', fg='red'))
            return

    if missing:
        field_map = {
            'lvl4': ('LvL4', lambda wp: _get_addr_field(wp, 'LvL4')),
            'tz': ('TimeZone', lambda wp: _get_addr_field(wp, 'TimeZone')),
            'addr': ('Address', lambda wp: _get_addr_field(wp, 'Address')),
            'time': ('time', lambda wp: wp.time),
        }
        label, getter = field_map[missing]
        total = len(waypoints)
        waypoints = [wp for wp in waypoints if not getter(wp)]
        click.echo(f'Missing {label}: {click.style(str(len(waypoints)), fg="green")}/{total} waypoints')
        if not waypoints:
            click.echo(click.style(f'All waypoints have {label}.', fg='green'))
            return

    if refresh:
        max_age = parse_relative(refresh)
        if isinstance(max_age, relativedelta):
            max_age = timedelta(days=max_age.months * 30 + max_age.years * 365)
        set_refresh_mode(max_age)

    # process the list of waypoints, apply requested transformations
    process_waypoints(waypoints, _params)

    print_waypoints(waypoints, columns)

    if _params.output_file:
        save_waypoints(waypoints, _params)
    if _params.show_map:
        from gpx_map_viewer import display_gpx_coordinates_in_browser
        html_file = display_gpx_coordinates_in_browser(waypoints)


if __name__ == '__main__':
    main()
