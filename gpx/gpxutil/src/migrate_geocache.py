#!/usr/bin/env python3
"""
One-time migration: rewrite geocoding cache keys to 4 decimal places.

Usage:
    python migrate_geocache.py [--dry-run]
"""

import json
import os
import sys
import shutil
from datetime import datetime


CACHE_PATH = os.path.join(os.path.expanduser('~'), '.cache', 'gpxutil', 'geocoding_cache.json')


def round_key(key: str) -> str:
    lat_s, lon_s = key.split(',')
    return f"{round(float(lat_s), 4)},{round(float(lon_s), 4)}"


def migrate(dry_run: bool = False):
    if not os.path.exists(CACHE_PATH):
        print(f"Cache file not found: {CACHE_PATH}")
        sys.exit(1)

    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', {})
    before = len(entries)

    # Build new entries: on collision keep the most recently cached entry
    new_entries = {}
    collisions = 0
    for full_key, value in entries.items():
        new_key = round_key(full_key)
        if new_key in new_entries:
            collisions += 1
            existing_at = new_entries[new_key].get('cached_at', '')
            this_at = value.get('cached_at', '')
            if this_at > existing_at:
                new_entries[new_key] = value
        else:
            new_entries[new_key] = value

    after = len(new_entries)
    print(f"Entries before: {before}")
    print(f"Entries after:  {after}")
    print(f"Collisions (duplicates dropped): {collisions}")

    if dry_run:
        print("Dry run — no changes written.")
        return

    # Back up original
    backup_path = CACHE_PATH + f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(CACHE_PATH, backup_path)
    print(f"Backup saved to: {backup_path}")

    data['entries'] = new_entries
    data['metadata']['total_entries'] = after
    data['metadata']['last_updated'] = datetime.now().isoformat()

    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Cache updated: {CACHE_PATH}")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    migrate(dry_run=dry_run)
