#!/usr/bin/env python
#
# my awesome GPX utility
#
# i: info
# q: query for address based on gpx data

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, IO, Any

import click
import geopy
import yaml
import gpxpy
import re
from gpxpy.gpx import GPXWaypoint, GPX
from geopy.geocoders import Nominatim
import traceback

# my stuff
from wpmodel import MyWaypoint, WaypointExtension, MyAddress, MyWidthTracker
from cmdarg import UpdateOption, UpdateOptionType, DeleteOption, DeleteOptionType, MyParams
from timefix import TimeFix, TimeZoneGps
from geocache import persistent_cache
from rate_limiter import rate_limit


# lazily initialized
_width_tracker: Optional[MyWidthTracker] = None
_my_params: Optional[MyParams] = None

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


def compute_max_name(waypoints: List[MyWaypoint]) -> int:
    name_len = 0
    for w in waypoints:
        name_len = max(name_len, len(w.name))
    return name_len


def fix_timestamp_desc(timestamp: str, wps_time: datetime):
    """fix the timestamp in the description field, if any"""
    # get the first part before newline or comma, in case the desc
    # field contains additional data.
    timestamp = re.split('[\n,]', timestamp)[0]
    t = TimeFix.read_timestamp(timestamp)
    if not t:
        return
    # preserve the seconds on time field to the string version
    if wps_time and wps_time.second != 0 and t.second == 0:
        t = t + timedelta(seconds=wps_time.second)
    # generate a new time, and return it if it's different from what we started with
    new_time = TimeFix.ref_format(t)
    if timestamp != new_time:
        return new_time


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
        if not wps.source and params.waypoint_src:
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
        if not wps.source and params.waypoint_src:
            wps.source = params.waypoint_src

    return gpx


def update_timestamp_to_localized(waypoint: GPXWaypoint) -> None:
    """update the gpx time field to a localized time"""
    # if we have no time data, just return
    if not waypoint.time:
        return
    # get the timezone based on the gps coordinate
    tz_zone = TimeZoneGps.get_timezone(waypoint.latitude, waypoint.longitude)
    localized_dt = TimeFix.localize_timestamp(waypoint.time, tz_zone)
    click.echo(f'  "{waypoint.time}" -> "{localized_dt}"')
    waypoint.time = localized_dt


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


def print_waypoints(waypoints: List[MyWaypoint]):
    name_len = compute_max_name(waypoints)
    counter = 1
    for waypoint in waypoints:
        # format the elevation string
        ele_str = f'{waypoint.elevation:>11}' if waypoint.elevation else ''

        # # compute timezone string
        # tz_zone = TimeZoneGps.get_timezone(waypoint.latitude, waypoint.longitude) if timezone else None
        # if tz_zone:
        #     tz_offset = TimeZoneGps.tz_offset(tz_zone)
        #     localized_dt = TimeFix.localize_timestamp(waypoint.time, tz_zone)
        #
        # timezone_str = f'{tz_zone} (UTC{tz_offset:+.2f})' if timezone and tz_zone else ''
        # now print the info
        print(f'[{counter:>3}] {waypoint.name:<{name_len}}, [{waypoint.longitude:>19}, {waypoint.latitude:>19}], '
              f'elev: {ele_str:>15}, {waypoint.description}, {waypoint.time}')
        counter += 1


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

    if params.time:
        # fix timestamp in description, if any
        if wps.description:
            v = fix_timestamp_desc(wps.description, wps.time)
            if v:
                click.echo(f'  "{wps.description}" -> "{v}"')
                wps.description = v

    # if timezone option specified, process time into coordinate target timezone
    if params.timezone:
        update_timestamp_to_localized(wps)


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
    total_waypoints = len(waypoints)
    for index, wps in enumerate(waypoints, 1):
        click.echo(f'[{index}/{total_waypoints}] {click.style(wps.name, fg="bright_green")}')
        # first process the waypoint timestamp if needed
        # we do this before sort, so we can sort properly
        # todo: is this compatible with yaml version?
        process_waypoint_timestamp(wps, params)

        # then fetch the address data
        address_ext = None
        if params.address:
            location = get_address_from_coordinates(wps.latitude, wps.longitude)
            if location:
                timezone = TimeZoneGps.get_timezone(wps.latitude, wps.longitude)  # to save on address
                address: MyAddress = MyAddress(location=location, timezone=timezone)
                save_address_to_my_waypoint(wps, address)
                click.echo(f'    {click.style(address.Address, fg="bright_white")}')
                click.echo(f'    {address}')  # obj and its fields
                click.echo(f'    TZ: {timezone}')
            else:
                click.echo(f'    {click.style("failed to get address, exiting ...", fg="bright_red")}')
                exit(1)

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
            waypoints.sort(key=lambda w: w.time)
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


@click.group()
def main():
    pass


@main.command(name='i', help='input GPX files to read (.gpx | .yaml)')
@click.argument('gpx_files', nargs=-1, type=click.File())
@click.option('-u', '--update', type=UpdateOptionType(),
              help='update fields accordingly (time,tz,addr)')
@click.option('-d', '--delete', type=DeleteOptionType(),
              help='delete specific fields (sym,type,extension)')
@click.option('-s', '--waypoint-src',
              help='set waypoint src field if empty')
@click.option('-b', '--sort-by', type=click.Choice(['name', 'time', 'desc', 'cmt']),
              help='Sort waypoints by name or time [default: none]')
@click.option('-o', '--output', 'output_file', type=click.File('w'),
              help='write waypoints to file (.gpx | .yaml)')
@click.option('--garmin', is_flag=True, default=False,
              help='output garmin compatible gpx')
@click.option('--debug', is_flag=True, default=False,
              help='enable more debugging logs')
def process_files(gpx_files, update: set[UpdateOption], delete: set[DeleteOption],
                  waypoint_src: Optional[str], sort_by: Optional[str], output_file,
                  garmin: bool, debug: bool):
    """Process multiple input files."""
    # print local variables, aka input parameters, for debugging
    # print(locals())
    # return

    if not gpx_files:
        click.echo('No input files specified. Exiting.')
        return

    global _width_tracker, _my_params
    _width_tracker = MyWidthTracker()  # initialize width tracker

    _params = MyParams(update, delete, waypoint_src, sort_by, output_file, garmin, debug)

    # read the input file into a list of waypoints
    waypoints = read_input_file(gpx_files, _params)
    if not waypoints:
        click.echo('No waypoints found.  Exiting.')
        return

    # process the list of waypoints, apply requested transformations
    process_waypoints(waypoints, _params)

    print_waypoints(waypoints)

    if _params.output_file:
        save_waypoints(waypoints, _params)


@main.command(name='q', help='query address for GPS coordinate')
@click.argument('latitude', type=float, required=True)
@click.argument('longitude', type=float, required=True)
def query_address(latitude: float, longitude: float):
    """Query address for GPS coordinate."""
    location = get_address_from_coordinates(latitude, longitude)
    address: MyAddress = MyAddress(location=location)
    click.echo(f"    {address.Address}")
    click.echo(f"    {address}")


if __name__ == '__main__':
    main()
