from types import SimpleNamespace

import numpy as np
import pytest

from reid.matcher import best_match, cosine_similarity, update_identity_embedding


def test_cosine_similarity_of_identical_vectors_is_one():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_of_orthogonal_vectors_is_zero():
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_best_match_picks_the_closest_identity():
    close = SimpleNamespace(embedding=[1.0, 0.0])
    far = SimpleNamespace(embedding=[0.0, 1.0])
    identity, score = best_match(np.array([0.9, 0.1]), [far, close])
    assert identity is close
    assert score > 0.9


def test_best_match_with_no_identities_returns_none():
    identity, score = best_match(np.array([1.0, 0.0]), [])
    assert identity is None
    assert score == -1.0


def test_update_identity_embedding_blends_toward_the_new_feature():
    identity = SimpleNamespace(embedding=[1.0, 0.0])
    update_identity_embedding(identity, np.array([0.0, 1.0]), alpha=0.5)
    assert identity.embedding != [1.0, 0.0]
    assert cosine_similarity(np.array(identity.embedding), np.array([0.0, 1.0])) > 0
