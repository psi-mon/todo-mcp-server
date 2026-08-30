"""Launch the MCP Inspector against this project's stdio server.

``uv run mcp dev`` shells out to ``npx @modelcontextprotocol/inspector`` (latest v2).
That fails in two common local setups:

- nvm default Node 18: ``styleText`` is missing from ``node:util``
- mixed Node / npx cache: Inspector v2 cannot load its native keyring binding

This launcher puts a Node >= 22.19 first on PATH and pins Inspector **v1**, which
is the documented workaround until v2's keyring install is reliable via npx.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MIN_NODE = (22, 19, 0)
INSPECTOR = "@modelcontextprotocol/inspector@v1-latest"
ROOT = Path(__file__).resolve().parents[2]


def _node_version(binary: Path) -> tuple[int, int, int] | None:
    try:
        out = subprocess.check_output(
            [str(binary), "-p", "process.versions.node"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        parts = out.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2] if len(parts) > 2 else 0)
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return None


def _candidates() -> list[Path]:
    found: list[Path] = []
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        found.extend(sorted(nvm_root.glob("*/bin/node"), reverse=True))
    for extra in (Path("/opt/homebrew/bin/node"), Path("/usr/local/bin/node")):
        found.append(extra)
    which = shutil.which("node")
    if which:
        found.append(Path(which))
    return found


def find_node() -> Path:
    best: Path | None = None
    best_ver: tuple[int, int, int] | None = None
    seen: set[Path] = set()
    for node in _candidates():
        if not node.is_file():
            continue
        resolved = node.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ver = _node_version(node)
        if ver is None or ver < MIN_NODE:
            continue
        if best_ver is None or ver > best_ver:
            best, best_ver = node, ver
    if best is None:
        sys.stderr.write(
            "MCP Inspector needs Node.js >= 22.19.0.\n"
            "This repo has an .nvmrc: run `nvm install && nvm use`, or `brew install node`.\n"
        )
        raise SystemExit(1)
    return best


def main() -> None:
    node = find_node()
    env = os.environ.copy()
    env["PATH"] = f"{node.parent}{os.pathsep}{env.get('PATH', '')}"
    env.pop("VIRTUAL_ENV", None)

    uv = shutil.which("uv", path=env["PATH"]) or "uv"
    cmd = [
        "npx",
        "--yes",
        INSPECTOR,
        "--",
        uv,
        "--directory",
        str(ROOT),
        "run",
        "todo-mcp",
    ]
    raise SystemExit(subprocess.call(cmd, env=env))


if __name__ == "__main__":
    main()
