#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from typing import Any

import yaml
from jsonschema import Draft7Validator, FormatChecker


def set_github_output(name: str, value: str) -> None:
    """Write a step output for GitHub Actions."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print("GITHUB_OUTPUT is not set.", file=sys.stderr)
        sys.exit(1)

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}<<EOF\n{value}\nEOF\n")


def fail_with_outputs(error_list: list[str]) -> None:
    """Emit failure outputs and exit."""
    error_json = json.dumps(error_list, indent=2)

    set_github_output("validation_passed", "false")
    set_github_output("validation_error_count", str(len(error_list)))
    set_github_output("validation_errors_json", error_json)

    print("Schema validation failed:", file=sys.stderr)
    for err in error_list:
        print(f"- {err}", file=sys.stderr)

    sys.exit(1)


def load_yaml_file(path: str) -> Any:
    """Load YAML from file path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Failed to parse YAML file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Failed to read YAML file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def load_json_file(path: str) -> Any:
    """Load JSON from file path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON schema '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Failed to read JSON schema '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def format_error_path(error_path: list[Any]) -> str:
    """Format jsonschema error path into a readable dotted path."""
    if not error_path:
        return "<root>"

    return ".".join(str(part) for part in error_path)


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: validate_config.py <config_path> <schema_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    config_path = os.path.abspath(sys.argv[1])
    schema_path = os.path.abspath(sys.argv[2])

    config = load_yaml_file(config_path)
    schema = load_json_file(schema_path)

    if config is None:
        fail_with_outputs([f"{config_path}: config file is empty or parsed to null"])

    if not isinstance(config, dict):
        fail_with_outputs(
            [f"{config_path}: top-level config must be a YAML object"]
        )

    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(config), key=lambda e: list(e.path))

    error_list: list[str] = []

    for error in errors:
        path = format_error_path(list(error.path))
        error_list.append(f"{path}: {error.message}")

    if error_list:
        fail_with_outputs(error_list)

    set_github_output("validation_passed", "true")
    set_github_output("validation_error_count", "0")
    set_github_output("validation_errors_json", "[]")

    print(f"Schema validation passed for: {config_path} using schema: {schema_path}")


if __name__ == "__main__":
    main()