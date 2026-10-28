"""Dependency-free JSON logging, Prometheus-style metrics and a sliding-window rate limiter."""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name,
             "msg": record.getMessage()}
        d.update(getattr(record, "extra_fields", {}))
        return json.dumps(d)


def setup_logging(level: int = logging.INFO) -> None:
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level)


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = defaultdict(float)
        self.hist: dict[tuple, list] = {}

    def inc(self, name: str, **labels) -> None:
        with self._lock:
            self.counters[(name, tuple(sorted(labels.items())))] += 1

    def observe(self, name: str, seconds: float, **labels) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            h = self.hist.setdefault(key, [[0] * len(BUCKETS), 0, 0.0])
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    h[0][i] += 1
            h[1] += 1
            h[2] += seconds

    @staticmethod
    def _fmt(labels: tuple, extra: str = "") -> str:
        parts = [f'{k}="{v}"' for k, v in labels] + ([extra] if extra else [])
        return "{" + ",".join(parts) + "}" if parts else ""

    def render(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lines.append(f"{name}{self._fmt(labels)} {v}")
            for (name, labels), (counts, n, total) in sorted(self.hist.items()):
                for b, c in zip(BUCKETS, counts, strict=True):
                    le = 'le="%s"' % b
                    lines.append(f"{name}_bucket{self._fmt(labels, le)} {c}")
                le_inf = 'le="+Inf"'
                lines.append(f"{name}_bucket{self._fmt(labels, le_inf)} {n}")
                lines.append(f"{name}_sum{self._fmt(labels)} {total}")
                lines.append(f"{name}_count{self._fmt(labels)} {n}")
        return "\n".join(lines) + "\n"


class RateLimiter:
    def __init__(self, max_per_min: int, now=time.monotonic):
        self.max, self.now = max_per_min, now
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        t = self.now()
        with self._lock:
            q = self._hits[key]
            while q and t - q[0] >= 60:
                q.popleft()
            if len(q) >= self.max:
                return False
            q.append(t)
            return True
