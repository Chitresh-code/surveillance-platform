import os

import numpy as np

from detection.boxes import DetectedBox
from detection.storage import crop_path, save_crop


def test_crop_path_uses_detection_id():
    assert crop_path("/data/frames", "det_abc") == "/data/frames/det_abc.jpg"


def test_save_crop_writes_a_file_sized_to_the_box(tmp_path):
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    box = DetectedBox(x=10, y=10, w=20, h=30, confidence=0.9)
    path = str(tmp_path / "det_abc.jpg")

    save_crop(frame, box, path)

    assert os.path.exists(path)
