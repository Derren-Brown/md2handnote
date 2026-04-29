from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image, ImageDraw

from .config import Config
from .fonts import FontManager, is_latin_text
from .handwriting import PUNCTUATION
from .math_renderer import FormulaAsset
from .parser import Token
from .utils import a4_px, mm_to_px


@dataclass
class TextElement:
    text: str
    x: int
    y: int
    size: int


@dataclass
class FormulaElement:
    asset: FormulaAsset
    x: int
    y: int
    line_y: int
    width: int
    height: int
    scale: float
    display: bool


@dataclass
class PageLayout:
    elements: list[TextElement | FormulaElement] = field(default_factory=list)


@dataclass
class LayoutResult:
    pages: list[PageLayout]
    warnings: list[str]


MeasureFunc = Callable[[str, int], int]


class LayoutEngine:
    def __init__(self, config: Config, font_manager: FontManager):
        self.config = config
        self.font_manager = font_manager
        self.page_width, self.page_height = a4_px(config.page.dpi)
        self.margin_left = mm_to_px(config.page.margin_left_mm, config.page.dpi)
        self.margin_right = mm_to_px(config.page.margin_right_mm, config.page.dpi)
        self.margin_top = mm_to_px(config.page.margin_top_mm, config.page.dpi)
        self.margin_bottom = mm_to_px(config.page.margin_bottom_mm, config.page.dpi)
        self.line_height = mm_to_px(config.page.line_spacing_mm, config.page.dpi)
        self.max_x = self.page_width - self.margin_right
        self.max_y = self.page_height - self.margin_bottom
        self.writable_width = self.max_x - self.margin_left
        self._measure_canvas = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def layout(
        self,
        tokens: list[Token],
        math_assets: dict[tuple[str, bool], FormulaAsset],
    ) -> LayoutResult:
        warnings: list[str] = []
        pages = [PageLayout()]
        x = self.margin_left
        y = self.margin_top

        def current_page() -> PageLayout:
            return pages[-1]

        def new_page() -> None:
            pages.append(PageLayout())

        def ensure_vertical(required_height: int) -> None:
            nonlocal x, y
            if y + required_height <= self.max_y:
                return
            new_page()
            x = self.margin_left
            y = self.margin_top

        def new_line(multiplier: int = 1) -> None:
            nonlocal x, y
            x = self.margin_left
            y += self.line_height * multiplier
            ensure_vertical(self.line_height)

        skip_next_line_break = False
        for token in tokens:
            if token.kind == "blank_line":
                if x != self.margin_left:
                    new_line()
                continue
            if token.kind == "line_break":
                if skip_next_line_break:
                    skip_next_line_break = False
                    continue
                new_line()
                continue
            if token.kind == "text":
                for unit in split_text_units(token.value):
                    if not unit:
                        continue
                    if unit.isspace() and x == self.margin_left:
                        continue
                    size = self._font_size_for(unit)
                    width = self.measure(unit, size)
                    extra_spacing = self._extra_spacing(unit)
                    if x + width > self.max_x and x > self.margin_left:
                        new_line()
                        if unit.isspace():
                            continue
                    if width > self.writable_width and len(unit) > 1:
                        for char in unit:
                            size = self._font_size_for(char)
                            width = self.measure(char, size)
                            if x + width > self.max_x and x > self.margin_left:
                                new_line()
                            ensure_vertical(self.line_height)
                            current_page().elements.append(TextElement(char, x, y, size))
                            x += width
                        continue
                    ensure_vertical(self.line_height)
                    current_page().elements.append(TextElement(unit, x, y, size))
                    x += width + extra_spacing
                continue
            if token.kind == "inline_math":
                asset = math_assets[(token.value, False)]
                scale = self.config.math.base_scale * self.config.math.inline_scale
                width, height, scale = self._scaled_formula_size(asset, scale)
                side_gap = mm_to_px(1.2, self.config.page.dpi)
                formula_x = x + (side_gap if x > self.margin_left else 0)
                if formula_x + width > self.max_x and x > self.margin_left:
                    new_line()
                    formula_x = x
                if width > self.writable_width:
                    min_scale = self.config.math.min_scale
                    width, height, scale = self._scaled_formula_size(asset, min_scale)
                    if width > self.writable_width:
                        warnings.append(
                            f"Line {token.line}: inline formula remains wider than text area after shrink"
                        )
                ensure_vertical(max(self.line_height, height))
                baseline = y + self._baseline_offset()
                top = baseline - int(round(height * 0.68))
                current_page().elements.append(
                    FormulaElement(asset, formula_x, top, y, width, height, scale, display=False)
                )
                x = formula_x + width + side_gap
                continue
            if token.kind == "block_math":
                if x != self.margin_left:
                    new_line()
                asset = math_assets[(token.value, True)]
                width, height, scale = self._scaled_formula_size(
                    asset, self.config.math.base_scale * self.config.math.block_scale
                )
                if width > self.writable_width:
                    shrink = max(self.config.math.min_scale, self.writable_width / asset.width)
                    width, height, scale = self._scaled_formula_size(asset, shrink)
                    warnings.append(f"Line {token.line}: block formula was shrunk to fit")
                if width > self.writable_width:
                    warnings.append(
                        f"Line {token.line}: block formula still exceeds text width after shrink"
                    )
                ensure_vertical(height + self.line_height)
                formula_x = self.margin_left + max(0, (self.writable_width - width) // 2)
                current_page().elements.append(
                    FormulaElement(asset, formula_x, y, y, width, height, scale, display=True)
                )
                lines_used = max(1, math.ceil((height + self.line_height * 0.6) / self.line_height))
                new_line(lines_used)
                skip_next_line_break = True
                continue

        return LayoutResult(pages=pages, warnings=warnings)

    def measure(self, text: str, size: int) -> int:
        font = self.font_manager.font_for_text(text, size)
        bbox = self._measure_canvas.textbbox((0, 0), text, font=font)
        return max(1, bbox[2] - bbox[0])

    def _font_size_for(self, text: str) -> int:
        if is_latin_text(text):
            return self.config.text.english_font_size_px
        return self.config.text.chinese_font_size_px

    def _extra_spacing(self, text: str) -> int:
        if text.isspace():
            return 0
        if is_latin_text(text) and re.search(r"[A-Za-z0-9]$", text):
            return int(round(self.config.jitter.word_spacing_px))
        return 0

    def _baseline_offset(self) -> int:
        return 0

    @staticmethod
    def _scaled_formula_size(asset: FormulaAsset, scale: float) -> tuple[int, int, float]:
        width = max(1, int(round(asset.width * scale)))
        height = max(1, int(round(asset.height * scale)))
        return width, height, scale


def split_text_units(text: str) -> list[str]:
    units: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace():
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            units.append(text[i:j])
            i = j
            continue
        if _is_ascii_word_char(char):
            j = i + 1
            while j < len(text) and _is_ascii_word_char(text[j]):
                j += 1
            units.append(text[i:j])
            i = j
            continue
        if char in PUNCTUATION:
            units.append(char)
            i += 1
            continue
        if ord(char) >= 128:
            j = i + 1
            while (
                j < len(text)
                and not text[j].isspace()
                and not _is_ascii_word_char(text[j])
                and text[j] not in PUNCTUATION
            ):
                j += 1
            run = text[i:j]
            units.extend(run[start : start + 2] for start in range(0, len(run), 2))
            i = j
            continue
        units.append(char)
        i += 1
    return units


def _is_ascii_word_char(char: str) -> bool:
    return bool(re.match(r"[A-Za-z0-9_./:+-]", char))
