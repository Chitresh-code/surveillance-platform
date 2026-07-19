"""Bounding-box types and person-detection inference (docs/DECISIONS.md ADR-0004: YOLOv8n).

Phase 1 scope is detection only, one Detection row per person per frame. Associating
detections into tracks across frames is Phase 2 (docs/PRD.md §10) so there is no
tracker here, only the per-frame detector.
"""

from dataclasses import dataclass

PERSON_CLASS_ID = 0  # COCO class index for "person"


@dataclass(frozen=True)
class DetectedBox:
    x: int
    y: int
    w: int
    h: int
    confidence: float

    def as_json(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def run_person_detection(model, frame, min_confidence: float = 0.5) -> list[DetectedBox]:
    results = model(frame, classes=[PERSON_CLASS_ID], verbose=False)
    boxes: list[DetectedBox] = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf[0])
            if confidence < min_confidence:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            boxes.append(
                DetectedBox(x=int(x1), y=int(y1), w=int(x2 - x1), h=int(y2 - y1), confidence=confidence)
            )
    return boxes
