from __future__ import annotations

from pathlib import Path


A4_MM = (210.0, 297.0)


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm / 25.4 * dpi))


def mm_to_pt(mm: float) -> float:
    return mm / 25.4 * 72.0


def a4_px(dpi: int) -> tuple[int, int]:
    return mm_to_px(A4_MM[0], dpi), mm_to_px(A4_MM[1], dpi)


def a4_pt() -> tuple[float, float]:
    return mm_to_pt(A4_MM[0]), mm_to_pt(A4_MM[1])


def resolve_relative(path_value: str | None, base_dir: Path) -> str | None:
    if not path_value:
        return path_value
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())
