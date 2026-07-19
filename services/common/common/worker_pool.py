"""Shared by ingestion and detection: which per-camera workers to start/stop this poll cycle."""


def diff_camera_sets(streaming_ids: set[str], active_ids: set[str]) -> tuple[set[str], set[str]]:
    to_start = streaming_ids - active_ids
    to_stop = active_ids - streaming_ids
    return to_start, to_stop
