import unittest

from md2handnote.errors import ParseError
from md2handnote.parser import parse_markdown


class ParserTest(unittest.TestCase):
    def test_inline_math_split(self):
        result = parse_markdown("由 $x_i$ 可得 delay 为 $t_k=D_k/r_k$。")
        pairs = [(token.kind, token.value) for token in result.tokens if token.kind != "line_break"]
        self.assertEqual(
            pairs,
            [
                ("text", "由 "),
                ("inline_math", "x_i"),
                ("text", " 可得 delay 为 "),
                ("inline_math", "t_k=D_k/r_k"),
                ("text", "。"),
            ],
        )

    def test_block_math(self):
        result = parse_markdown("前文\n$$\na=b\n$$\n后文")
        block = [token for token in result.tokens if token.kind == "block_math"][0]
        self.assertEqual(block.value, "a=b")
        self.assertEqual(block.line, 2)

    def test_unclosed_block_math(self):
        with self.assertRaises(ParseError):
            parse_markdown("before\n$$\na=b")

    def test_unclosed_inline_math(self):
        with self.assertRaises(ParseError):
            parse_markdown("before $a=b")


if __name__ == "__main__":
    unittest.main()
