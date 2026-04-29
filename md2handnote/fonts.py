from __future__ import annotations

from functools import lru_cache

from PIL import ImageFont

from .config import Config


class FontManager:
    def __init__(self, config: Config):
        self.config = config

    @lru_cache(maxsize=128)
    def font(self, script: str, size: int) -> ImageFont.FreeTypeFont:
        path = (
            self.config.fonts.english_font
            if script == "english"
            else self.config.fonts.chinese_font
        )
        return self.font_path(path, size)

    @lru_cache(maxsize=256)
    def font_path(self, path: str, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(path, size=size)

    def font_for_text(self, text: str, size: int | None = None) -> ImageFont.FreeTypeFont:
        script = "english" if is_latin_text(text) else "chinese"
        if size is None:
            size = (
                self.config.text.english_font_size_px
                if script == "english"
                else self.config.text.chinese_font_size_px
            )
        return self.font(script, size)


def is_latin_text(text: str) -> bool:
    meaningful = [c for c in text if not c.isspace()]
    if not meaningful:
        return True
    latin_count = sum(1 for c in meaningful if ord(c) < 128)
    return latin_count >= max(1, len(meaningful) // 2)
