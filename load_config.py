#!/usr/bin/env python3

from __future__ import annotations

import os
import sys


def set_github_output(name: str, value: str) -> None:
    """Write a step output for GitHub Actions."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print("GITHUB_OUTPUT is not set.", file=sys.stderr)
        sys.exit(1)

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}<<EOF\n{value}\nEOF\n")


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "cicd.app.yaml"
    config_path = os.path.abspath(config_path)

    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(config_path):
        print(f"Path is not a file: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = f.read()
    except OSError as exc:
        print(f"Failed to read config file '{config_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    if not raw_config.strip():
        print(f"Config file is empty: {config_path}", file=sys.stderr)
        sys.exit(1)

    set_github_output("config_path", config_path)
    set_github_output("config_exists", "true")
    set_github_output("raw_config", raw_config)

    print(f"Loaded config: {config_path}")


if __name__ == "__main__":
    main()