#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ATTEMPTS = 5
DEFAULT_DELAY_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 10


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def set_github_output(name: str, value: str) -> None:
    """Write a step output for GitHub Actions."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print("GITHUB_OUTPUT is not set.", file=sys.stderr)
        sys.exit(1)

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}<<EOF\n{value}\nEOF\n")


def fail(message: str) -> None:
    """Print fatal error and exit."""
    print(message, file=sys.stderr)
    sys.exit(1)


def load_manifest(path: str) -> dict[str, Any]:
    """Load and validate the release manifest file."""
    manifest_path = Path(path).resolve()

    if not manifest_path.exists():
        fail(f"Release manifest not found: {manifest_path}")

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        fail(f"Failed to parse release manifest JSON '{manifest_path}': {exc}")
    except OSError as exc:
        fail(f"Failed to read release manifest '{manifest_path}': {exc}")

    if not isinstance(manifest, dict):
        fail("Release manifest must be a JSON object.")

    return manifest


def substitute_placeholders(value: str, release_id: str, release_version: str) -> str:
    """Substitute supported placeholders in string values."""
    return (
        value.replace("{{ release.version }}", release_version)
        .replace("{{ release.id }}", release_id)
    )


def normalize_string_map(
    raw: dict[str, Any] | None,
    release_id: str,
    release_version: str,
) -> dict[str, str]:
    """Normalize a dict into string:string with placeholder substitution."""
    if not raw:
        return {}

    result: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            result[str(key)] = substitute_placeholders(value, release_id, release_version)
        else:
            result[str(key)] = str(value)
    return result


def get_retry_settings(
    contract: dict[str, Any],
    check: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """Get retry settings from check, contract, or defaults."""
    retries: dict[str, Any] = {}

    if isinstance(contract.get("retries"), dict):
        retries.update(contract["retries"])

    if check and isinstance(check.get("retries"), dict):
        retries.update(check["retries"])

    attempts = retries.get("max_attempts", DEFAULT_ATTEMPTS)
    delay = retries.get("delay_seconds", DEFAULT_DELAY_SECONDS)

    if not isinstance(attempts, int) or attempts < 1:
        attempts = DEFAULT_ATTEMPTS

    if not isinstance(delay, int) or delay < 0:
        delay = DEFAULT_DELAY_SECONDS

    return attempts, delay


def get_timeout_seconds(
    contract: dict[str, Any],
    check: dict[str, Any] | None = None,
) -> int:
    """Get timeout from check, contract, or default."""
    timeout = contract.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)

    if check and "timeout_seconds" in check:
        timeout = check["timeout_seconds"]

    if not isinstance(timeout, int) or timeout < 1:
        timeout = DEFAULT_TIMEOUT_SECONDS

    return timeout


def run_http_check(
    check: dict[str, Any],
    release_id: str,
    release_version: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    """Run a single HTTP verification check."""
    url = check.get("url")
    method = check.get("method", "GET")
    raw_headers = check.get("headers", {})
    headers = normalize_string_map(raw_headers, release_id, release_version)

    expect = check.get("expect", {})
    expected_statuses = expect.get("status_codes", [200])

    body_contains = expect.get("body_contains")
    if isinstance(body_contains, str):
        body_contains = substitute_placeholders(body_contains, release_id, release_version)

    if not url:
        return False, "HTTP check missing required field: url"

    request = urllib.request.Request(url=url, method=method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return False, f"HTTP request failed: {exc}"
    except Exception as exc:
        return False, f"Unexpected HTTP check error: {exc}"

    if status_code not in expected_statuses:
        return False, f"Expected status {expected_statuses}, got {status_code}"

    if body_contains and body_contains not in body:
        return False, f"Response body did not contain expected text: {body_contains}"

    return True, f"HTTP check passed with status {status_code}"


def run_command_check(
    check: dict[str, Any],
    release_id: str,
    release_version: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    """Run a single command verification check."""
    command = check.get("command")
    shell_name = check.get("shell", "bash")
    working_directory = check.get("working_directory")

    raw_env = check.get("env", {})
    extra_env = normalize_string_map(raw_env, release_id, release_version)

    expect = check.get("expect", {})
    expected_exit_code = expect.get("exit_code", 0)

    stdout_contains = expect.get("stdout_contains")
    if isinstance(stdout_contains, str):
        stdout_contains = substitute_placeholders(stdout_contains, release_id, release_version)

    if not command:
        return False, "Command check missing required field: command"

    env = os.environ.copy()
    env.update(extra_env)

    try:
        if shell_name == "bash":
            completed = subprocess.run(
                substitute_placeholders(command, release_id, release_version),
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                cwd=working_directory,
                env=env,
                timeout=timeout_seconds,
            )
        else:
            completed = subprocess.run(
                substitute_placeholders(command, release_id, release_version),
                shell=True,
                capture_output=True,
                text=True,
                cwd=working_directory,
                env=env,
                timeout=timeout_seconds,
            )
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout_seconds} seconds"
    except Exception as exc:
        return False, f"Command execution failed: {exc}"

    if completed.returncode != expected_exit_code:
        stderr_text = completed.stderr.strip()
        extra = f" stderr: {stderr_text}" if stderr_text else ""
        return (
            False,
            f"Expected exit code {expected_exit_code}, got {completed.returncode}.{extra}",
        )

    if stdout_contains and stdout_contains not in completed.stdout:
        return False, f"stdout did not contain expected text: {stdout_contains}"

    return True, "Command check passed"


def run_single_check(
    check: dict[str, Any],
    contract: dict[str, Any],
    release_id: str,
    release_version: str,
) -> tuple[bool, str]:
    """Run one supported verification check."""
    check_type = check.get("type")
    timeout_seconds = get_timeout_seconds(contract, check)

    if check_type == "http":
        return run_http_check(check, release_id, release_version, timeout_seconds)

    if check_type == "command":
        return run_command_check(check, release_id, release_version, timeout_seconds)

    return False, f"Unsupported verification type in first implementation: {check_type}"


def run_check_with_retries(
    check: dict[str, Any],
    contract: dict[str, Any],
    release_id: str,
    release_version: str,
) -> dict[str, Any]:
    """Run a check with retry behavior and return structured result."""
    attempts, delay = get_retry_settings(contract, check)

    check_name = check.get("name") or check.get("type", "unnamed-check")
    check_type = check.get("type", "unknown")

    last_message = "Check did not run"

    for attempt in range(1, attempts + 1):
        passed, message = run_single_check(check, contract, release_id, release_version)
        last_message = message

        if passed:
            return {
                "name": check_name,
                "type": check_type,
                "passed": True,
                "attempts_used": attempt,
                "max_attempts": attempts,
                "delay_seconds": delay,
                "message": message,
            }

        if attempt < attempts:
            time.sleep(delay)

    return {
        "name": check_name,
        "type": check_type,
        "passed": False,
        "attempts_used": attempts,
        "max_attempts": attempts,
        "delay_seconds": delay,
        "message": last_message,
    }


def normalize_checks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert supported contract shapes into a flat check list."""
    contract_type = contract.get("type")

    if contract_type in {"http", "command"}:
        return [contract]

    if contract_type == "composite":
        checks = contract.get("checks", [])
        if not isinstance(checks, list) or not checks:
            fail("Composite verification contract must contain a non-empty checks array.")
        return checks

    fail(f"Unsupported top-level verification contract type in first implementation: {contract_type}")


