"""Bounding-box types, detection, and within-camera tracking (docs/DECISIONS.md ADR-0004,
ADR-0007).

`run_person_tracking` runs the detector then feeds its output through a per-camera
BYTETracker instance so each returned box carries a `track_id` local to that tracker
(scoped to one camera for the tracker's lifetime, not a database id).
"""

from dataclasses import dataclass

from ultralytics.trackers import BYTETracker
from ultralytics.utils import YAML, IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml

PERSON_CLASS_ID = 0  # COCO class index for "person"


@dataclass(frozen=True)
class DetectedBox:
    x: int
    y: int
    w: int
    h: int
    confidence: float
    track_id: int

    def as_json(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def build_tracker() -> BYTETracker:
    cfg = IterableSimpleNamespace(**YAML.load(check_yaml("bytetrack.yaml")))
    return BYTETracker(cfg)


def run_person_tracking(model, tracker: BYTETracker, frame, min_confidence: float = 0.5) -> list[DetectedBox]:
    results = model(frame, classes=[PERSON_CLASS_ID], verbose=False)
    tracked = tracker.update(results[0].boxes.cpu().numpy(), frame)

    boxes: list[DetectedBox] = []
    for x1, y1, x2, y2, track_id, confidence, _cls, _idx in tracked:
        if confidence < min_confidence:
            continue
        boxes.append(
            DetectedBox(
                x=int(x1),
                y=int(y1),
                w=int(x2 - x1),
                h=int(y2 - y1),
                confidence=float(confidence),
                track_id=int(track_id),
            )
        )
    return boxes
