from common.worker_pool import diff_ids


def test_diff_ids_finds_new_and_removed():
    to_add, to_remove = diff_ids(target_ids={"cam_a", "cam_b"}, current_ids={"cam_b", "cam_c"})
    assert to_add == {"cam_a"}
    assert to_remove == {"cam_c"}


def test_diff_ids_no_change():
    to_add, to_remove = diff_ids(target_ids={"cam_a"}, current_ids={"cam_a"})
    assert to_add == set()
    assert to_remove == set()
