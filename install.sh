#!/usr/bin/env bash
#
# Symlink the standalone scripts in bin/ into ~/.bin (which the dotfiles add to
# PATH). Idempotent; backs up any existing real file first.
#
# Usage: ./install.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.bin"
BACKUP_DIR="$HOME/.bin-backup/$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST"

for src in "$REPO"/bin/*; do
  name="$(basename "$src")"
  [ "$name" = "requirements.txt" ] && continue
  dest="$DEST/$name"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    continue
  fi
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    mkdir -p "$BACKUP_DIR"
    mv "$dest" "$BACKUP_DIR/$name"
    echo "backed up: $dest"
  fi
  chmod +x "$src"
  ln -s "$src" "$dest"
  echo "linked:    $dest -> $src"
done

echo
echo "Done. Backups (if any) in: $BACKUP_DIR"
echo "Scripts need Python deps + an OpenAI key — see README."
