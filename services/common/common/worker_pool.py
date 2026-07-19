"""Generic id-set diffing: what to start/open vs. stop/close this cycle.

Used by ingestion and detection to reconcile per-camera worker pools against
the streaming camera list, and by the detection worker to reconcile per-camera
tracker output against currently open tracks.
"""


def diff_ids(target_ids: set[str], current_ids: set[str]) -> tuple[set[str], set[str]]:
    to_add = target_ids - current_ids
    to_remove = current_ids - target_ids
    return to_add, to_remove
