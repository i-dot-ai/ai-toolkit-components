"""
Parser package for data ingestion.

Provides auto-discovery of parser classes and a registry for lookup by source type.
"""

import importlib
import pkgutil
from pathlib import Path

from .base import BaseParser, ParsedDocument

# Registry mapping source_type -> parser class
_PARSER_REGISTRY: dict[str, type[BaseParser]] = {}


def _discover_parsers() -> None:
    """
    Automatically discover all parser classes in this package.

    Scans all modules for classes that inherit from BaseParser
    and registers them by their source_type property.
    """
    package_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name == "base":
            continue

        module = importlib.import_module(f".{module_info.name}", package=__name__)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseParser)
                and attr is not BaseParser
            ):
                try:
                    instance = attr()
                    _PARSER_REGISTRY[instance.source_type] = attr
                except TypeError:
                    # Skip if can't instantiate with no args
                    pass


def get_parser_class(source_type: str) -> type[BaseParser]:
    """
    Get parser class for a given source type.

    Args:
        source_type: Parser type identifier (e.g., 'html', 'pdf')

    Returns:
        Parser class

    Raises:
        ValueError: If source type is not supported
    """
    if source_type not in _PARSER_REGISTRY:
        raise ValueError(
            f"Unsupported source type: {source_type}. "
            f"Available types: {list(_PARSER_REGISTRY.keys())}"
        )
    return _PARSER_REGISTRY[source_type]


def supported_types() -> list[str]:
    """Return list of supported source types."""
    return list(_PARSER_REGISTRY.keys())


# Run discovery on import
_discover_parsers()


__all__ = [
    "BaseParser",
    "ParsedDocument",
    "get_parser_class",
    "supported_types",
]
