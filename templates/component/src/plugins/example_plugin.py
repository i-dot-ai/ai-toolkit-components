"""
Example startup plugin for COMPONENT_NAME.  # TODO: replace COMPONENT_NAME

STARTUP PLUGINS vs EXTENSIBILITY PLUGINS
-----------------------------------------
This file illustrates the *startup plugin* pattern (used by vector_db):

  - Plain Python scripts — no base class or registry required
  - Every .py file in this directory is executed by the entrypoint after
    the service has started, in filename order
  - Intended for one-time setup tasks: creating collections, seeding data,
    configuring indexes, etc.

This is different from the *extensibility plugin* pattern (base.py / __init__.py),
which uses PluginRegistry to auto-discover classes that add new capabilities
(parsers, backends, tools) at runtime.

If your component only needs one of the two patterns, delete the files for
the other. If you only need startup scripts, you can remove base.py,
__init__.py, and registry.py entirely.

HOW TO USE THIS FILE
--------------------
Rename or copy this file for each setup task you need. The entrypoint will
execute all .py files in this directory after the service starts.

Delete this example file once you have added your own plugins.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # TODO: implement your setup logic here
    logger.info("Example startup plugin executed — modify or delete this file")