def composite_stop_on_failure(contract: dict[str, Any]) -> bool:
    """Return whether composite verification should stop on first failure."""
    execution = contract.get("execution", {})
    if isinstance(execution, dict):
        value = execution.get("stop_on_failure")
        if isinstance(value, bool):
            return value
    return True


def main() -> None:
    if len(sys.argv) != 3:
        fail("Usage: verify_release.py <release_manifest_path> <target_environment>")

    verification_started_at = now_utc_iso()

    release_manifest_path = sys.argv[1]
    target_environment = sys.argv[2]

    manifest = load_manifest(release_manifest_path)

    release = manifest.get("release", {})
    release_id = release.get("id", "unknown-release")
    release_version = release.get("version", "unknown-version")

    verification_contract_wrapper = manifest.get("verification_contract", {})
    contract = verification_contract_wrapper.get("definition")

    if not isinstance(contract, dict) or not contract:
        fail("Release manifest is missing embedded verification contract definition.")

    checks = normalize_checks(contract)
    stop_on_failure = composite_stop_on_failure(contract)

    results: list[dict[str, Any]] = []
    failed_count = 0

    for check in checks:
        result = run_check_with_retries(check, contract, release_id, release_version)
        results.append(result)

        if not result["passed"]:
            failed_count += 1
            if stop_on_failure:
                break

    verification_passed = failed_count == 0
    verification_finished_at = now_utc_iso()

    report = {
        "target_environment": target_environment,
        "release_id": release_id,
        "release_version": release_version,
        "verification_started_at": verification_started_at,
        "verification_finished_at": verification_finished_at,
        "verification_passed": verification_passed,
        "verification_error_count": failed_count,
        "results": results,
    }

    report_path = Path("verification-report.json").resolve()
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    set_github_output("verification_passed", "true" if verification_passed else "false")
    set_github_output("verification_error_count", str(failed_count))
    set_github_output("verification_report_path", str(report_path))

    print(f"Verification report written to: {report_path}")

    if not verification_passed:
        print("Verification failed.", file=sys.stderr)
        for result in results:
            if not result["passed"]:
                print(
                    f"- {result['name']} ({result['type']}): {result['message']}",
                    file=sys.stderr,
                )
        sys.exit(1)

    print("Verification passed.")


if __name__ == "__main__":
    main()