from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFilter

from .config import Config
from .fonts import FontManager, is_latin_text


INK_RGB = (30, 31, 30)
INK_ALPHA = 222
PUNCTUATION = set("，。！？；：、,.!?;:()（）[]【】{}《》<>“”\"'‘’")


class HandwritingRenderer:
    def __init__(self, config: Config, font_manager: FontManager, rng: random.Random):
        self.config = config
        self.font_manager = font_manager
        self.rng = rng
        self.baseline_offset = 0

    def draw_text(self, page: Image.Image, text: str, x: int, y: int, size: int) -> None:
        if text.strip() and is_latin_text(text) and len(text.strip()) > 1:
            self._draw_text_run(page, text, x, y, size, "english")
            return
        if text.strip() and not is_latin_text(text) and len(text.strip()) > 1:
            self._draw_text_chars(page, text, x, y, size)
            return

        self._draw_text_chars(page, text, x, y, size)

    def _draw_text_chars(self, page: Image.Image, text: str, x: int, y: int, size: int) -> None:
        cursor = float(x)
        for char in text:
            if char.isspace():
                cursor += max(4, size * 0.35)
                continue

            script = "english" if is_latin_text(char) or char in PUNCTUATION else "chinese"
            size_delta = (
                self.rng.choice([-3, -2, -1, 0, 0, 1, 2, 3])
                if script == "chinese"
                else self.rng.choice([-2, -1, 0, 0, 1, 2])
            )
            actual_size = max(self.config.text.min_font_size_px, size + size_delta)
            if char in PUNCTUATION and not is_latin_text(char):
                advance = self._draw_punctuation(page, char, int(round(cursor)), y, actual_size)
                cursor += advance
                continue

            font = self._font_for_char(script, actual_size)
            bbox = self._baseline_bbox(font, char)
            char_w = max(1, bbox[2] - bbox[0])
            char_h = max(1, bbox[3] - bbox[1])
            pad = 8
            layer = Image.new("RGBA", (char_w + pad * 2, char_h + pad * 2), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            anchor = (pad - bbox[0], pad - bbox[1])
            draw.text(anchor, char, font=font, fill=INK_RGB + (255,), anchor="ls")
            layer = self._normalize_ink(layer, thicken=0)
            if script == "chinese":
                layer = self._glyph_variant(layer, actual_size)

            rotation_scale = 1.55 if script == "chinese" else 1.0
            angle = self.rng.uniform(
                -self.config.jitter.char_rotation_deg * rotation_scale,
                self.config.jitter.char_rotation_deg * rotation_scale,
            )
            layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
            dx = self.rng.uniform(-self.config.jitter.char_x_px, self.config.jitter.char_x_px)
            dy = self.rng.uniform(
                -self.config.jitter.char_y_px * 0.25,
                self.config.jitter.char_y_px * 0.25,
            )
            baseline_y = y + self.baseline_offset
            paste_x = int(round(cursor - pad + dx))
            paste_y = int(round(baseline_y - anchor[1] + dy))
            page.alpha_composite(layer, (paste_x, paste_y))
            cursor += char_w + self.rng.uniform(-0.4, 0.9)

    def _draw_punctuation(
        self, page: Image.Image, char: str, x: int, y: int, size: int
    ) -> float:
        width = max(10, int(round(size * 0.32)))
        height = max(14, int(round(size * 0.36)))
        layer = Image.new("RGBA", (width + 8, height + 8), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        stroke = max(1, int(round(size * 0.045)))
        ink = INK_RGB + (INK_ALPHA,)
        cx = width * 0.42 + 4
        lower_y = height * 0.50 + 4

        if char in {"。", "."}:
            r = max(2, int(round(size * 0.055)))
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), outline=ink, width=stroke)
        elif char in {"，", ","}:
            r = max(2, int(round(size * 0.05)))
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), fill=ink)
            draw.line((cx + r * 0.3, lower_y + r, cx - r * 0.8, lower_y + r * 2.5), fill=ink, width=stroke)
        elif char == "、":
            draw.line(
                (cx + size * 0.05, lower_y - size * 0.08, cx - size * 0.08, lower_y + size * 0.12),
                fill=ink,
                width=stroke,
            )
        elif char in {"；", ";"}:
            upper_y = height * 0.18 + 4
            r = max(2, int(round(size * 0.045)))
            draw.ellipse((cx - r, upper_y - r, cx + r, upper_y + r), fill=ink)
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), fill=ink)
            draw.line((cx + r * 0.3, lower_y + r, cx - r * 0.8, lower_y + r * 2.5), fill=ink, width=stroke)
        elif char in {"：", ":"}:
            upper_y = height * 0.18 + 4
            r = max(2, int(round(size * 0.045)))
            draw.ellipse((cx - r, upper_y - r, cx + r, upper_y + r), fill=ink)
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), fill=ink)
        elif char in {"！", "!"}:
            top = height * 0.05 + 4
            bottom = height * 0.42 + 4
            draw.line((cx, top, cx, bottom), fill=ink, width=stroke)
            r = max(2, int(round(size * 0.045)))
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), fill=ink)
        elif char in {"？", "?"}:
            top = height * 0.05 + 4
            mid = height * 0.38 + 4
            r = max(2, int(round(size * 0.045)))
            draw.arc((cx - size * 0.14, top, cx + size * 0.14, mid), 200, 520, fill=ink, width=stroke)
            draw.line((cx, mid, cx, mid + size * 0.08), fill=ink, width=stroke)
            draw.ellipse((cx - r, lower_y - r, cx + r, lower_y + r), fill=ink)
        else:
            font = self.font_manager.font("chinese", size)
            bbox = font.getbbox(char)
            draw.text((4 - bbox[0], 4 - bbox[1]), char, font=font, fill=ink)

        angle = self.rng.uniform(
            -self.config.jitter.char_rotation_deg * 0.3,
            self.config.jitter.char_rotation_deg * 0.3,
        )
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        dx = self.rng.uniform(-self.config.jitter.char_x_px * 0.3, self.config.jitter.char_x_px * 0.3)
        dy = self.rng.uniform(-self.config.jitter.char_y_px * 0.15, self.config.jitter.char_y_px * 0.15)
        baseline_y = y + self.baseline_offset
        page.alpha_composite(layer, (int(round(x + dx)), int(round(baseline_y - lower_y + dy))))
        return width + self.rng.uniform(0.0, 1.0)

    def _draw_text_run(
        self, page: Image.Image, text: str, x: int, y: int, size: int, script: str
    ) -> None:
        actual_size = max(
            self.config.text.min_font_size_px,
            size + self.rng.choice([-2, -1, 0, 0, 1, 2]),
        )
        font = self.font_manager.font(script, actual_size)
        bbox = self._baseline_bbox(font, text)
        run_w = max(1, bbox[2] - bbox[0])
        run_h = max(1, bbox[3] - bbox[1])
        pad = 10
        layer = Image.new("RGBA", (run_w + pad * 2, run_h + pad * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        anchor = (pad - bbox[0], pad - bbox[1])
        draw.text(anchor, text, font=font, fill=INK_RGB + (255,), anchor="ls")
        layer = self._normalize_ink(layer, thicken=0)
        angle = self.rng.uniform(
            -self.config.jitter.char_rotation_deg * 0.8,
            self.config.jitter.char_rotation_deg * 0.8,
        )
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        dx = self.rng.uniform(-self.config.jitter.char_x_px, self.config.jitter.char_x_px)
        dy = self.rng.uniform(
            -self.config.jitter.char_y_px * 0.25,
            self.config.jitter.char_y_px * 0.25,
        )
        baseline_y = y + self.baseline_offset
        paste_x = int(round(x - pad + dx))
        paste_y = int(round(baseline_y - anchor[1] + dy))
        page.alpha_composite(layer, (paste_x, paste_y))

    def _font_for_char(self, script: str, size: int):
        if script != "chinese":
            return self.font_manager.font(script, size)
        variants = self.config.fonts.chinese_variant_fonts or []
        if not variants or self.rng.random() < 0.62:
            return self.font_manager.font("chinese", size)
        path = self.rng.choice(variants)
        return self.font_manager.font_path(path, size)

    @staticmethod
    def _baseline_bbox(font, text: str) -> tuple[int, int, int, int]:
        bbox = font.getbbox(text, anchor="ls")
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            return font.getbbox(text)
        return bbox

    @staticmethod
    def _subtle_resize(image: Image.Image, x_scale: float) -> Image.Image:
        new_width = max(1, int(round(image.width * x_scale)))
        if new_width == image.width:
            return image
        return image.resize((new_width, image.height), Image.Resampling.BICUBIC)

    def _glyph_variant(self, image: Image.Image, size: int) -> Image.Image:
        image = self._subtle_resize(image, self.rng.uniform(0.92, 1.09))
        shear = self.rng.uniform(-0.085, 0.085)
        if abs(shear) > 0.004:
            width, height = image.size
            image = image.transform(
                image.size,
                Image.Transform.AFFINE,
                (1, shear, -shear * height * 0.5, 0, 1, 0),
                Image.Resampling.BICUBIC,
            )
        return self._mesh_warp(image, max_offset=max(0.4, size * 0.018), cells=2)

    def perturb_formula(self, image: Image.Image) -> Image.Image:
        return self._formula_to_ink(image.convert("RGBA"), thicken=0)

    def _formula_to_ink(self, image: Image.Image, thicken: int = 0) -> Image.Image:
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] > 248:
            luminance = image.convert("L")
            alpha = luminance.point(lambda v: max(0, min(255, (245 - v) * 6)))
        return self._alpha_to_ink(alpha, thicken=thicken)

    def _normalize_ink(self, image: Image.Image, thicken: int = 0) -> Image.Image:
        return self._alpha_to_ink(image.convert("RGBA").getchannel("A"), thicken=thicken)

    def _alpha_to_ink(self, alpha: Image.Image, thicken: int = 0) -> Image.Image:
        alpha = alpha.point(lambda value: 255 if value > 16 else 0)
        for _ in range(thicken):
            alpha = alpha.filter(ImageFilter.MaxFilter(3))
        alpha = alpha.filter(ImageFilter.GaussianBlur(0.12))
        alpha = alpha.point(lambda value: int(value * INK_ALPHA / 255))
        result = Image.new("RGBA", alpha.size, INK_RGB + (0,))
        result.putalpha(alpha)
        return result

    def _mesh_warp(self, image: Image.Image, max_offset: float, cells: int) -> Image.Image:
        width, height = image.size
        if width < 12 or height < 12:
            return image
        cols = max(2, min(cells, width // 24 + 1))
        rows = max(2, min(cells, height // 24 + 1))
        vertices: list[list[tuple[float, float]]] = []
        for row in range(rows + 1):
            vertex_row = []
            y = row * height / rows
            for col in range(cols + 1):
                x = col * width / cols
                edge = row in {0, rows} or col in {0, cols}
                scale = 0.35 if edge else 1.0
                vertex_row.append(
                    (
                        self._clamp(x + self.rng.uniform(-max_offset, max_offset) * scale, 0, width),
                        self._clamp(y + self.rng.uniform(-max_offset, max_offset) * scale, 0, height),
                    )
                )
            vertices.append(vertex_row)

        mesh = []
        for row in range(rows):
            y0 = int(round(row * height / rows))
            y1 = int(round((row + 1) * height / rows))
            for col in range(cols):
                x0 = int(round(col * width / cols))
                x1 = int(round((col + 1) * width / cols))
                quad = (
                    *vertices[row][col],
                    *vertices[row + 1][col],
                    *vertices[row + 1][col + 1],
                    *vertices[row][col + 1],
                )
                mesh.append(((x0, y0, x1, y1), quad))
        return image.transform(image.size, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)

    @staticmethod
    def _clamp(value: float, low: int, high: int) -> float:
        return max(low, min(high, value))
