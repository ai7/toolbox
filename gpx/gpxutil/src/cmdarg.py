"""
Command-line argument related stuff
"""

import click
import enum
from typing import List, Optional, Tuple, IO, Any


class DeleteOption(str, enum.Enum):
    """fields we allow to trim from waypoints"""
    SYM = 'sym'
    TYPE = 'type'
    EXTENSION = 'extension'


class UpdateOption(str, enum.Enum):
    """various field transformations we support"""
    TIME = 'time'
    TIME_ZONE = 'tz'
    ADDRESS = 'addr'


class DeleteOptionType(click.ParamType):
    name = 'delete_option'

    def convert(self, value, param, ctx):
        if value is None:
            return None
        try:
            # Split the input string by commas and convert to set of enum values
            return {DeleteOption(v.strip()) for v in value.split(',')}
        except ValueError:
            self.fail(
                f'"{value}" is not a valid delete option. Choose from: {", ".join(e.value for e in DeleteOption)}',
                param,
                ctx,
            )


class UpdateOptionType(click.ParamType):
    name = 'update_option'

    def convert(self, value, param, ctx):
        if value is None:
            return None
        try:
            # Split the input string by commas and convert to set of enum values
            return {UpdateOption(v.strip()) for v in value.split(',')}
        except ValueError:
            self.fail(
                f'"{value}" is not a valid update option. Choose from: {", ".join(e.value for e in UpdateOption)}',
                param,
                ctx,
            )


class MyParams:
    """Holds parameters for program operation"""

    time: bool = False      # fix time values
    timezone: bool = False  # fetch tz info
    address: bool = False   # fetch address

    no_sym: bool = False  # remove sym field under waypoint
    no_type: bool = False  # strip type field under waypoint
    no_extension: bool = False  # strip extension from gpx file

    def __init__(self, update: set[UpdateOption], delete: set[DeleteOption],
                 waypoint_src: Optional[str], sort_by: Optional[str], output_file,
                 garmin: bool, debug: bool):
        """convert from click input to runtime params for use"""

        self.waypoint_src = waypoint_src  # tag waypoint with specific src value
        self.sort_by = sort_by            # order waypoints by name or time
        self.output_file = output_file    # write output file
        self.debug = debug                # enable more debug output
        self.garmin = garmin              # remove some custom fields

        if update:
            self.time: bool = True if UpdateOption.TIME in update else False
            self.timezone: bool = True if UpdateOption.TIME_ZONE in update else False
            self.address: bool = True if UpdateOption.ADDRESS in update else False
        if delete:
            self.no_extension: bool = True if DeleteOption.EXTENSION in delete else False
            self.no_sym: bool = True if DeleteOption.SYM in delete else False
            self.no_type: bool = True if DeleteOption.TYPE in delete else False
