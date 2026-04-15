#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def set_github_output(name: str, value: str) -> None:
    """Write a step output for GitHub Actions."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print("GITHUB_OUTPUT is not set.", file=sys.stderr)
        sys.exit(1)

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}<<EOF\n{value}\nEOF\n")


def require_env(name: str) -> str:
    """Get a required environment variable and fail if missing or empty."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Required environment variable '{name}' is missing or empty.", file=sys.stderr)
        sys.exit(1)
    return value


def optional_env(name: str) -> str | None:
    """Get an optional environment variable."""
    value = os.environ.get(name, "").strip()
    return value if value else None


def parse_json_env(name: str) -> Any:
    """Parse a required JSON environment variable."""
    raw = require_env(name)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Environment variable '{name}' is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)


def parse_bool_env(name: str) -> bool:
    """Parse a required boolean environment variable."""
    raw = require_env(name).lower()
    if raw == "true":
        return True
    if raw == "false":
        return False

    print(
        f"Environment variable '{name}' must be 'true' or 'false', got: {raw}",
        file=sys.stderr,
    )
    sys.exit(1)


def parse_int_env(name: str) -> int | None:
    """Parse an optional integer environment variable."""
    raw = optional_env(name)
    if raw is None:
        return None

    try:
        return int(raw)
    except ValueError:
        print(f"Environment variable '{name}' must be an integer, got: {raw}", file=sys.stderr)
        sys.exit(1)


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Serialize manifest deterministically for hashing/writing."""
    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def sha256_bytes(data: bytes) -> str:
    """Compute SHA256 for bytes."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def main() -> None:
    app_name = require_env("APP_NAME")
    service = require_env("SERVICE")
    profile = require_env("PROFILE")
    role = optional_env("ROLE")

    release_version = require_env("RELEASE_VERSION")
    release_id = require_env("RELEASE_ID")
    created_at = require_env("CREATED_AT")
    source_ref = require_env("SOURCE_REF")
    commit_sha = require_env("COMMIT_SHA")
    short_sha = require_env("SHORT_SHA")
    branch = require_env("BRANCH")
    tag = optional_env("TAG")

    deployment_unit_type = require_env("DEPLOYMENT_UNIT_TYPE")
    image_registry = require_env("IMAGE_REGISTRY")
    image_repository = require_env("IMAGE_REPOSITORY")
    image_tag = require_env("IMAGE_TAG")
    image_digest = require_env("IMAGE_DIGEST")

    runner_type = require_env("RUNNER_TYPE")
    workflow_ref = require_env("WORKFLOW_REF")
    workflow_run_id = require_env("WORKFLOW_RUN_ID")
    workflow_run_attempt = parse_int_env("WORKFLOW_RUN_ATTEMPT")
    started_at = require_env("STARTED_AT")
    finished_at = require_env("FINISHED_AT")
    source_config_hash = require_env("SOURCE_CONFIG_HASH")
    build_inputs_hash = optional_env("BUILD_INPUTS_HASH")

    verification_contract = parse_json_env("VERIFICATION_CONTRACT_JSON")
    supported_environments = parse_json_env("SUPPORTED_ENVIRONMENTS_JSON")

    deploy_mode = require_env("DEPLOY_MODE")
    source_deploy_eligible = parse_bool_env("SOURCE_DEPLOY_ELIGIBLE")

    recovery_strategy = require_env("RECOVERY_STRATEGY")
    retained = parse_bool_env("RETAINED")
    previous_release_id = optional_env("PREVIOUS_RELEASE_ID")
    rollback_commit_sha = optional_env("ROLLBACK_COMMIT_SHA")

    deployment_unit_digest_verified = parse_bool_env("DEPLOYMENT_UNIT_DIGEST_VERIFIED")
    output_path_raw = require_env("OUTPUT_PATH")

    if deployment_unit_type != "image":
        print(
            f"Only image deployment_unit_type is supported in this first implementation, got: {deployment_unit_type}",
            file=sys.stderr,
        )
        sys.exit(1)

    if deploy_mode != "image":
        print(
            f"Only image deploy_mode is supported in this first implementation, got: {deploy_mode}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(supported_environments, list) or not supported_environments:
        print(
            "SUPPORTED_ENVIRONMENTS_JSON must be a non-empty JSON array.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(verification_contract, dict) or not verification_contract:
        print(
            "VERIFICATION_CONTRACT_JSON must be a non-empty JSON object.",
            file=sys.stderr,
        )
        sys.exit(1)

    manifest: dict[str, Any] = {
        "schema_version": "1",
        "kind": "release_manifest",
        "manifest_version": 1,
        "release": {
            "id": release_id,
            "version": release_version,
            "created_at": created_at,
            "channel": branch,
            "source_ref": source_ref,
            "git": {
                "commit_sha": commit_sha,
                "short_sha": short_sha,
                "branch": branch,
                "tag": tag,
            },
        },
        "app": {
            "name": app_name,
            "service": service,
            "profile": profile,
            "role": role,
        },
        "deployment_unit": {
            "type": "image",
            "image": {
                "registry": image_registry,
                "repository": image_repository,
                "tag": image_tag,
                "digest": image_digest,
            },
        },
        "build": {
            "runner_type": runner_type,
            "workflow_ref": workflow_ref,
            "workflow_run_id": workflow_run_id,
            "workflow_run_attempt": workflow_run_attempt,
            "started_at": started_at,
            "finished_at": finished_at,
            "source_config_hash": source_config_hash,
            "build_inputs_hash": build_inputs_hash,
        },
        "verification_contract": {
            "source": "embedded",
            "definition": verification_contract,
        },
        "compatibility": {
            "supported_environments": supported_environments,
            "deploy_mode": deploy_mode,
            "source_deploy_eligible": source_deploy_eligible,
        },
        "recovery": {
            "recovery_strategy": recovery_strategy,
            "retained": retained,
            "previous_release_id": previous_release_id,
            "rollback_commit_sha": rollback_commit_sha,
        },
        "integrity": {
            "manifest_sha256": "",
            "deployment_unit_digest_verified": deployment_unit_digest_verified,
        },
    }

    # Compute manifest hash from canonical JSON with empty manifest_sha256 field
    manifest_for_hash = json.loads(json.dumps(manifest))
    manifest_bytes_for_hash = canonical_json_bytes(manifest_for_hash)
    manifest_sha256 = sha256_bytes(manifest_bytes_for_hash)

    # Set final hash and write once
    manifest["integrity"]["manifest_sha256"] = manifest_sha256

    output_path = Path(output_path_raw).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_manifest_bytes = canonical_json_bytes(manifest)
    with output_path.open("wb") as f:
        f.write(final_manifest_bytes)

    set_github_output("manifest_path", str(output_path))
    set_github_output("manifest_sha256", manifest_sha256)
    set_github_output("release_id", release_id)
    set_github_output("release_version", release_version)

    print(f"Generated release manifest: {output_path}")
    print(f"Manifest SHA256: {manifest_sha256}")


if __name__ == "__main__":
    main()