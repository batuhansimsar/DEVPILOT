"""Read-only, privacy-conscious dependency inventory for local repositories.

Run independently with python -m devpilot.deps --path <directory> --json.
No installation hooks, network requests, or project scripts are invoked.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .walk import walk_project

IGNORED = {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "target", "bin", "obj", ".next", ".tox", "__pycache__"}
MAX_BYTES = 512_000
MAX_DEPTH = 4
MAX_FILES = 500
PYTHON_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s*\[[^\]\n]*\])?(?:\s*(?:[<>=!~;]|$))")
GO_NAME = re.compile(r"^\s*([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+)\s+v\S+")
CARGO_NAME = re.compile(r'^\s*([A-Za-z0-9_-]+)\s*=')


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Identify file replacement and in-place writes during inspection."""
    return (metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _read(path: Path) -> str:
    """Read a bounded regular file, detecting symlink and concurrent write races.

    Check the descriptor both before and after reading: a same-size rewrite
    must not silently produce an inconsistent dependency report.
    """
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("not a regular file")
    if metadata.st_size > MAX_BYTES:
        raise ValueError("file larger than 512 KB")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("not a regular file")
        if opened.st_size > MAX_BYTES:
            raise ValueError("file larger than 512 KB")
        if _file_identity(opened) != _file_identity(metadata):
            raise ValueError("file changed during inspection")
        content = stream.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError("file larger than 512 KB")
        if _file_identity(os.fstat(stream.fileno())) != _file_identity(opened):
            raise ValueError("file changed during inspection")
    return content.decode("utf-8")


def _parse(path: Path) -> tuple[str, dict[str, list[str]]]:
    name = path.name
    content = _read(path)
    if name == "package.json":
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("package.json root must be an object")
        groups = {}
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            obj = data.get(key, {})
            if not isinstance(obj, dict):
                raise ValueError(f"{key} must be an object")
            if obj:
                groups[key] = sorted(k for k in obj if isinstance(k, str))
        return "Node.js", groups
    if name.startswith("requirements") and name.endswith(".txt"):
        matches = set()
        for line in content.splitlines():
            if line.lstrip().startswith(("#", "-", "git+", "https:", "http:")):
                continue
            match = PYTHON_NAME.match(line)
            if match:
                matches.add(match.group(1).lower().replace("_", "-"))
        return "Python", {"requirements": sorted(matches)}
    if name == "go.mod":
        names = set()
        inside = False
        for line in content.splitlines():
            line = line.split("//", 1)[0].strip()
            if line == "require (":
                inside = True
                continue
            if inside and line == ")":
                inside = False
                continue
            if line.startswith("require "):
                line = line.removeprefix("require ").strip()
            elif not inside:
                continue
            match = GO_NAME.match(line)
            if match:
                names.add(match.group(1))
        return "Go", {"require": sorted(names)}
    if name == "Cargo.toml":
        groups: dict[str, set[str]] = {}
        section = ""
        for raw in content.splitlines():
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line.strip("[]").split(".")[-1]
            elif section in ("dependencies", "dev-dependencies", "build-dependencies"):
                match = CARGO_NAME.match(line)
                if match:
                    groups.setdefault(section, set()).add(match.group(1))
        return "Rust", {key: sorted(value) for key, value in groups.items()}
    if name.endswith((".csproj", ".fsproj", ".vbproj")):
        if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
            raise ValueError("DTD and XML entities are not supported")
        root = ET.fromstring(content)
        names = set()
        for node in root.iter():
            if node.tag.split("}")[-1] == "PackageReference":
                dep = node.attrib.get("Include") or node.attrib.get("Update")
                if dep:
                    names.add(dep)
        return ".NET", {"PackageReference": sorted(names)}
    raise ValueError("unsupported manifest")


def scan(path: str | Path) -> dict:
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("path is not a directory")
    manifests = []
    warnings = []
    found = 0
    for current, subdirs, filenames in walk_project(root, warnings):
        folder = Path(current)
        depth = len(folder.relative_to(root).parts)
        subdirs[:] = sorted(d for d in subdirs if d not in IGNORED and not (folder / d).is_symlink()) if depth < MAX_DEPTH else []
        for filename in sorted(filenames):
            if not (filename in ("package.json", "go.mod", "Cargo.toml")
                    or filename.startswith("requirements") and filename.endswith(".txt")
                    or filename.endswith((".csproj", ".fsproj", ".vbproj"))):
                continue
            filepath = folder / filename
            if filepath.is_symlink():
                continue
            if found >= MAX_FILES:
                warnings.append(f"Scan limited to {MAX_FILES} manifests")
                break
            found += 1
            rel = filepath.relative_to(root).as_posix()
            try:
                ecosystem, groups = _parse(filepath)
            except (OSError, UnicodeError, ValueError, ET.ParseError) as exc:
                warnings.append(f"{rel}: {exc}")
                continue
            manifests.append({"path": rel, "ecosystem": ecosystem, "groups": groups,
                              "count": sum(len(items) for items in groups.values())})
        if found >= MAX_FILES:
            break
    totals: dict[str, int] = {}
    for item in manifests:
        totals[item["ecosystem"]] = totals.get(item["ecosystem"], 0) + item["count"]
    return {"root": str(root), "manifests": manifests, "totals": dict(sorted(totals.items())),
            "warnings": warnings, "truncated": found >= MAX_FILES}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Read-only dependency manifest inventory")
    cli.add_argument("--path", default=".", help="Repository directory")
    cli.add_argument("--json", action="store_true", help="Print JSON report")
    args = cli.parse_args(argv)
    try:
        report = scan(args.path)
    except (OSError, ValueError) as exc:
        print(f"devpilot deps: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Dependency inventory: {report['root']}")
        for item in report["manifests"]:
            print(f"  {item['ecosystem']}: {item['path']} ({item['count']} declarations)")
            for group, names in item["groups"].items():
                print(f"    {group}: {', '.join(names) or '(none)'}")
        for warning in report["warnings"]:
            print(f"  warning: {warning}")
    return 0 if not report["warnings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
