#!/usr/bin/env bash
#
# cleanup-disk.sh — reclaim disk from the usual large, self-regrowing offenders.
#
#   ./cleanup-disk.sh             # safe mode: only caches that regenerate on demand
#   ./cleanup-disk.sh --dry-run   # show what each step WOULD do, change nothing
#   ./cleanup-disk.sh --snapshots # also thin Time Machine local snapshots (needs sudo)
#   ./cleanup-disk.sh --aggressive  # also prune Docker volumes + deeper caches
#   ./cleanup-disk.sh -y          # don't ask for confirmation
#
# Safe mode never deletes data you can't trivially regenerate. Aggressive mode
# can remove un-tagged Docker images and *unused* volumes — review before using.
# --snapshots asks macOS to free space pinned in local TM snapshots so deletions
# show up in `df` immediately (local snapshots only; real backups untouched).

set -uo pipefail

DRY=0; AGGRESSIVE=0; ASSUME_YES=0; SNAPSHOTS=0
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n)     DRY=1 ;;
    --aggressive|-a)  AGGRESSIVE=1 ;;
    --snapshots|-s)   SNAPSHOTS=1 ;;
    -y|--yes)         ASSUME_YES=1 ;;
    -h|--help)        sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

# --- helpers ---------------------------------------------------------------
bytes_free() { df -k / | awk 'NR==2 {print $4 * 1024}'; }
human() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "$1 bytes"; }
have() { command -v "$1" >/dev/null 2>&1; }

run() {
  # run "<description>" <cmd...>
  local desc="$1"; shift
  if [[ $DRY -eq 1 ]]; then
    printf '  [dry-run] %s\n            -> %s\n' "$desc" "$*"
  else
    printf '  • %s\n' "$desc"
    "$@" >/dev/null 2>&1 && printf '    done\n' || printf '    skipped/failed (non-fatal)\n'
  fi
}

confirm() {
  [[ $ASSUME_YES -eq 1 || $DRY -eq 1 ]] && return 0
  read -r -p "Proceed with cleanup? [y/N] " a
  [[ "$a" == "y" || "$a" == "Y" ]]
}

# --- start -----------------------------------------------------------------
START_FREE=$(bytes_free)
echo "Disk free before: $(human "$START_FREE")"
[[ $DRY -eq 1 ]]        && echo "(dry-run — nothing will be deleted)"
[[ $AGGRESSIVE -eq 1 ]] && echo "(AGGRESSIVE mode — Docker volumes & deeper caches in scope)"
echo
confirm || { echo "Aborted."; exit 0; }
echo

echo "Go build/test cache:"
have go && run "go clean -cache -testcache" go clean -cache -testcache
echo

echo "Docker / OrbStack (OrbStack auto-shrinks its disk image after a prune):"
if have docker && docker info >/dev/null 2>&1; then
  if [[ $AGGRESSIVE -eq 1 ]]; then
    run "docker system prune -af --volumes (removes unused images AND volumes)" \
        docker system prune -af --volumes
  else
    run "docker image prune -f (dangling images only)" docker image prune -f
    run "docker builder prune -f (build cache)"        docker builder prune -f
  fi
else
  echo "  • Docker/OrbStack not running — start it to reclaim the 45GB image, then re-run."
fi
echo

echo "Package-manager caches (regenerate on next install):"
have brew && run "brew cleanup --prune=all" brew cleanup --prune=all
have npm  && run "npm cache clean --force"  npm cache clean --force
have uv   && run "uv cache prune"           uv cache prune
echo

echo "App caches:"
run "Playwright browser cache"  rm -rf "$HOME/Library/Caches/ms-playwright"
[[ $AGGRESSIVE -eq 1 ]] && run "Adobe cache" rm -rf "$HOME/Library/Caches/Adobe"
echo

# Run snapshot thinning LAST so it reclaims everything the steps above deleted.
if [[ $SNAPSHOTS -eq 1 ]]; then
  echo "Time Machine local snapshots (frees space pinned by deletions above):"
  # urgency 4 = high; size is a target hint in bytes (~50GB), macOS frees what it can.
  run "sudo tmutil thinlocalsnapshots / 53687091200 4" \
      sudo tmutil thinlocalsnapshots / 53687091200 4
  echo
fi

# --- report ----------------------------------------------------------------
END_FREE=$(bytes_free)
DELTA=$(( END_FREE - START_FREE ))
echo "Disk free after:  $(human "$END_FREE")"
if [[ $DRY -eq 0 ]]; then
  if (( DELTA >= 0 )); then echo "Reclaimed:        $(human "$DELTA")"
  else echo "Net change:       -$(human $(( -DELTA ))) (background activity wrote data)"; fi
fi
if [[ $DRY -eq 0 ]]; then
  tips=()
  [[ $SNAPSHOTS -eq 0 ]]  && tips+=("--snapshots to free space pinned in local TM snapshots (needs sudo)")
  [[ $AGGRESSIVE -eq 0 ]] && tips+=("--aggressive to also prune Docker volumes & Adobe cache")
  if (( ${#tips[@]} )); then
    echo
    echo "Tip: run with"
    for t in "${tips[@]}"; do echo "  • $t"; done
  fi
fi
exit 0
