# FIT File Technical Reference

Technical notes on Garmin FIT file format internals relevant to fitutil.py.

## Coordinate Storage

FIT stores latitude and longitude as **semicircles** — signed 32-bit integers.

Conversion to degrees:
```
degrees = semicircles × (180 / 2³¹)
```

Resolution: `180 / 2³¹ ≈ 0.0000000838°`, which is approximately **0.009 meters** (~1 cm) at the equator.

GPX stores coordinates as decimal degrees in XML text. No precision is lost in conversion
since the semicircle resolution exceeds what GPS hardware can measure.

## Elevation Storage

FIT stores altitude as an unsigned integer with:
- **Scale:** 5
- **Offset:** 500

```
raw_integer = (altitude_meters + 500) × 5
altitude_meters = (raw_integer / 5) - 500
```

This gives **0.2 meter resolution**. The SDK returns floating point values, which can
introduce noise (e.g., `46.200000000000045` instead of `46.2`). fitutil rounds to 1
decimal place in GPX output to eliminate this while preserving full native precision.

Two fields exist:
- `altitude` — 16-bit, range -500m to 12606.6m
- `enhanced_altitude` — 32-bit, same 0.2m resolution but wider range

## Timestamps

All timestamps in FIT are stored in UTC. Available timestamp fields:

| Message | Field | Description |
|---------|-------|-------------|
| `file_id` | `time_created` | When recording was started (UTC) |
| `session` | `start_time` | Session start (UTC) |
| `session` | `timestamp` | Session end (UTC) |
| `session` | `total_elapsed_time` | Total wall clock duration (seconds) |
| `session` | `total_timer_time` | Moving/active duration (seconds) |
| `record` | `timestamp` | Per-trackpoint timestamp (UTC) |
| `activity` | `timestamp` | Activity end time (UTC) |
| `activity` | `local_timestamp` | End time in device's local timezone (Garmin epoch integer) |

The `local_timestamp` is a raw integer (seconds since Garmin epoch 1989-12-31 00:00:00 UTC)
representing what the device clock showed locally. The UTC offset can be derived:
```
offset = local_timestamp - timestamp (both in Garmin epoch seconds)
```

However, this reflects the device's timezone setting, which may be wrong. GPS-based timezone
lookup (via TimezoneFinder from coordinates) is more reliable for determining local time.

### Garmin Epoch

Garmin uses its own epoch: **1989-12-31 00:00:00 UTC** (631065600 seconds before Unix epoch).
The SDK automatically converts to Python datetime objects with UTC timezone, so consumer code
does not need to handle the epoch difference.

## FIT vs GPX Model Differences

| Aspect | FIT | GPX |
|--------|-----|-----|
| Format | Binary, message-based | XML text |
| Coordinates | Semicircles (int32) | Decimal degrees (text) |
| Elevation | Integer with scale/offset (0.2m steps) | Decimal meters (text) |
| Timestamps | Garmin epoch seconds (UTC) | ISO 8601 strings (UTC) |
| Structure | Flat messages (session, record, lap, device_info) | Hierarchical (trk > trkseg > trkpt) |
| Metadata | Spread across message types (device_info, session, file_id) | Single `<metadata>` element |
| Activity data | Native (sport, calories, HR, cadence, power) | Requires extensions |
| Multi-session | Multiple session/lap messages in one file | Typically separate files |

## Device Info

Device identity comes from `device_info` messages:
- `manufacturer` — string (e.g., "garmin")
- `garmin_product` — integer product ID (e.g., 4202 = eTrex Solar 2)
- `serial_number` — device serial
- `software_version` — firmware version

The product ID requires a lookup table to map to a human-readable name.
Garmin does not publish a complete public mapping; IDs are collected empirically.

## Session Summary Fields

The `session` message contains pre-computed summary statistics:
- `total_distance` — cumulative distance in meters
- `total_ascent` / `total_descent` — elevation gain/loss in meters (integer)
- `enhanced_avg_speed` / `enhanced_max_speed` — meters/second
- `sport` / `sub_sport` — activity type classification (see Sport Types below)
- `start_position_lat` / `start_position_long` — first fix (semicircles)
- `nec_lat`, `nec_long`, `swc_lat`, `swc_long` — bounding box (semicircles)

## Sport Types

Valid `sport` values from the Garmin FIT SDK Profile (`garmin_fit_sdk.Profile['types']['sport']`):

| ID | Sport |
|----|-------|
| 0 | generic |
| 1 | running |
| 2 | cycling |
| 3 | transition |
| 4 | fitness_equipment |
| 5 | swimming |
| 6 | basketball |
| 7 | soccer |
| 8 | tennis |
| 9 | american_football |
| 10 | training |
| 11 | walking |
| 12 | cross_country_skiing |
| 13 | alpine_skiing |
| 14 | snowboarding |
| 15 | rowing |
| 16 | mountaineering |
| 17 | hiking |
| 18 | multisport |
| 19 | paddling |
| 20 | flying |
| 21 | e_biking |
| 22 | motorcycling |
| 23 | boating |
| 24 | driving |
| 25 | golf |
| 26 | hang_gliding |
| 27 | horseback_riding |
| 28 | hunting |
| 29 | fishing |
| 30 | inline_skating |
| 31 | rock_climbing |
| 32 | sailing |
| 33 | ice_skating |
| 34 | sky_diving |
| 35 | snowshoeing |
| 36 | snowmobiling |
| 37 | stand_up_paddleboarding |
| 38 | surfing |
| 39 | wakeboarding |
| 40 | water_skiing |
| 41 | kayaking |
| 42 | rafting |
| 43 | windsurfing |
| 44 | kitesurfing |
| 45 | tactical |
| 47 | boxing |
| 48 | floor_climbing |
| 49 | baseball |
| 53 | diving |
| 56 | shooting |
| 58 | winter_sport |
| 62 | hiit |
| 67 | meditation |
| 69 | disc_golf |
| 76 | water_tubing |
| 77 | wakesurfing |
| 80 | mixed_martial_arts |
| 82 | snorkeling |
| 83 | dance |
| 84 | jump_rope |
| 87 | geocaching |
| 88 | canoeing |
| 254 | all |

Common types for GPS tracklogs: `hiking`, `walking`, `cycling`, `driving`, `running`,
`flying`, `mountaineering`, `boating`, `motorcycling`, `e_biking`.

The `sub_sport` field provides further classification (e.g., `trail` under hiking,
`road` under cycling) but is often set to `generic`.
