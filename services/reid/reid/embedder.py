"""Person appearance embeddings via Ultralytics' bundled ReID encoder (docs/DECISIONS.md ADR-0008)."""

import numpy as np
from ultralytics.trackers.utils.reid import ReID

REID_MODEL = "yolo26n-reid.onnx"


def build_encoder() -> ReID:
    return ReID(REID_MODEL)


def embed_crop(encoder: ReID, image: np.ndarray) -> np.ndarray | None:
    h, w = image.shape[:2]
    dets = np.array([[w / 2, h / 2, w, h]], dtype=np.float32)
    return encoder(image, dets)[0]
