#!/usr/bin/env python3
"""Run sync and show clean results."""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING)

# Clear known_events for fresh novelty detection
from pathlib import Path
ke = Path.home() / ".local/share/fechas-academicas/known_events.json"
if ke.exists():
    ke.unlink()

from backend.fechas_sync import sync
cache = sync(dry_run=False)

moodle = [e for e in cache.events if "Moodle" in e.get("source_name","")]
unrn = [e for e in cache.events if "UNRN" in e.get("source_name","")]

print("=" * 60)
print("  SYNC RESULTS")
print("=" * 60)
print(f"  Total: {len(cache.events)} | Moodle: {len(moodle)} | UNRN: {len(unrn)}")
print(f"  Status: {cache.sync_status}")
if cache.sync_error:
    print(f"  Error: {cache.sync_error}")
print()
print("--- MOODLE ---")
for e in moodle:
    n = " NEW" if e.get("is_new") else ""
    print(f"  [{e['urgency']:>6}] {e['days_remaining']:>3}d{n} | {e['title'][:65]}")
print()
print("--- UNRN ---")
for e in unrn:
    n = " NEW" if e.get("is_new") else ""
    print(f"  [{e['urgency']:>6}] {e['days_remaining']:>3}d{n} | {e['title'][:65]}")
print("=" * 60)
