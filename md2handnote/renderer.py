from __future__ import annotations

import random

from PIL import Image, ImageDraw

from .config import Config
from .fonts import FontManager
from .handwriting import HandwritingRenderer
from .layout import FormulaElement, LayoutResult, TextElement
from .utils import a4_px, mm_to_px


PAPER_COLOR = (250, 248, 240)
LINE_COLOR = (214, 209, 196)


class PageRenderer:
    def __init__(self, config: Config, font_manager: FontManager, rng: random.Random):
        self.config = config
        self.font_manager = font_manager
        self.rng = rng
        self.handwriting = HandwritingRenderer(config, font_manager, rng)
        self.width, self.height = a4_px(config.page.dpi)

    def render(self, layout: LayoutResult) -> list[Image.Image]:
        return [self._render_page(page.elements) for page in layout.pages]

    def _render_page(self, elements: list[TextElement | FormulaElement]) -> Image.Image:
        page = Image.new("RGBA", (self.width, self.height), PAPER_COLOR + (255,))
        self._draw_lined_paper(page)
        line_offsets: dict[int, float] = {}
        line_x_offsets: dict[int, float] = {}
        for element in elements:
            line_y = element.y if isinstance(element, TextElement) else element.line_y
            line_offsets.setdefault(
                line_y,
                self.rng.uniform(-self.config.jitter.line_y_px, self.config.jitter.line_y_px),
            )
            line_x_offsets.setdefault(
                line_y,
                self.rng.uniform(-self.config.jitter.char_x_px * 1.25, self.config.jitter.char_x_px * 1.25),
            )
        for element in elements:
            if isinstance(element, TextElement):
                line_jitter = line_offsets[element.y]
                line_x = line_x_offsets[element.y]
                self.handwriting.draw_text(
                    page,
                    element.text,
                    int(round(element.x + line_x)),
                    int(round(element.y + line_jitter)),
                    element.size,
                )
            else:
                self._draw_formula(page, element, line_offsets[element.line_y], line_x_offsets[element.line_y])

        angle = self.rng.uniform(
            -self.config.jitter.page_rotation_deg, self.config.jitter.page_rotation_deg
        )
        page = page.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=PAPER_COLOR + (255,),
        )
        return page.convert("RGB")

    def _draw_lined_paper(self, page: Image.Image) -> None:
        if not self.config.page.show_lined_paper:
            return
        draw = ImageDraw.Draw(page)
        spacing = mm_to_px(self.config.page.line_spacing_mm, self.config.page.dpi)
        y = mm_to_px(self.config.page.margin_top_mm, self.config.page.dpi)
        while y < self.height - mm_to_px(self.config.page.margin_bottom_mm, self.config.page.dpi):
            draw.line((0, y, self.width, y), fill=LINE_COLOR + (255,), width=1)
            y += spacing

    def _draw_formula(
        self, page: Image.Image, element: FormulaElement, line_jitter: float, line_x: float
    ) -> None:
        image = element.asset.image.resize(
            (element.width, element.height), Image.Resampling.BICUBIC
        )
        image = self.handwriting.perturb_formula(image)
        dx = self.rng.uniform(-self.config.jitter.char_x_px, self.config.jitter.char_x_px)
        dy = line_jitter + self.rng.uniform(
            -self.config.jitter.formula_y_px * 0.25,
            self.config.jitter.formula_y_px * 0.25,
        )
        page.alpha_composite(image, (int(round(element.x + line_x + dx)), int(round(element.y + dy))))
