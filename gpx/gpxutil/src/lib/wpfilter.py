"""
Waypoint filtering — shared between CLI (cmdarg.py) and map viewer (map_filter.js).

Date range syntax:
  Partial dates (expand to full range of that period):
    2025           -> Jan 1, 2025 .. Dec 31, 2025
    2025-04        -> Apr 1, 2025 .. Apr 30, 2025
    2025-04-23     -> Apr 23 .. Apr 23

  Explicit range (two dates separated by ..):
    2025-04..2025-06       -> Apr 1 .. Jun 30
    2025-04-01..2025-04-15 -> Apr 1 .. Apr 15

  Open-ended range (one side of .. is empty):
    2024..         -> Jan 1, 2024 .. no upper bound
    ..2023         -> no lower bound .. Dec 31, 2023

  Relative offset (one side is Nd/Nw/Nm/Ny):
    2025-04-01..7d -> Apr 1 .. Apr 8
    7d..2025-04-15 -> Apr 8 .. Apr 15
    2025-04..3m    -> Apr 1 .. Jul 1

  Offset suffixes: d=days, w=weeks, m=months, y=years

Location filtering:
  Matches against LvL4 (ISO3166-2, e.g. CA-BC), country code, or city.
  Case-insensitive substring match.
"""

import re
import calendar
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def parse_partial_date(s):
    """Parse YYYY, YYYY-MM, or YYYY-MM-DD and return (start_date, end_date)."""
    if re.match(r'^\d{4}$', s):
        year = int(s)
        return date(year, 1, 1), date(year, 12, 31)
    elif re.match(r'^\d{4}-\d{2}$', s):
        year, month = int(s[:4]), int(s[5:7])
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)
    else:
        d = date.fromisoformat(s)
        return d, d


def parse_relative(s):
    """Parse a relative offset like 7d, 2w, 3m, 1y and return a timedelta/relativedelta."""
    m = re.match(r'^(\d+)([dwmy])$', s)
    if not m:
        raise ValueError(f'invalid relative offset: {s}')
    n, unit = int(m.group(1)), m.group(2)
    if unit == 'd':
        return timedelta(days=n)
    elif unit == 'w':
        return timedelta(weeks=n)
    elif unit == 'm':
        return relativedelta(months=n)
    elif unit == 'y':
        return relativedelta(years=n)


def is_relative(s):
    return bool(re.match(r'^\d+[dwmy]$', s))


def parse_date_range(value):
    """
    Parse a flexible date range string into (start_date, end_date) tuple.
    Either date may be None for open-ended ranges.
    """
    if '..' in value:
        left, right = value.split('..', 1)
        if not left and not right:
            raise ValueError('both sides of .. cannot be empty')
        elif not left:
            start = None
            end = parse_partial_date(right)[1]
        elif not right:
            start = parse_partial_date(left)[0]
            end = None
        else:
            left_rel, right_rel = is_relative(left), is_relative(right)
            if not left_rel and not right_rel:
                start = parse_partial_date(left)[0]
                end = parse_partial_date(right)[1]
            elif not left_rel and right_rel:
                start = parse_partial_date(left)[0]
                end = start + parse_relative(right)
            elif left_rel and not right_rel:
                end = parse_partial_date(right)[1]
                start = end - parse_relative(left)
            else:
                raise ValueError('both parts cannot be relative')
    else:
        start, end = parse_partial_date(value)
    return (start, end)


def filter_by_date(waypoints, date_ranges):
    """Filter waypoints matching any of the date ranges (OR logic)."""
    def matches(wp):
        if not wp.time:
            return False
        d = wp.time.date()
        return any((start is None or d >= start) and (end is None or d <= end)
                   for start, end in date_ranges)
    return [wp for wp in waypoints if matches(wp)]


def filter_by_location(waypoints, terms):
    """Filter waypoints matching any of the location terms (OR logic).
    Matches against LvL4, country code, state, or city (case-insensitive substring)."""
    lower_terms = [t.lower() for t in terms]

    def matches(wp):
        addr = wp.get_address()
        if not addr:
            return False
        fields = [
            getattr(addr, 'LvL4', None),
            getattr(addr, 'CountryCode', None),
            getattr(addr, 'State', None),
            getattr(addr, 'City', None),
        ]
        return any(
            f and any(term in f.lower() for term in lower_terms)
            for f in fields
        )
    return [wp for wp in waypoints if matches(wp)]


def filter_by_index(waypoints, index_ranges):
    """Filter waypoints matching any of the index ranges (1-based, OR logic)."""
    def matches(i):
        return any((start is None or i >= start) and (end is None or i <= end)
                   for start, end in index_ranges)
    return [wp for i, wp in enumerate(waypoints, 1) if matches(i)]
