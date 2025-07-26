"""
Timestamp related stuff
"""

# moptionx GPS: Jul 20, 2018  6:14 pm

# %b: Month name abbreviated (Jul)
# %d: Day of month (20)
# %Y: Year with century (2018)
# %I: Hour (12-hour clock)
# %H: Hour (24-hour clock)
# %M: Minute
# %p: AM/PM

from typing import List, Optional, Tuple, IO, Any

import pytz

from datetime import datetime
from timezonefinder import TimezoneFinder


class TimeFix:

    # reference date/time format for the description field
    REF_DESCRIPTION = '%Y-%m-%d %H:%M:%S'

    # formats that we'll try to decode from.
    # These are typically date/time stored by various apps as String for reference.
    FORMATS = [
        "%b %d, %Y %I:%M %p",  # Jul 20, 2018  6:14 pm
        "%b %d, %Y %H:%M",     # Jul 20, 2018  18:14
        "%Y-%m-%d %I:%M %p",   # 2018-07-20 6:14 pm
        '%d-%b-%y %H:%M:%S',   # 06-AUG-18 7:57:56, 60csx
        REF_DESCRIPTION        # 2025-03-06 14:26:54
    ]

    @staticmethod
    def read_timestamp(time_str: str, latitude: float = None, longitude: float = None) -> Optional[datetime]:
        """read a string timestamp into datetime"""
        for fmt in TimeFix.FORMATS:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

    @staticmethod
    def ref_format(timestamp: datetime):
        """convert timestamp into our preferred format"""
        return timestamp.strftime(TimeFix.REF_DESCRIPTION)

    @staticmethod
    def localize_timestamp(timestamp: datetime, timezone: str):
        """convert timestamp to the specified timezone"""
        target_timezone = pytz.timezone(timezone)
        return timestamp.astimezone(target_timezone)


class TimeZoneGps:

    # lazily initialized
    _timezonefinder: Optional[TimezoneFinder] = None

    @staticmethod
    def get_timezonefinder() -> TimezoneFinder:
        if TimeZoneGps._timezonefinder is None:
            TimeZoneGps._timezonefinder = TimezoneFinder()  # this is slow
        return TimeZoneGps._timezonefinder

    @staticmethod
    def get_timezone(latitude: float, longitude: float) -> Optional[str]:
        """
        Convert GPS coordinates to timezone name.
        Returns the timezone as string, and the utc_offset
        Returns None if timezone cannot be determined.
        """
        try:
            # get the TimezoneFinder object, create it (slow) if necessary
            tf = TimeZoneGps.get_timezonefinder()
            # compute timezone based on gps coordinate
            return tf.timezone_at(lat=latitude, lng=longitude)
        except Exception:
            return None

    @staticmethod
    def tz_offset(timezone: str) -> float:
        """calculates the offset of a given timezone."""
        # Get the timezone object
        tz = pytz.timezone(timezone)
        # Get current UTC offset in hours
        return datetime.now(tz).utcoffset().total_seconds() / 3600
