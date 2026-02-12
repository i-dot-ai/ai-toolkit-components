"""
Backends package - pluggable vector database backends.

Backends are auto-discovered from this package. Any class inheriting
from BaseBackend is automatically registered by its backend_type property.
"""

from pathlib import Path

from registry import PluginRegistry

from .base import BaseBackend

_registry = PluginRegistry(BaseBackend, "backend_type", "backend")
_registry.discover(__name__, Path(__file__).parent)

get_backend_class = _registry.get
available_backends = _registry.supported_keys()

__all__ = [
    "BaseBackend",
    "get_backend_class",
    "available_backends",
]
