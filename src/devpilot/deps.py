"""Read-only, privacy-conscious dependency inventory for local repositories.

Run independently with python -m devpilot.deps --path <directory> --json.
No installation hooks, network requests, or project scripts are invoked.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import stat
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .walk import walk_project, _printable
from .cargo_deps import parse_cargo_dependencies
from .cargo_lock import parse_cargo_lock
from .go_mod import parse_go_requirements
from .composer_deps import parse_composer_dependencies
from .composer_lock import parse_composer_lock
from .maven_deps import parse_maven_dependencies
from .dotnet_deps import parse_dotnet_dependencies
from .pyproject_deps import parse_pyproject_dependencies
from .requirements_deps import parse_requirements_dependencies
from .requirements_names import is_requirements_manifest as _is_requirements_manifest
from .pipenv_deps import parse_pipfile_lock
from .pipfile_deps import parse_pipfile_dependencies
from .json_numbers import parse_finite_json_float
from .gemfile_lock import parse_gemfile_lock
from .node_deps import parse_node_dependency_groups
from .uv_lock import parse_uv_lock
from .poetry_lock import parse_poetry_lock

IGNORED = {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "target", "bin", "obj", ".next", ".tox", "__pycache__"}
MAX_BYTES = 512_000
MAX_DEPTH = 4
MAX_FILES = 500
# Recognize PEP 508 "name @ URL" while retaining only the package name.
PYTHON_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s*\[[^\]\n]*\])?(?:\s*(?:[<>=!~;]|@\s*\S|$))")
PYTHON_CANONICAL_SEPARATOR = re.compile(r"[-_.]+")



def _unique_node_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous nested package.json mappings without logging key values."""
    data: dict[str, object] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('package.json contains duplicate JSON object keys')
        data[key] = value
    return data


def _reject_nonfinite_number(_value: str) -> None:
    """Reject Python's nonstandard NaN/Infinity extensions in JSON manifests."""
    raise ValueError("non-finite JSON number in package.json")


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
    return content.decode("utf-8-sig")


def _parse(path: Path) -> tuple[str, dict[str, list[str]]]:
    name = path.name
    content = _read(path)
    if name == "pyproject.toml":
        return "Python", parse_pyproject_dependencies(content)
    if name == "package.json":
        data = json.loads(content, parse_constant=_reject_nonfinite_number,
                          parse_float=parse_finite_json_float,
                          object_pairs_hook=_unique_node_keys)
        if not isinstance(data, dict):
            raise ValueError("package.json root must be an object")
        return "Node.js", parse_node_dependency_groups(data)
    if _is_requirements_manifest(name):
        return "Python", {"requirements": parse_requirements_dependencies(content)}
    if name in ("Gemfile.lock", "gems.locked"):
        return "Ruby", {"locked": parse_gemfile_lock(content)}
    if name == "Pipfile":
        return "Python", parse_pipfile_dependencies(content)
    if name == "Pipfile.lock":
        return "Python", parse_pipfile_lock(content)
    if name == "uv.lock":
        return "Python", {"locked": parse_uv_lock(content)}
    if name == "poetry.lock":
        return "Python", {"locked": parse_poetry_lock(content)}
    if name == "go.mod":
        return "Go", {"require": parse_go_requirements(content)}
    if name == "composer.json":
        return "PHP", parse_composer_dependencies(content)
    if name == "composer.lock":
        return "PHP", parse_composer_lock(content)
    if name == "pom.xml":
        return "Java", parse_maven_dependencies(content)
    if name == "Cargo.toml":
        return "Rust", parse_cargo_dependencies(content)
    if name == "Cargo.lock":
        return "Rust", {"locked": parse_cargo_lock(content)}
    if name == "Directory.Packages.props":
        return ".NET", parse_dotnet_dependencies(content, central=True)
    if name.lower().endswith((".csproj", ".fsproj", ".vbproj")):
        return ".NET", parse_dotnet_dependencies(content)
    raise ValueError("unsupported manifest")


def scan(path: str | Path) -> dict:
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("path is not a directory")
    manifests = []
    warnings = []
    walk_problems: list[str] = []
    found = 0
    depth_limited = False
    file_limited = False
    for current, subdirs, filenames in walk_project(root, walk_problems):
        folder = Path(current)
        depth = len(folder.relative_to(root).parts)
        traversable = sorted(d for d in subdirs if d not in IGNORED and not (folder / d).is_symlink())
        if depth >= MAX_DEPTH:
            if traversable and not depth_limited:
                warnings.append(f"Directory scan limited to depth {MAX_DEPTH}; nested manifests were not inspected")
                depth_limited = True
            subdirs[:] = []
        else:
            subdirs[:] = traversable
        for filename in sorted(filenames):
            if not (filename in ("pyproject.toml", "package.json", "go.mod", "Cargo.toml", "Cargo.lock", "composer.json", "composer.lock", "pom.xml", "Pipfile", "Pipfile.lock", "uv.lock", "poetry.lock", "Gemfile.lock", "gems.locked")
                    or _is_requirements_manifest(filename)
                    or filename == "Directory.Packages.props"
                    or filename.lower().endswith((".csproj", ".fsproj", ".vbproj"))):
                continue
            filepath = folder / filename
            if filepath.is_symlink():
                continue
            if found >= MAX_FILES:
                warnings.append(f"Scan limited to {MAX_FILES} manifests")
                file_limited = True
                break
            found += 1
            rel = filepath.relative_to(root).as_posix()
            try:
                ecosystem, groups = _parse(filepath)
            except RecursionError:
                warnings.append(f"{rel}: manifest nesting exceeds parser limits")
                continue
            except OSError as exc:
                # OSError can embed absolute filenames and private OS strerror.
                # Expose only the stable errno mnemonic in inventory reports.
                warnings.append(f"{rel}: {errno.errorcode.get(exc.errno, 'I/O error')}")
                continue
            except UnicodeError:
                # Decode errors can include private manifest bytes in their text.
                warnings.append(f"{rel}: manifest is not valid UTF-8")
                continue
            except (ValueError, ET.ParseError) as exc:
                warnings.append(f"{rel}: {exc}")
                continue
            manifests.append({"path": rel, "ecosystem": ecosystem, "groups": groups,
                              "count": sum(len(items) for items in groups.values())})
        if file_limited:
            break
    warnings.extend(walk_problems)
    totals: dict[str, int] = {}
    for item in manifests:
        totals[item["ecosystem"]] = totals.get(item["ecosystem"], 0) + item["count"]
    return {"root": str(root), "manifests": manifests, "totals": dict(sorted(totals.items())),
            "warnings": warnings, "truncated": file_limited or depth_limited or bool(walk_problems)}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Read-only dependency manifest inventory")
    cli.add_argument("--path", default=".", help="Repository directory")
    cli.add_argument("--json", action="store_true", help="Print JSON report")
    args = cli.parse_args(argv)
    try:
        report = scan(args.path)
    except (OSError, ValueError) as exc:
        print(_printable(f"devpilot deps: {exc}"), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(_printable(f"Dependency inventory: {report['root']}"))
        for item in report["manifests"]:
            print(_printable(f"  {item['ecosystem']}: {item['path']} ({item['count']} declarations)"))
            for group, names in item["groups"].items():
                print(_printable(f"    {group}: {', '.join(names) or '(none)'}"))
        for warning in report["warnings"]:
            print(_printable(f"  warning: {warning}"))
    return 0 if not report["warnings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())