import os
import unittest

from PIL import Image

from md2handnote.config import Config, FontsConfig, PageConfig
from md2handnote.fonts import FontManager
from md2handnote.layout import LayoutEngine, split_text_units
from md2handnote.math_renderer import FormulaAsset
from md2handnote.parser import Token


DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class LayoutTest(unittest.TestCase):
    def test_split_text_units_keeps_english_words(self):
        self.assertEqual(split_text_units("第 k user delay"), ["第", " ", "k", " ", "user", " ", "delay"])

    @unittest.skipUnless(os.path.isfile(DEJAVU), "DejaVuSans font not available")
    def test_layout_wraps_text_and_inline_formula(self):
        config = Config(
            page=PageConfig(dpi=120, margin_left_mm=10, margin_right_mm=10),
            fonts=FontsConfig(chinese_font=DEJAVU, english_font=DEJAVU, math_font_hint=None),
        )
        asset = FormulaAsset("k", "x_i", False, Image.new("RGBA", (80, 24), (0, 0, 0, 255)))
        tokens = [
            Token("text", "由 verylongword transmission delay ", 1),
            Token("inline_math", "x_i", 1),
            Token("text", " 可得。", 1),
        ]
        result = LayoutEngine(config, FontManager(config)).layout(tokens, {("x_i", False): asset})
        self.assertGreaterEqual(len(result.pages), 1)
        self.assertTrue(result.pages[0].elements)


if __name__ == "__main__":
    unittest.main()
