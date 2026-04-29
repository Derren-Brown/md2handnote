from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .utils import resolve_relative


@dataclass(frozen=True)
class PageConfig:
    size: str = "A4"
    orientation: str = "portrait"
    dpi: int = 300
    margin_left_mm: float = 22
    margin_right_mm: float = 22
    margin_top_mm: float = 18
    margin_bottom_mm: float = 18
    line_spacing_mm: float = 9
    show_lined_paper: bool = True
    show_left_vertical_line: bool = False


@dataclass(frozen=True)
class FontsConfig:
    chinese_font: str = "fonts/chinese_handwriting.ttf"
    english_font: str = "fonts/english_handwriting.ttf"
    math_font_hint: str | None = "fonts/math_handwriting.ttf"
    chinese_variant_fonts: list[str] | None = None


@dataclass(frozen=True)
class TextConfig:
    base_font_size_px: int = 34
    chinese_font_size_px: int = 34
    english_font_size_px: int = 32
    min_font_size_px: int = 26
    ink_alpha_min: int = 210
    ink_alpha_max: int = 245


@dataclass(frozen=True)
class MathConfig:
    renderer: str = "tectonic"
    base_scale: float = 1.0
    inline_scale: float = 0.95
    block_scale: float = 1.05
    min_scale: float = 0.72
    max_width_policy: str = "shrink_then_warn"


@dataclass(frozen=True)
class JitterConfig:
    char_x_px: float = 1.8
    char_y_px: float = 2.2
    char_rotation_deg: float = 1.2
    word_spacing_px: float = 2.5
    line_y_px: float = 1.8
    page_rotation_deg: float = 0.25
    formula_rotation_deg: float = 0.6
    formula_y_px: float = 2.0
    formula_scale: float = 0.025


@dataclass(frozen=True)
class OutputConfig:
    jpeg_quality: int = 95
    keep_temp_files: bool = False


@dataclass(frozen=True)
class Config:
    page: PageConfig = PageConfig()
    fonts: FontsConfig = FontsConfig()
    text: TextConfig = TextConfig()
    math: MathConfig = MathConfig()
    jitter: JitterConfig = JitterConfig()
    output: OutputConfig = OutputConfig()


DEFAULT_CONFIG: dict[str, Any] = {
    "page": PageConfig().__dict__,
    "fonts": FontsConfig().__dict__,
    "text": TextConfig().__dict__,
    "math": MathConfig().__dict__,
    "jitter": JitterConfig().__dict__,
    "output": OutputConfig().__dict__,
}


def load_config(path: str | None = None, dpi_override: int | None = None) -> Config:
    config_path = Path(path) if path else Path("config.yaml")
    base_dir = config_path.resolve().parent if config_path.exists() else Path.cwd()
    data = _deep_copy(DEFAULT_CONFIG)

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"Config file must contain a YAML mapping: {config_path}")
        _deep_merge(data, loaded)

    if dpi_override is not None:
        data.setdefault("page", {})["dpi"] = dpi_override

    for key in ("chinese_font", "english_font", "math_font_hint"):
        data["fonts"][key] = resolve_relative(data["fonts"].get(key), base_dir)
    variants = data["fonts"].get("chinese_variant_fonts") or []
    if not isinstance(variants, list):
        raise ConfigError("fonts.chinese_variant_fonts must be a list when provided")
    data["fonts"]["chinese_variant_fonts"] = [
        resolved for item in variants if (resolved := resolve_relative(item, base_dir))
    ]

    try:
        config = Config(
            page=PageConfig(**data["page"]),
            fonts=FontsConfig(**data["fonts"]),
            text=TextConfig(**data["text"]),
            math=MathConfig(**data["math"]),
            jitter=JitterConfig(**data["jitter"]),
            output=OutputConfig(**data["output"]),
        )
    except TypeError as exc:
        raise ConfigError(f"Invalid config key or value: {exc}") from exc

    _validate_config(config)
    return config


def validate_fonts(config: Config) -> None:
    required = {
        "fonts.chinese_font": config.fonts.chinese_font,
        "fonts.english_font": config.fonts.english_font,
    }
    if config.fonts.math_font_hint:
        required["fonts.math_font_hint"] = config.fonts.math_font_hint
    for index, path in enumerate(config.fonts.chinese_variant_fonts or [], start=1):
        required[f"fonts.chinese_variant_fonts[{index}]"] = path

    missing = [f"{name}: {path}" for name, path in required.items() if not Path(path).is_file()]
    if missing:
        joined = "\n  ".join(missing)
        raise ConfigError(
            "Missing font file(s). Put fonts in the configured path or update config.yaml:\n  "
            + joined
        )


def _validate_config(config: Config) -> None:
    if config.page.size != "A4":
        raise ConfigError("Only page.size=A4 is supported in the MVP")
    if config.page.orientation != "portrait":
        raise ConfigError("Only page.orientation=portrait is supported in the MVP")
    if config.page.dpi <= 0:
        raise ConfigError("page.dpi must be positive")
    if config.page.line_spacing_mm <= 0:
        raise ConfigError("page.line_spacing_mm must be positive")
    if config.text.min_font_size_px <= 0:
        raise ConfigError("text.min_font_size_px must be positive")
    if config.math.min_scale <= 0:
        raise ConfigError("math.min_scale must be positive")


def _deep_copy(value: dict[str, Any]) -> dict[str, Any]:
    return {k: (_deep_copy(v) if isinstance(v, dict) else v) for k, v in value.items()}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
