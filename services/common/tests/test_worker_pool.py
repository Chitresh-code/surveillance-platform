from common.worker_pool import diff_camera_sets


def test_diff_camera_sets_finds_new_and_removed_cameras():
    to_start, to_stop = diff_camera_sets(streaming_ids={"cam_a", "cam_b"}, active_ids={"cam_b", "cam_c"})
    assert to_start == {"cam_a"}
    assert to_stop == {"cam_c"}


def test_diff_camera_sets_no_change():
    to_start, to_stop = diff_camera_sets(streaming_ids={"cam_a"}, active_ids={"cam_a"})
    assert to_start == set()
    assert to_stop == set()
