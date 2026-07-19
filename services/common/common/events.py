"""Redis pub/sub channel for the real-time sighting feed (docs/DECISIONS.md ADR-0012).
Shared so `reid` (publisher) and `api` (subscriber) agree on the channel name.
"""

SIGHTINGS_CHANNEL = "sightings"
