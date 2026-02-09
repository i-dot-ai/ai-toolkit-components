"""
Embedders package - pluggable vector store backends.

Embedders are auto-discovered from this package. Any class inheriting
from BaseEmbedder is automatically registered by its store_type property.
"""

from pathlib import Path

from registry import PluginRegistry

from .base import BaseEmbedder

_registry = PluginRegistry(BaseEmbedder, "store_type", "embedder")
_registry.discover(__name__, Path(__file__).parent)

get_embedder_class = _registry.get
available_embedders = _registry.supported_keys()

all__ = [
    "BaseEmbedder",
    "get_embedder_class",
    "available_embedders",
]
