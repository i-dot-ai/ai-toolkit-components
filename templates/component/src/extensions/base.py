"""
Base extension interface for COMPONENT_NAME.  # TODO: replace COMPONENT_NAME

All extensions must inherit from BaseExtension and implement the required
abstract methods. The extension_type property is the registry key used for
auto-discovery — it must be unique across all extensions registered with the
same PluginRegistry.

TODO: Rename this directory, this file, the class, and the key property to
      reflect your extension's role. The table below shows what to change and
      where the same name must be kept in sync:

  This file              extensions/__init__.py                  Meaning
  ---------------------  --------------------------------------  ----------------
  class BaseExtension    from .base import BaseExtension         The base class
  def extension_type     PluginRegistry(..., "extension_type",)  Must match exactly

  Examples from the existing components:
    parsers/base.py  → class BaseParser,  property source_type
    backends/base.py → class BaseBackend, property backend_type
    tools/base.py    → class BaseTool,    property tool_name
"""

from abc import ABC, abstractmethod


class BaseExtension(ABC):  # TODO: rename (e.g. BaseParser, BaseBackend, BaseTool)
    """
    Abstract base class for COMPONENT_NAME extensions.  # TODO: replace COMPONENT_NAME

    Subclasses must implement:
    - extension_type: unique string identifier for this extension  # TODO: rename
    - (add your abstract methods below)
    """

    @property
    @abstractmethod
    def extension_type(self) -> str:  # TODO: rename to match your domain (e.g. source_type, backend_type)
        """
        Return the unique type identifier for this extension.

        This string is used as the registry key, so it must be unique across
        all extensions of this type (e.g. 'csv', 'json', 'xml').

        IMPORTANT: the string you use here as the property *name* (extension_type)
        must exactly match the key_attr argument passed to PluginRegistry in
        extensions/__init__.py.
        """
        ...

    # -------------------------------------------------------------------------
    # TODO: Add your abstract methods below.
    # Each method should have a clear docstring explaining its contract —
    # what arguments it accepts, what it returns, and any exceptions it raises.
    #
    # Example:
    #
    # @abstractmethod
    # def process(self, data: bytes, source: str) -> dict:
    #     """
    #     Process raw data from a source.
    #
    #     Args:
    #         data:   Raw bytes to process.
    #         source: Identifier of the data source (e.g. a file path or URL).
    #
    #     Returns:
    #         A dict containing the processed result.
    #     """
    #     ...
    # -------------------------------------------------------------------------
