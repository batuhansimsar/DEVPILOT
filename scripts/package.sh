#!/usr/bin/env bash
# Package native CLI snapshots for local verification or manual distribution.
# No upload, release, or deployment occurs here.
set -euo pipefail

version="${1:-snapshot}"
output_dir="${2:-dist}"
case "$version" in
  *[!a-zA-Z0-9._-]*|"") echo 'version must contain only letters, digits, periods, underscores, or hyphens' >&2; exit 2 ;;
esac

command -v go >/dev/null || { echo 'Go is required' >&2; exit 2; }
command -v tar >/dev/null || { echo 'tar is required' >&2; exit 2; }
command -v zip >/dev/null || { echo 'zip is required' >&2; exit 2; }
command -v sha256sum >/dev/null || command -v shasum >/dev/null || { echo 'sha256sum or shasum is required' >&2; exit 2; }

# Refuse a non-empty output directory to avoid overwriting existing artifacts.
if [[ -d "$output_dir" && -n "$(ls -A "$output_dir")" ]]; then
  echo "output directory is not empty: $output_dir" >&2
  exit 2
fi
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd -P)"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT

# A space-separated subset can be selected for quicker local smoke checks.
targets="${TARGETS:-linux/amd64 linux/arm64 darwin/amd64 darwin/arm64 windows/amd64 windows/arm64}"
for target in $targets; do
  case "$target" in
    linux/amd64|linux/arm64|darwin/amd64|darwin/arm64|windows/amd64|windows/arm64) ;;
    *) echo "unsupported target: $target" >&2; exit 2 ;;
  esac
  goos="${target%/*}"
  goarch="${target#*/}"
  name="devpilot_${version}_${goos}_${goarch}"
  stage="$staging/$name"
  mkdir -p "$stage"
  binary="devpilot"
  if [[ "$goos" == windows ]]; then binary="devpilot.exe"; fi
  echo "Building $target..."
  CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" go build -trimpath -buildvcs=false -ldflags='-s -w' -o "$stage/$binary" ./cmd/devpilot
  cp README.md LICENSE "$stage/"
  if [[ "$goos" == windows ]]; then
    (cd "$stage" && zip -q "$output_dir/$name.zip" "$binary" README.md LICENSE)
  else
    tar -czf "$output_dir/$name.tar.gz" -C "$stage" "$binary" README.md LICENSE
  fi
done

# Include only artifacts from this invocation in the checksum file.
manifest="$output_dir/SHA256SUMS"
: > "$manifest"
for target in $targets; do
  goos="${target%/*}"; goarch="${target#*/}"
  name="devpilot_${version}_${goos}_${goarch}"
  archive="$name.tar.gz"
  if [[ "$goos" == windows ]]; then archive="$name.zip"; fi
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$output_dir" && sha256sum "$archive") >> "$manifest"
  else
    (cd "$output_dir" && shasum -a 256 "$archive") >> "$manifest"
  fi
done
printf 'Created %s artifact checksums in %s\n' "$(wc -l < "$manifest" | tr -d ' ')" "$manifest"
