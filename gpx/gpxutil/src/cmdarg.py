"""
Command-line argument related stuff
"""

import click
import enum
from typing import List, Optional, Tuple, IO, Any
from wpfilter import parse_date_range


class DeleteOption(str, enum.Enum):
    """fields we allow to trim from waypoints"""
    SYM = 'sym'
    TYPE = 'type'
    EXTENSION = 'extension'


class UpdateOption(str, enum.Enum):
    """various field transformations we support"""
    DESCTIME = 'desctime'
    FIXSEC = 'fixsec'
    LOCALTIME = 'localtime'
    TZ = 'tz'
    ADDRESS = 'addr'
    DESC2TIME = 'desc2time'


class DeleteOptionType(click.ParamType):
    name = 'fields'

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
    name = 'action'

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


VALID_COLUMNS = ['name', 'coord', 'ele', 'time', 'lvl4', 'tz', 'loc', 'addr', 'desc', 'src']


class ColumnsType(click.ParamType):
    name = 'columns'

    def convert(self, value, param, ctx):
        if value is None:
            return None
        cols = [c.strip() for c in value.split(',')]
        invalid = [c for c in cols if c not in VALID_COLUMNS]
        if invalid:
            self.fail(
                f'invalid column(s): {", ".join(invalid)}.\n'
                f'Choose from: {", ".join(VALID_COLUMNS)}',
                param, ctx,
            )
        return cols


class IndexRangeType(click.ParamType):
    """Parse index ranges like 5, 5..10, 5.., ..10, or comma-separated 5,10,20..25 (1-based)."""
    name = 'index_range'

    def _parse_one(self, s):
        s = s.strip()
        if '..' in s:
            left, right = s.split('..', 1)
            return (int(left) if left else None, int(right) if right else None)
        else:
            n = int(s)
            return (n, n)

    def convert(self, value, param, ctx):
        if value is None:
            return None
        try:
            return [self._parse_one(part) for part in value.split(',')]
        except ValueError:
            self.fail(
                f'"{value}" is not a valid index range. Use N, N..M, N.., ..M, or comma-separated',
                param, ctx,
            )


class DateRangeType(click.ParamType):
    name = 'date_range'

    def convert(self, value, param, ctx):
        if value is None:
            return None
        try:
            return parse_date_range(value)
        except ValueError as e:
            self.fail(str(e), param, ctx)


class MyParams:
    """Holds parameters for program operation"""

    desctime: bool = False   # normalize timestamp in desc field
    fixsec: bool = False     # copy seconds from wps.time to desc (use with fixdesc)
    localtime: bool = False  # convert wps.time from UTC to local
    tz: bool = False         # recompute timezone from GPS coords
    address: bool = False    # fetch address
    desc2time: bool = False  # backfill time from desc (Garmin 60csx)

    no_sym: bool = False  # remove sym field under waypoint
    no_type: bool = False  # strip type field under waypoint
    no_extension: bool = False  # strip extension from gpx file

    def __init__(self, update: set[UpdateOption], delete: set[DeleteOption],
                 waypoint_src: Optional[str], sort_by: Optional[str], output_file,
                 garmin: bool, show_map: bool, debug: bool):
        """convert from click input to runtime params for use"""

        self.waypoint_src = waypoint_src  # tag waypoint with specific src value
        self.sort_by = sort_by            # order waypoints by name or time
        self.output_file = output_file    # write output file
        self.debug = debug                # enable more debug output
        self.garmin = garmin              # remove some custom fields
        self.show_map = show_map          # show waypoints in open street map

        if update:
            self.desctime: bool = True if UpdateOption.DESCTIME in update else False
            self.fixsec: bool = True if UpdateOption.FIXSEC in update else False
            self.localtime: bool = True if UpdateOption.LOCALTIME in update else False
            self.tz: bool = True if UpdateOption.TZ in update else False
            self.address: bool = True if UpdateOption.ADDRESS in update else False
            self.desc2time: bool = True if UpdateOption.DESC2TIME in update else False
        if delete:
            self.no_extension: bool = True if DeleteOption.EXTENSION in delete else False
            self.no_sym: bool = True if DeleteOption.SYM in delete else False
            self.no_type: bool = True if DeleteOption.TYPE in delete else False
