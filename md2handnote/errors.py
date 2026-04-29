class Md2HandnoteError(Exception):
    """Base exception for user-facing failures."""


class ConfigError(Md2HandnoteError):
    """Invalid configuration or missing required files."""


class ParseError(Md2HandnoteError):
    """Invalid Markdown/math input."""


class DependencyError(Md2HandnoteError):
    """A required runtime dependency is missing."""


class MathRenderError(Md2HandnoteError):
    """LaTeX math rendering failed."""


class LayoutError(Md2HandnoteError):
    """The document cannot be laid out safely."""
