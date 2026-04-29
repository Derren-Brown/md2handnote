from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from .config import load_config, validate_fonts
from .errors import Md2HandnoteError
from .fonts import FontManager
from .layout import LayoutEngine
from .math_renderer import FormulaAsset, MathRenderer
from .parser import Token, parse_markdown
from .pdf_writer import write_pdf
from .renderer import PageRenderer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md2handnote",
        description="Convert Markdown with LaTeX math into handwritten-style lined-paper PDF.",
    )
    parser.add_argument("input", help="Input UTF-8 Markdown file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF path")
    parser.add_argument("--config", default=None, help="Config YAML path")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic random seed")
    parser.add_argument("--dpi", type=int, default=None, help="Override page DPI")
    parser.add_argument("--verbose", action="store_true", help="Print detailed logs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        run(args)
    except Md2HandnoteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130
    return 0


def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.is_file():
        raise Md2HandnoteError(f"Input file does not exist: {input_path}")

    seed = args.seed
    if seed is None:
        seed = random.SystemRandom().randint(0, 2**31 - 1)
        print(f"Seed: {seed}")
    rng = random.Random(seed)

    config = load_config(args.config, dpi_override=args.dpi)
    validate_fonts(config)
    source = input_path.read_text(encoding="utf-8")
    parsed = parse_markdown(source)
    for warning in parsed.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    font_manager = FontManager(config)
    math_assets = _render_math_assets(parsed.tokens, config, args.verbose)
    layout = LayoutEngine(config, font_manager).layout(parsed.tokens, math_assets)
    for warning in layout.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    pages = PageRenderer(config, font_manager, rng).render(layout)
    write_pdf(pages, args.output)
    if args.verbose:
        print(f"Wrote {args.output} ({len(pages)} page(s))")


def _render_math_assets(
    tokens: list[Token], config, verbose: bool
) -> dict[tuple[str, bool], FormulaAsset]:
    formulas = {
        (token.value, token.kind == "block_math")
        for token in tokens
        if token.kind in {"inline_math", "block_math"}
    }
    if not formulas:
        return {}

    renderer = MathRenderer(config, verbose=verbose)
    assets: dict[tuple[str, bool], FormulaAsset] = {}
    for formula, display in sorted(formulas):
        if verbose:
            kind = "block" if display else "inline"
            print(f"Rendering {kind} formula: {formula}")
        assets[(formula, display)] = renderer.render(formula, display)
    return assets


if __name__ == "__main__":
    raise SystemExit(main())
