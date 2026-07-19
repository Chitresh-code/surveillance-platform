"""Cosine-similarity identity matching (docs/DECISIONS.md ADR-0008)."""

import numpy as np
from ultralytics.trackers.utils.reid import smooth_feature


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def best_match(embedding: np.ndarray, identities: list) -> tuple[object | None, float]:
    best, best_score = None, -1.0
    for identity in identities:
        score = cosine_similarity(embedding, np.array(identity.embedding, dtype=np.float32))
        if score > best_score:
            best, best_score = identity, score
    return best, best_score


def update_identity_embedding(identity, embedding: np.ndarray, alpha: float = 0.7) -> None:
    _, smoothed = smooth_feature(embedding, np.array(identity.embedding, dtype=np.float32), alpha)
    identity.embedding = smoothed.tolist()
