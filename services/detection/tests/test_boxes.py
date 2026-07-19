import numpy as np
import pytest

from detection.boxes import DetectedBox, run_person_tracking


class _FakeBoxes:
    def cpu(self):
        return self

    def numpy(self):
        return self


class _FakeResult:
    def __init__(self):
        self.boxes = _FakeBoxes()


class _FakeTracker:
    def __init__(self, rows):
        self._rows = rows

    def update(self, boxes, frame):
        return np.array(self._rows, dtype=np.float32)


def _fake_model():
    def model(frame, classes=None, verbose=False):
        return [_FakeResult()]

    return model


def test_run_person_tracking_converts_xyxy_to_xywh_with_track_id():
    tracker = _FakeTracker([[10.0, 20.0, 30.0, 50.0, 3.0, 0.9, 0.0, 0.0]])
    boxes = run_person_tracking(_fake_model(), tracker, frame=None, min_confidence=0.5)
    assert len(boxes) == 1
    assert boxes[0].confidence == pytest.approx(0.9)
    assert boxes[0] == DetectedBox(x=10, y=20, w=20, h=30, confidence=boxes[0].confidence, track_id=3)


def test_run_person_tracking_drops_low_confidence_boxes():
    tracker = _FakeTracker([[0.0, 0.0, 10.0, 10.0, 1.0, 0.2, 0.0, 0.0]])
    boxes = run_person_tracking(_fake_model(), tracker, frame=None, min_confidence=0.5)
    assert boxes == []


def test_run_person_tracking_handles_no_detections():
    tracker = _FakeTracker([])
    boxes = run_person_tracking(_fake_model(), tracker, frame=None, min_confidence=0.5)
    assert boxes == []
