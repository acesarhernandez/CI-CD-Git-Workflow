#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from typing import Any

import yaml


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

    set_github_output("policy_validation_passed", "false")
    set_github_output("policy_error_count", str(len(error_list)))
    set_github_output("policy_errors_json", error_json)

    print("Policy validation failed:", file=sys.stderr)
    for err in error_list:
        print(f"- {err}", file=sys.stderr)

    sys.exit(1)


def load_yaml_file(path: str) -> dict[str, Any]:
    """Load YAML config file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Failed to parse YAML file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Failed to read YAML file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)

    if data is None:
        fail_with_outputs([f"{path}: config file is empty or parsed to null"])

    if not isinstance(data, dict):
        fail_with_outputs([f"{path}: top-level config must be a YAML object"])

    return data


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: policy_validate.py <config_path> <target_environment>",
            file=sys.stderr,
        )
        sys.exit(1)

    config_path = os.path.abspath(sys.argv[1])
    target_environment = sys.argv[2]

    config = load_yaml_file(config_path)

    errors: list[str] = []

    profile = config.get("profile", {})
    profile_id = profile.get("id")

    app = config.get("app", {})
    app_role = app.get("role")

    deploy_modes = config.get("deploy_modes", {})
    primary_mode = deploy_modes.get("primary")
    allow_source_deploy = deploy_modes.get("allow_source_deploy", False)
    source_deploy = deploy_modes.get("source_deploy", {})

    environments = config.get("environments", {})

    # Rule 1: target environment must exist
    if target_environment not in environments:
        errors.append(
            f"Requested target environment '{target_environment}' is not defined in environments"
        )

    # Rule 2: primary deploy mode cannot be source
    if primary_mode == "source":
        errors.append("deploy_modes.primary cannot be 'source'")

    # Rule 3: role required for container profiles
    if profile_id in {"container-single", "compose-multi"} and not app_role:
        errors.append(
            f"app.role is required when profile.id is '{profile_id}'"
        )

    # Rule 4: source deploy enabled must have required restrictions
    if allow_source_deploy:
        if not isinstance(source_deploy, dict) or not source_deploy:
            errors.append(
                "deploy_modes.source_deploy must be defined when allow_source_deploy is true"
            )
        else:
            allowed_envs = source_deploy.get("allowed_environments", [])
            allowed_branches = source_deploy.get("allowed_branches", [])

            if not allowed_envs:
                errors.append(
                    "deploy_modes.source_deploy.allowed_environments must not be empty when source deploy is allowed"
                )

            if not allowed_branches:
                errors.append(
                    "deploy_modes.source_deploy.allowed_branches must not be empty when source deploy is allowed"
                )

            if "production" in allowed_envs:
                errors.append(
                    "Source deploy cannot allow the production environment"
                )

    # Rule 5: source deploy forbidden in production environment config
    production_cfg = environments.get("production", {})
    production_source_deploy = production_cfg.get("source_deploy", {})

    if (
        target_environment == "production"
        and isinstance(production_source_deploy, dict)
        and production_source_deploy.get("enabled") is True
    ):
        errors.append("Source deploy is forbidden in production")

    if errors:
        fail_with_outputs(errors)

    set_github_output("policy_validation_passed", "true")
    set_github_output("policy_error_count", "0")
    set_github_output("policy_errors_json", "[]")

    print(
        f"Policy validation passed for: {config_path} (target environment: {target_environment})"
    )


if __name__ == "__main__":
    main()