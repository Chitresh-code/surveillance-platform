from detection.boxes import DetectedBox, run_person_detection


class _FakeTensor:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return list(self._values)

    def __getitem__(self, index):
        return self._values[index]

    def __float__(self):
        return float(self._values[0])


class _FakeBox:
    def __init__(self, xyxy, conf, cls):
        self.xyxy = [_FakeTensor(xyxy)]
        self.conf = [conf]
        self.cls = [cls]


class _FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


def _fake_model(boxes):
    def model(frame, classes=None, verbose=False):
        return [_FakeResult(boxes)]

    return model


def test_run_person_detection_converts_xyxy_to_xywh():
    model = _fake_model([_FakeBox(xyxy=[10.0, 20.0, 30.0, 50.0], conf=0.9, cls=0)])
    boxes = run_person_detection(model, frame=None, min_confidence=0.5)
    assert boxes == [DetectedBox(x=10, y=20, w=20, h=30, confidence=0.9)]


def test_run_person_detection_drops_low_confidence_boxes():
    model = _fake_model([_FakeBox(xyxy=[0.0, 0.0, 10.0, 10.0], conf=0.2, cls=0)])
    boxes = run_person_detection(model, frame=None, min_confidence=0.5)
    assert boxes == []
