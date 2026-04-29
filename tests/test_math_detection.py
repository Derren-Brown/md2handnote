import unittest

from md2handnote.parser import parse_markdown


class MathDetectionTest(unittest.TestCase):
    def test_inline_and_block_formula_keys(self):
        result = parse_markdown("a $x$ b\n$$\ny\n$$")
        formulas = {(token.value, token.kind) for token in result.tokens if "math" in token.kind}
        self.assertEqual(formulas, {("x", "inline_math"), ("y", "block_math")})


if __name__ == "__main__":
    unittest.main()
