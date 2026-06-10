#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "finance" / "backend"
FRONTEND = ROOT / "finance" / "frontend"


def run(name: str, command: list[str], cwd: Path = ROOT) -> int:
    print(f"\n== {name} ==")
    result = subprocess.run(command, cwd=cwd, text=True, check=False)
    if result.returncode == 0:
        print(f"PASS: {name}")
    else:
        print(f"WARN: {name} returned exit code {result.returncode}")
    return result.returncode


def command_available(command: list[str], cwd: Path = ROOT) -> bool:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def main() -> int:
    failures = 0
    failures += run("local security configuration", [sys.executable, str(BACKEND / "scripts" / "local_security_check.py")])
    failures += run("runtime EOL/support check", [sys.executable, str(BACKEND / "scripts" / "eol_check.py")])
    failures += run(
        "inactive-user deprovisioning dry run",
        [sys.executable, str(BACKEND / "scripts" / "deprovision_inactive_users.py"), "--dry-run"],
    )

    if command_available([sys.executable, "-m", "pip_audit", "--version"]):
        failures += run("Python dependency audit", [sys.executable, "-m", "pip_audit"], cwd=BACKEND)
    else:
        print("\n== Python dependency audit ==\nWARN: pip-audit is not installed. Install it with `python -m pip install pip-audit`.")

    if (FRONTEND / "package-lock.json").exists() and command_available(["npm", "--version"], cwd=FRONTEND):
        failures += run("Frontend dependency audit", ["npm", "audit", "--omit=dev", "--audit-level=moderate"], cwd=FRONTEND)
    else:
        print("\n== Frontend dependency audit ==\nWARN: npm or package-lock.json was not available.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
