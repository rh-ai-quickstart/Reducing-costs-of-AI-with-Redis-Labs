"""Tests for the UI guide tab."""

from __future__ import annotations

from pathlib import Path

from ui.tabs import guide


def test_guide_markdown_path_exists():
    guide_path = Path(guide._REPO_ROOT) / "docs" / "embeded_guide.md"
    assert guide_path.is_file()


def test_embed_local_images_rewrites_docs_relative_paths():
    docs_dir = Path(guide._DOCS_DIR)
    markdown = "![demo](images/infra-verification.png)"
    rendered = guide._embed_local_images(markdown, docs_dir=docs_dir)
    assert rendered.startswith("![demo](data:image/png;base64,")
