#!/usr/bin/env python3
from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT / "finance" / "backend" / ".env"
PLACEHOLDER_PREFIX = "replace-with-"
SENSITIVE_KEYS = {
    "OPENAI_API_KEY",
    "PLAID_SECRET",
    "PLAID_SANDBOX_SECRET",
    "PLAID_PRODUCTION_SECRET",
    "TASKBRAIN_FINANCE_SESSION_SECRET",
    "TASKBRAIN_FINANCE_TOKEN_ENCRYPTION_KEY",
}


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def record(results: list[tuple[str, str, str]], level: str, name: str, detail: str) -> None:
    results.append((level, name, detail))


def env_value_is_set(values: dict[str, str], key: str) -> bool:
    value = values.get(key, "")
    return bool(value) and not value.startswith(PLACEHOLDER_PREFIX)


def tracked_files() -> list[str]:
    result = run_git("ls-files")
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def tracked_secret_leaks(values: dict[str, str]) -> list[str]:
    files = tracked_files()
    secret_values = {
        key: value
        for key, value in values.items()
        if key in SENSITIVE_KEYS and len(value) >= 12 and not value.startswith(PLACEHOLDER_PREFIX)
    }
    leaks: list[str] = []
    for rel_path in files:
        if rel_path.endswith("package-lock.json"):
            continue
        path = ROOT / rel_path
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for key, value in secret_values.items():
            if value in text:
                leaks.append(f"{key} appears in tracked file {rel_path}")
    return leaks


def main() -> int:
    results: list[tuple[str, str, str]] = []
    values = parse_env(ENV_FILE)

    if ENV_FILE.exists():
        record(results, "PASS", ".env exists", "Local backend .env file found.")
    else:
        record(results, "FAIL", ".env exists", "Create finance/backend/.env before enabling Plaid production.")

    ignored = run_git("check-ignore", "-q", "finance/backend/.env").returncode == 0
    record(
        results,
        "PASS" if ignored else "FAIL",
        ".env is ignored",
        "finance/backend/.env is ignored by Git." if ignored else "finance/backend/.env is not ignored by Git.",
    )

    if ENV_FILE.exists():
        mode = stat.S_IMODE(ENV_FILE.stat().st_mode)
        private_mode = mode & 0o077 == 0
        record(
            results,
            "PASS" if private_mode else "WARN",
            ".env permissions",
            f"Current mode is {mode:o}; 600 is recommended.",
        )

    required_keys = [
        "TASKBRAIN_FINANCE_SESSION_SECRET",
        "TASKBRAIN_FINANCE_TOKEN_ENCRYPTION_KEY",
        "PLAID_CLIENT_ID",
        "PLAID_SANDBOX_SECRET",
    ]
    for key in required_keys:
        record(
            results,
            "PASS" if env_value_is_set(values, key) else "FAIL",
            f"{key} configured",
            "Value is present and not a placeholder." if env_value_is_set(values, key) else "Missing or placeholder value.",
        )

    plaid_env = values.get("PLAID_ENV", "sandbox").lower().strip()
    allow_production = values.get("PLAID_ALLOW_PRODUCTION_LINKING", "false").lower().strip() == "true"
    production_secret_present = env_value_is_set(values, "PLAID_PRODUCTION_SECRET")
    record(results, "PASS" if plaid_env in {"sandbox", "production"} else "FAIL", "PLAID_ENV value", plaid_env)
    record(
        results,
        "PASS" if production_secret_present else "WARN",
        "PLAID_PRODUCTION_SECRET stored",
        "Production secret is present." if production_secret_present else "Production secret is not present yet.",
    )

    if plaid_env == "production" and not allow_production:
        record(results, "PASS", "Production linking lock", "Production mode is selected, but linking remains locked.")
    elif plaid_env == "production" and allow_production:
        record(results, "WARN", "Production linking lock", "Production linking is enabled. Confirm the UI is ready.")
    else:
        record(results, "PASS", "Production linking lock", "Sandbox mode is active.")

    origins = values.get("TASKBRAIN_FINANCE_ALLOWED_ORIGINS", "")
    origins_ok = "*" not in origins and "0.0.0.0" not in origins
    record(
        results,
        "PASS" if origins_ok else "FAIL",
        "Allowed origins",
        "No wildcard/public origin found." if origins_ok else "Remove wildcard or public-bind origins before production.",
    )

    tracked_bad = [
        path
        for path in tracked_files()
        if path == "finance/backend/.env"
        or path.startswith("finance/backend/data/")
        or path.endswith((".db", ".sqlite", ".sqlite3"))
    ]
    record(
        results,
        "PASS" if not tracked_bad else "FAIL",
        "No tracked local data",
        "No .env/database/data files are tracked." if not tracked_bad else ", ".join(tracked_bad),
    )

    leaks = tracked_secret_leaks(values)
    record(
        results,
        "PASS" if not leaks else "FAIL",
        "No tracked secret values",
        "No configured secret values were found in tracked files." if not leaks else "; ".join(leaks),
    )

    for level, name, detail in results:
        print(f"{level}: {name} - {detail}")

    return 1 if any(level == "FAIL" for level, _, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
