"""Repository-scoped benchmark pause; downloads/offline tests remain available."""
from pathlib import Path


def require_benchmark_enabled(root):
    if (Path(root)/'INFERENCE_PAUSED').exists():
        raise ValueError('Benchmark inference is paused for independent test review. Explicit user resumption is required; see docs/review-request.md.')
