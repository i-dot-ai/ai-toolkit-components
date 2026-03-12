"""
Read a Qdrant config.yaml and print shell export statements for each setting.

Qdrant picks up configuration from QDRANT__<SECTION>__<KEY> environment
variables (double-underscore separated, uppercase).  This script converts a
config.yaml into those exports so the entrypoint can source them.

Usage:
    eval "$(python3 load_config.py <config_file>)"
"""

import shlex
import sys

import yaml


def to_env_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def config_to_exports(config: dict) -> list[str]:
    exports = []
    for key, value in config.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                env_name = f"QDRANT__{key}__{sub_key}".upper()
                exports.append(f"export {env_name}={shlex.quote(to_env_value(sub_value))}")
        else:
            env_name = f"QDRANT__{key}".upper()
            exports.append(f"export {env_name}={shlex.quote(to_env_value(value))}")
    return exports


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config_file>", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    with open(config_file) as f:
        config = yaml.safe_load(f) or {}

    for line in config_to_exports(config):
        print(line)


if __name__ == "__main__":
    main()
