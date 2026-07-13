"""
Shared filesystem / image I/O helpers
======================================
These small utilities collapse patterns that were duplicated dozens of times
across the export, content, engine and analytics packages:

* ``os.makedirs(path, exist_ok=True)``            -> :func:`ensure_dir`
* ``with open(path, "w", encoding="utf-8") ...``  -> :func:`write_text`
* ``Image.fromarray(arr[, mode]).save(path)``     -> :func:`save_image`

Keeping them in one place means the encoding, directory-creation and image
mode conventions only have to be maintained once.
"""

from __future__ import annotations

import os
from typing import Optional


def ensure_dir(path: str) -> str:
    """Create ``path`` (and parents) if needed and return it.

    Mirrors ``os.makedirs(path, exist_ok=True)`` but is safe to call with an
    empty string (e.g. the directory part of a bare filename).
    """
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def write_text(path: str, content: str, *, mode: str = "w",
               encoding: str = "utf-8") -> str:
    """Write ``content`` to ``path`` and return the path.

    Creates the parent directory if it does not already exist so callers do
    not have to repeat the ``makedirs`` dance before every write.
    """
    ensure_dir(os.path.dirname(path))
    with open(path, mode, encoding=encoding) as f:
        f.write(content)
    return path


def save_image(array, path: str, mode: Optional[str] = None) -> str:
    """Save a numpy array as an image via Pillow and return the path.

    ``mode`` is forwarded to :func:`PIL.Image.fromarray` (e.g. ``"RGB"`` or
    ``"RGBA"``); when ``None`` Pillow infers it from the array shape/dtype.
    """
    from PIL import Image  # local import keeps Pillow optional for text-only callers

    ensure_dir(os.path.dirname(path))
    if mode is None:
        Image.fromarray(array).save(path)
    else:
        Image.fromarray(array, mode).save(path)
    return path
