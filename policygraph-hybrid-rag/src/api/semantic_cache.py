from __future__ import annotations

import hashlib
import json
import time

import numpy as np
import redis


class SemanticCache:
    """
    Redis-backed semantic cache.

    Stores query embeddings and generated answers.
    A cached result is returned when cosine similarity
    with a previous query is greater than the threshold.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 86400,
    ):
        self.client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds

        self.key_prefix = "policygraph:semantic_cache:"
        self.hits = 0
        self.misses = 0

    # ========================================================
    # Connection
    # ========================================================

    def ping(self) -> bool:
        return bool(self.client.ping())

    # ========================================================
    # Similarity
    # ========================================================

    @staticmethod
    def cosine_similarity(
        embedding_a: list[float],
        embedding_b: list[float],
    ) -> float:

        a = np.asarray(
            embedding_a,
            dtype=np.float32,
        )

        b = np.asarray(
            embedding_b,
            dtype=np.float32,
        )

        denominator = (
            np.linalg.norm(a)
            * np.linalg.norm(b)
        )

        if denominator == 0:
            return 0.0

        return float(
            np.dot(a, b)
            / denominator
        )

    # ========================================================
    # Cache storage
    # ========================================================

    def _make_key(
        self,
        query: str,
    ) -> str:

        query_hash = hashlib.sha256(
            query.encode("utf-8")
        ).hexdigest()

        return (
            f"{self.key_prefix}"
            f"{query_hash}"
        )

    def set(
        self,
        query: str,
        embedding: list[float],
        answer: str,
        metadata: dict | None = None,
    ) -> None:

        key = self._make_key(query)

        payload = {
            "query": query,
            "embedding": embedding,
            "answer": answer,
            "metadata": metadata or {},
            "created_at": time.time(),
        }

        self.client.setex(
            key,
            self.ttl_seconds,
            json.dumps(payload),
        )

    # ========================================================
    # Semantic lookup
    # ========================================================

    def get(
        self,
        embedding: list[float],
    ) -> dict | None:

        keys = self.client.keys(
            f"{self.key_prefix}*"
        )

        best_match = None
        best_similarity = 0.0

        for key in keys:

            raw_value = self.client.get(key)

            if raw_value is None:
                continue

            payload = json.loads(raw_value)

            similarity = self.cosine_similarity(
                embedding,
                payload["embedding"],
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = payload

        if (
            best_match is not None
            and best_similarity
            >= self.similarity_threshold
        ):
            self.hits += 1

            best_match["similarity"] = (
                best_similarity
            )

            return best_match

        self.misses += 1

        return None

    # ========================================================
    # Statistics
    # ========================================================

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:

        if self.total_requests == 0:
            return 0.0

        return (
            self.hits
            / self.total_requests
        )

    def stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
            "similarity_threshold": (
                self.similarity_threshold
            ),
            "ttl_seconds": self.ttl_seconds,
        }