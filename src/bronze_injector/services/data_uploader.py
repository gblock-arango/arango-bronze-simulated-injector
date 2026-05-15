"""Per-dataset parsers that turn staged volume files into bronze row payloads (playback chunks).

Each dataset should register a real implementation later. The default **stub** yields no rows and
reports ``exhausted`` immediately so PLAY stops cleanly until a dataset-specific uploader exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybackChunk:
    """One playback tick: opaque cursor hand-off + normalized bronze row dicts."""

    next_marker: str | None
    rows: list[dict[str, Any]]
    exhausted: bool


UploaderFn = Callable[..., PlaybackChunk]


def _stub_chunk(
    *,
    dataset_key: str,
    volume_base_path: str,
    marker_json: str | None,
    **_kwargs: Any,
) -> PlaybackChunk:
    logger.debug(
        "data_uploader stub: dataset=%s volume=%s marker=%s",
        dataset_key,
        volume_base_path,
        marker_json,
    )
    return PlaybackChunk(next_marker=None, rows=[], exhausted=True)


_UPLOADER_REGISTRY: dict[str, UploaderFn] = {}


def register_dataset_uploader(dataset_key: str, fn: UploaderFn) -> None:
    """Register the chunk producer for a normalized ``dataset_key`` (lowercase, underscores)."""
    _UPLOADER_REGISTRY[dataset_key.strip().lower()] = fn


def next_playback_chunk(
    *,
    dataset_key: str,
    volume_base_path: str,
    marker_json: str | None,
    batch_hint: int | None = None,
) -> PlaybackChunk:
    """Return the next chunk for playback; ``marker_json`` is opaque state from UC playback table."""
    key = (dataset_key or "").strip().lower().replace("-", "_")
    fn = _UPLOADER_REGISTRY.get(key, _stub_chunk)
    return fn(
        dataset_key=key,
        volume_base_path=volume_base_path,
        marker_json=marker_json,
        batch_hint=batch_hint,
    )


register_dataset_uploader("elliptic_bitcoin", _stub_chunk)
register_dataset_uploader("elliptic", _stub_chunk)
