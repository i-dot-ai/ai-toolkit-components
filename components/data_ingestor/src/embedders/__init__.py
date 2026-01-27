"""
Embedder package for vector storage.

Provides auto-discovery of embedder classes and a registry for lookup by store type.
"""

import importlib
import pkgutil
from pathlib import Path

from .base import BaseEmbedder

# Registry mapping store_type -> embedder class
_EMBEDDER_REGISTRY: dict[str, type[BaseEmbedder]] = {}


def _discover_embedders() -> None:
    """
    Automatically discover all embedder classes in this package.

    Scans all modules for classes that inherit from BaseEmbedder
    and registers them by their store_type property.
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
                and issubclass(attr, BaseEmbedder)
                and attr is not BaseEmbedder
            ):
                try:
                    instance = attr()
                    _EMBEDDER_REGISTRY[instance.store_type] = attr
                except TypeError:
                    # Skip if can't instantiate with no args
                    pass


def get_embedder_class(store_type: str) -> type[BaseEmbedder]:
    """
    Get embedder class for a given store type.

    Args:
        store_type: Embedder type identifier (e.g., 'qdrant', 'pinecone')

    Returns:
        Embedder class

    Raises:
        ValueError: If store type is not supported
    """
    if store_type not in _EMBEDDER_REGISTRY:
        raise ValueError(
            f"Unsupported store type: {store_type}. "
            f"Available types: {list(_EMBEDDER_REGISTRY.keys())}"
        )
    return _EMBEDDER_REGISTRY[store_type]


def supported_stores() -> list[str]:
    """Return list of supported store types."""
    return list(_EMBEDDER_REGISTRY.keys())


# Run discovery on import
_discover_embedders()


__all__ = [
    "BaseEmbedder",
    "get_embedder_class",
    "supported_stores",
]
