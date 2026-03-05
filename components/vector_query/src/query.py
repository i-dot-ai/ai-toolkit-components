"""
Vector Query CLI - Direct access to vector database operations.

Subcommands are auto-discovered from the queries/ package. To add a new
command, drop a file implementing BaseQuery into the queries/ directory —
argparse flags are generated automatically from the query's input_schema.
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

from backends import get_backend_class
from backends.base import BaseBackend
from queries import available_queries, get_query_class

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "/app/custom/config/config.yaml") -> dict:
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_backend(config: dict) -> BaseBackend:
    backend_type = config.get("backend", "qdrant")
    backend_class = get_backend_class(backend_type)
    settings = config.get("backend_settings", {})
    return backend_class(**settings)


def add_query_subparser(subparsers, query) -> None:
    """Register a subparser for a query, generating flags from its input_schema."""
    p = subparsers.add_parser(query.query_name, help=query.description)
    schema = query.input_schema
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for name, prop in properties.items():
        kwargs = {"help": prop.get("description", ""), "dest": name}
        typ = prop.get("type", "string")
        if typ == "integer":
            kwargs["type"] = int
        elif typ == "boolean":
            kwargs["action"] = "store_true"
        if name in required:
            kwargs["required"] = True
        elif "default" in prop:
            kwargs["default"] = prop["default"]

        p.add_argument(f"--{name.replace('_', '-')}", **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query and manage a vector database",
        prog="vector_query",
    )
    parser.add_argument(
        "--config",
        default="/app/custom/config/config.yaml",
        help="Config file path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.required = True

    queries = {name: get_query_class(name)() for name in available_queries}
    for query in queries.values():
        add_query_subparser(subparsers, query)

    args = parser.parse_args()

    config = load_config(args.config)
    backend = get_backend(config)

    try:
        backend.connect()
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    query = queries[args.command]
    schema_params = set(query.input_schema.get("properties", {}).keys())
    kwargs = {k: v for k, v in vars(args).items() if k in schema_params}

    try:
        result = query.execute(backend, **kwargs)
        query.format_output(result, json_output=args.json)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
