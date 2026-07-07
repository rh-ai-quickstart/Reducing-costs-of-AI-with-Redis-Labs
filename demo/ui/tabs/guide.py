"""Tab 0 — Streamlit UI guide (repository markdown)."""

from __future__ import annotations

import base64
import re
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_DIR = _REPO_ROOT / "docs"
_GUIDE_PATH = _DOCS_DIR / "embeded_guide.md"
_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _embed_local_images(markdown: str, *, docs_dir: Path) -> str:
    """Rewrite docs-relative image links so Streamlit can render them inline."""

    def _replace(match: re.Match[str]) -> str:
        alt, raw_path = match.group(1), match.group(2).strip()
        if raw_path.startswith(("http://", "https://", "data:")):
            return match.group(0)
        image_path = (docs_dir / raw_path.removeprefix("./")).resolve()
        if not image_path.is_file():
            return match.group(0)
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        suffix = image_path.suffix.lower().lstrip(".")
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix or "png"
        return f"![{alt}](data:image/{mime};base64,{encoded})"

    return _IMAGE_PATTERN.sub(_replace, markdown)


def render() -> None:
    if not _GUIDE_PATH.is_file():
        st.error(f"Guide not found: `{_GUIDE_PATH}`")
        return

    markdown = _GUIDE_PATH.read_text(encoding="utf-8")
    st.markdown(_embed_local_images(markdown, docs_dir=_DOCS_DIR))
