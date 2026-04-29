from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .config import Config
from .errors import DependencyError, MathRenderError


@dataclass
class FormulaAsset:
    key: str
    formula: str
    display: bool
    image: Image.Image

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height


class MathRenderer:
    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self._cache: dict[tuple[str, bool], FormulaAsset] = {}
        if config.math.renderer != "tectonic":
            raise DependencyError("Only math.renderer=tectonic is supported in the MVP")
        if shutil.which("tectonic") is None:
            raise DependencyError("Missing external command: tectonic")

    def render(self, formula: str, display: bool) -> FormulaAsset:
        key = (formula, display)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        asset_key = hashlib.sha1((formula + "|" + str(display)).encode("utf-8")).hexdigest()
        image = self._render_uncached(formula, display)
        asset = FormulaAsset(key=asset_key, formula=formula, display=display, image=image)
        self._cache[key] = asset
        return asset

    def _render_uncached(self, formula: str, display: bool) -> Image.Image:
        try:
            import fitz
        except ModuleNotFoundError as exc:
            raise DependencyError("Missing Python dependency: PyMuPDF (import name: fitz)") from exc

        with tempfile.TemporaryDirectory(prefix="md2handnote_math_") as tmp:
            tmp_path = Path(tmp)
            tex_path = tmp_path / "formula.tex"
            pdf_path = tmp_path / "formula.pdf"
            tex_path.write_text(_latex_document(formula, display), encoding="utf-8")

            cmd = [
                "tectonic",
                "--keep-logs",
                "--outdir",
                str(tmp_path),
                str(tex_path),
            ]
            env = os.environ.copy()
            if "XDG_CACHE_HOME" not in env:
                cache_dir = Path(tempfile.gettempdir()) / "md2handnote-cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                env["XDG_CACHE_HOME"] = str(cache_dir)
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout).strip()
                raise MathRenderError(f"LaTeX compile failed for formula {formula!r}:\n{detail}")
            if not pdf_path.is_file():
                raise MathRenderError(f"LaTeX compile did not produce a PDF for formula {formula!r}")

            doc = fitz.open(str(pdf_path))
            if doc.page_count < 1:
                raise MathRenderError(f"Formula render result is empty: {formula!r}")
            page = doc.load_page(0)
            zoom = self.config.page.dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
            if pix.width <= 0 or pix.height <= 0:
                raise MathRenderError(f"Formula render result is empty: {formula!r}")
            image = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            doc.close()
            return _trim_transparent(image)


def _latex_document(formula: str, display: bool) -> str:
    body = f"\\[{formula}\\]" if display else f"\\({formula}\\)"
    return rf"""
\documentclass[preview,border=1pt]{{standalone}}
\usepackage{{amsmath,amssymb,mathtools,bm}}
\begin{{document}}
{body}
\end{{document}}
""".strip()


def _trim_transparent(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise MathRenderError("Formula render result has no visible pixels")
    padded = (
        max(0, bbox[0] - 4),
        max(0, bbox[1] - 4),
        min(image.width, bbox[2] + 4),
        min(image.height, bbox[3] + 4),
    )
    return image.crop(padded)
