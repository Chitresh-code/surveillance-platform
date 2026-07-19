"""Frame crop storage (docs/DECISIONS.md ADR-0006: local filesystem volume for Phase 1)."""

import os

import cv2

from detection.boxes import DetectedBox


def crop_path(frame_store_dir: str, detection_id: str) -> str:
    return os.path.join(frame_store_dir, f"{detection_id}.jpg")


def save_crop(frame, box: DetectedBox, path: str) -> None:
    crop = frame[box.y : box.y + box.h, box.x : box.x + box.w]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, crop)
