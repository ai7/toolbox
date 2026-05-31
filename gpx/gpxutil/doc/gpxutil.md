# gpxutil.py readme


# option notes

## -u tz notes

-u tz converts the waypoint's time field from UTC to local time:

1. Determines the timezone from the waypoint's GPS coordinates (using TimezoneFinder)
2. Calls datetime.astimezone() to convert the UTC time to that local timezone
3. Overwrites wps.time with the localized datetime

Example: a waypoint at Vancouver coordinates with time = 2025-04-16
17:11:33+00:00 becomes 2025-04-16 10:11:33-07:00.

Assumes the existing wps.time is a timezone-aware UTC datetime (which is
standard for GPX files).

## -u desctime

-u desctime normalizes the timestamp string in the waypoint's description field:

1. Takes the first line of the description (splits on \n)
2. Tries to parse it against known formats:
  - Jul 20, 2018 6:14 pm (motionX GPS)
  - Jul 20, 2018 18:14
  - 2018-07-20 6:14 pm
   - 06-AUG-18 7:57:56 (Garmin 60csx)
   - 2025-03-06 14:26:54 (standard format)
3. If the parsed time has seconds == 0 but wps.time has non-zero seconds,
   copies the seconds over (preserves precision lost by some apps)
   - only if 'fixsec' suboption is used
4. Reformats to the standard YYYY-MM-DD HH:MM:SS
5. Overwrites the description only if it changed
6. Any extra info after description is kept.

It does not touch wps.time — it only cleans up the text representation stored
in the desc field.
