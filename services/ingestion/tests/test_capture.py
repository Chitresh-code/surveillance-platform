import numpy as np

from ingestion.capture import build_frame_fields, frame_stream_key, resolve_capture_source


def test_build_frame_fields_encodes_jpeg():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    fields = build_frame_fields(frame)
    assert isinstance(fields["jpeg"], bytes)
    assert fields["jpeg"][:2] == b"\xff\xd8"  # JPEG magic bytes
    assert "captured_at" in fields


def test_frame_stream_key_namespaces_by_camera():
    assert frame_stream_key("cam_lobby") == "frames:cam_lobby"


def test_resolve_capture_source_treats_digit_string_as_device_index():
    assert resolve_capture_source("0") == 0


def test_resolve_capture_source_leaves_urls_untouched():
    assert resolve_capture_source("rtsp://camera-host/lobby-north") == "rtsp://camera-host/lobby-north"
