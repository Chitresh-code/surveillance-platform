import numpy as np

from ingestion.capture import build_frame_fields, frame_stream_key


def test_build_frame_fields_encodes_jpeg_and_tags_track():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    fields = build_frame_fields(frame, track_id="trk_123")
    assert fields["track_id"] == "trk_123"
    assert isinstance(fields["jpeg"], bytes)
    assert fields["jpeg"][:2] == b"\xff\xd8"  # JPEG magic bytes
    assert "captured_at" in fields


def test_frame_stream_key_namespaces_by_camera():
    assert frame_stream_key("cam_lobby") == "frames:cam_lobby"
