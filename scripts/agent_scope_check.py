#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Enforce AGENT_CAPABILITIES.md scope contract on PRs from agents/* branches.

Usage: agent_scope_check.py <base-ref> <head-ref>

Exits non-zero on:
  - file outside allow list
  - file inside deny list (deny wins over allow)
  - changed-file count over limits.max_files
  - added+removed line total over limits.max_loc
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def glob_to_regex(pat: str) -> re.Pattern[str]:
    out: list[str] = []
    i = 0
    while i < len(pat):
        c = pat[i]
        if c == "*":
            if i + 1 < len(pat) and pat[i + 1] == "*":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c in r".()+|^$\{}[]":
            out.append("\\" + c)
            i += 1
        else:
            out.append(c)
            i += 1
    return re.compile("^" + "".join(out) + "$")


def parse_capabilities(path: Path) -> dict:
    text = path.read_text()
    m = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not m:
        sys.exit(f"FAIL: no ```yaml block in {path}")
    return parse_simple_yaml(m.group(1))


def parse_simple_yaml(body: str) -> dict:
    spec: dict = {"allow": [], "deny": [], "limits": {}}
    section: str | None = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            section = key if key in spec else None
            continue
        if section in ("allow", "deny"):
            stripped = line.strip()
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                spec[section].append(value)
        elif section == "limits":
            stripped = line.strip()
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                spec["limits"][k.strip()] = int(v.strip())
    return spec


def diff_files(base: str, head: str) -> list[tuple[str, int, int]]:
    out = subprocess.check_output(
        ["git", "diff", "--numstat", f"{base}...{head}"], text=True
    )
    rows: list[tuple[str, int, int]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        rows.append((path, _to_int(added), _to_int(removed)))
    return rows


def _to_int(value: str) -> int:
    return int(value) if value.isdigit() else 0


def matches_any(path: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.match(path) for p in patterns)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    base, head = argv[1], argv[2]
    spec = parse_capabilities(Path("AGENT_CAPABILITIES.md"))
    allow = [glob_to_regex(p) for p in spec["allow"]]
    deny = [glob_to_regex(p) for p in spec["deny"]]
    max_files = spec["limits"].get("max_files", 25)
    max_loc = spec["limits"].get("max_loc", 800)

    files = diff_files(base, head)
    if not files:
        print(f"INFO: no diff between {base} and {head}; passing")
        return 0

    errors: list[str] = []
    for path, _added, _removed in files:
        if matches_any(path, deny):
            errors.append(f"DENY: {path} matches a deny-listed glob")
            continue
        if not matches_any(path, allow):
            errors.append(f"OUT-OF-SCOPE: {path} does not match any allow-listed glob")

    if len(files) > max_files:
        errors.append(f"LIMIT: {len(files)} files changed (max_files={max_files})")
    total_loc = sum(a + r for _, a, r in files)
    if total_loc > max_loc:
        errors.append(f"LIMIT: {total_loc} added+removed lines (max_loc={max_loc})")

    if errors:
        print("Agent scope check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nEdit AGENT_CAPABILITIES.md to expand scope, or split this slice.",
            file=sys.stderr,
        )
        return 1

    print(
        f"PASS: {len(files)} file(s), {total_loc} LOC -- "
        f"within limits ({max_files} files, {max_loc} LOC)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
