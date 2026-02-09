#!/bin/bash
set -e

VERSION="${1:?Usage: ./release.sh <version> (e.g. 0.1.0)}"
TAG="label-v$VERSION"
REPO="francofrizzo/utilities"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
TAP_DIR="$REPO_ROOT/../homebrew-tap"

if [ ! -d "$TAP_DIR/.git" ]; then
  echo "Error: homebrew-tap repo not found at $TAP_DIR" >&2
  echo "Clone it alongside this repo: git clone git@github.com:francofrizzo/homebrew-tap.git" >&2
  exit 1
fi

echo "==> Tagging $TAG"
git -C "$REPO_ROOT" tag "$TAG"
git -C "$REPO_ROOT" push origin "$TAG"

echo "==> Computing SHA256"
SHA=$(curl -sL "https://github.com/$REPO/archive/refs/tags/$TAG.tar.gz" | shasum -a 256 | cut -d' ' -f1)
echo "    $SHA"

echo "==> Updating homebrew-tap formula"
FORMULA="$TAP_DIR/Formula/print-label.rb"
# Update tarball URL
sed -i '' "s|url \"https://github.com/$REPO/archive/.*\"|url \"https://github.com/$REPO/archive/refs/tags/$TAG.tar.gz\"|" "$FORMULA"
# Update only the top-level sha256 (line after the url line), not the bleak resource sha256
sed -i '' "/url \"https:\/\/github.com\/$REPO\/archive/{ n; s|sha256 \".*\"|sha256 \"$SHA\"|; }" "$FORMULA"

echo "==> Pushing homebrew-tap"
git -C "$TAP_DIR" add Formula/print-label.rb
git -C "$TAP_DIR" commit -m "print-label $TAG"
git -C "$TAP_DIR" push

echo ""
echo "Done! Released print-label $TAG"
echo "Users can run: brew upgrade print-label"
