#!/usr/bin/env python3
from __future__ import annotations

import platform
import re
import sqlite3
import subprocess
import sys


MIN_PYTHON = (3, 11)
MIN_NODE_MAJOR = 22
MIN_SQLITE = (3, 39, 0)


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or result.stderr.strip()


def record(results: list[tuple[str, str, str]], level: str, name: str, detail: str) -> None:
    results.append((level, name, detail))


def main() -> int:
    results: list[tuple[str, str, str]] = []

    python_version = sys.version_info[:3]
    record(
        results,
        "PASS" if python_version >= MIN_PYTHON else "FAIL",
        "Python runtime",
        f"{platform.python_version()} detected; policy minimum is {'.'.join(map(str, MIN_PYTHON))}.",
    )

    sqlite_version = sqlite3.sqlite_version_info
    record(
        results,
        "PASS" if sqlite_version >= MIN_SQLITE else "WARN",
        "SQLite runtime",
        f"{sqlite3.sqlite_version} detected; policy minimum is {'.'.join(map(str, MIN_SQLITE))}.",
    )

    node_output = run(["node", "--version"])
    if node_output:
        node_major = version_tuple(node_output)[0]
        record(
            results,
            "PASS" if node_major >= MIN_NODE_MAJOR else "WARN",
            "Node.js runtime",
            f"{node_output} detected; policy minimum for development/build hosts is major {MIN_NODE_MAJOR}.",
        )
    else:
        record(results, "WARN", "Node.js runtime", "Node.js was not found. This is acceptable on runtime-only hosts.")

    npm_output = run(["npm", "--version"])
    record(
        results,
        "PASS" if npm_output else "WARN",
        "npm",
        f"{npm_output} detected." if npm_output else "npm was not found. This is acceptable on runtime-only hosts.",
    )

    record(results, "INFO", "Host platform", platform.platform())

    for level, name, detail in results:
        print(f"{level}: {name} - {detail}")

    return 1 if any(level == "FAIL" for level, _, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
