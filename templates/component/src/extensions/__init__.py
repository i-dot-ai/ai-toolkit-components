"""
Extensions package for COMPONENT_NAME.  # TODO: replace COMPONENT_NAME

Extensions are auto-discovered from this package at startup. Any class that
inherits from BaseExtension and defines an extension_type property is
automatically registered and available for lookup by that key.

TODO: Rename this directory and update this file whenever you rename things
      in base.py:

  What to change        Where              Notes
  --------------------  -----------------  ------------------------------------
  "extension_type"      PluginRegistry()   Must exactly match the property name
                                           defined in base.py (e.g. if base.py
                                           uses `def source_type`, write
                                           "source_type" here)
  "extension"           PluginRegistry()   Human-readable label used in log
                                           messages (e.g. "parser", "backend")
  BaseExtension         import + __all__   Match the class name in base.py
  get_extension_class   alias + __all__    Rename to suit your domain
                                           (e.g. get_parser_class)
  available_extensions  alias + __all__    Rename to suit your domain
                                           (e.g. available_parsers)
"""

from pathlib import Path

from registry import PluginRegistry

from .base import BaseExtension  # TODO: rename to match base.py (e.g. BaseParser)

_registry = PluginRegistry(
    BaseExtension,      # TODO: rename to match base.py
    "extension_type",   # TODO: rename to match the property name in base.py
    "extension",        # TODO: rename to a human-readable label (e.g. "parser", "backend")
)
_registry.discover(__name__, Path(__file__).parent)

get_extension_class = _registry.get            # TODO: rename (e.g. get_parser_class)
available_extensions = _registry.supported_keys()  # TODO: rename (e.g. available_parsers)

__all__ = [
    "BaseExtension",        # TODO: rename to match base.py
    "get_extension_class",  # TODO: rename
    "available_extensions", # TODO: rename
]
