from __future__ import annotations

from pathlib import Path

from PIL import Image

from .errors import ConfigError, DependencyError
from .utils import a4_pt


def write_pdf(pages: list[Image.Image], output_path: str) -> None:
    if not pages:
        raise ConfigError("No pages were generated")

    path = Path(output_path)
    parent = path.parent if path.parent != Path("") else Path(".")
    if not parent.exists():
        raise ConfigError(f"Output directory does not exist: {parent}")
    if parent.is_dir() is False:
        raise ConfigError(f"Output parent is not a directory: {parent}")

    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError as exc:
        raise DependencyError("Missing Python dependency: reportlab") from exc

    width_pt, height_pt = a4_pt()
    pdf = canvas.Canvas(str(path), pagesize=(width_pt, height_pt))
    for page in pages:
        pdf.drawImage(ImageReader(page), 0, 0, width=width_pt, height=height_pt)
        pdf.showPage()
    pdf.save()
