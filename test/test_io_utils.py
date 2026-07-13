"""Unit tests for the shared filesystem/image I/O helpers."""

import os
import sys

import numpy as np
from PIL import Image

# Make the repository root importable regardless of how pytest is invoked.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.io_utils import ensure_dir, write_text, save_image  # noqa: E402


def test_ensure_dir_creates_nested_directories(tmp_path):
    target = os.path.join(str(tmp_path), "a", "b", "c")
    returned = ensure_dir(target)
    assert returned == target
    assert os.path.isdir(target)
    # idempotent
    ensure_dir(target)
    assert os.path.isdir(target)


def test_ensure_dir_tolerates_empty_path():
    assert ensure_dir("") == ""


def test_write_text_creates_parent_and_writes(tmp_path):
    path = os.path.join(str(tmp_path), "sub", "file.txt")
    returned = write_text(path, "hello world")
    assert returned == path
    with open(path, encoding="utf-8") as f:
        assert f.read() == "hello world"


def test_write_text_append_mode(tmp_path):
    path = os.path.join(str(tmp_path), "log.txt")
    write_text(path, "one\n")
    write_text(path, "two\n", mode="a")
    with open(path, encoding="utf-8") as f:
        assert f.read() == "one\ntwo\n"


def test_write_text_bom_encoding(tmp_path):
    path = os.path.join(str(tmp_path), "bom.yml")
    write_text(path, "l_english:", encoding="utf-8-sig")
    with open(path, "rb") as f:
        assert f.read().startswith(b"\xef\xbb\xbf")


def test_save_image_infers_and_forces_mode(tmp_path):
    rgb = (np.random.rand(6, 6, 3) * 255).astype(np.uint8)
    rgb_path = save_image(rgb, os.path.join(str(tmp_path), "imgs", "rgb.bmp"), "RGB")
    assert os.path.getsize(rgb_path) > 0
    assert Image.open(rgb_path).size == (6, 6)

    gray = (np.random.rand(6, 6) * 255).astype(np.uint8)
    gray_path = save_image(gray, os.path.join(str(tmp_path), "gray.bmp"))
    assert os.path.getsize(gray_path) > 0
