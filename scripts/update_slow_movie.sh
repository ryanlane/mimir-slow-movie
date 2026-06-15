#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-/home/ryan/projects/mimir/mimir-slow-movie}"
SRC="${SRC:-${REPO}/channels/slow_movie/}"
DST="${DST:-/var/opt/mimir/mimir-api/channels/slow_movie}"
SERVICE_NAME="${SERVICE_NAME:-mimir-api}"
NO_GIT="${NO_GIT:-0}"
DRY_RUN="${DRY_RUN:-0}"
RESTART="${RESTART:-1}"

SUDO="${SUDO:-sudo}"

if [[ "$NO_GIT" != "1" ]]; then
  git -C "$REPO" fetch --quiet
  git -C "$REPO" pull --ff-only
fi

$SUDO install -d -m 2775 -o mimir -g mimir "$DST"
$SUDO mkdir -p "$DST/data" "$DST/videos"

RSYNC_FLAGS=(-a --delete --exclude 'data/' --exclude 'videos/' --exclude '__pycache__/' --exclude '*.pyc')
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_FLAGS+=(--dry-run)
fi

echo "Syncing ${SRC} -> ${DST}"
$SUDO rsync "${RSYNC_FLAGS[@]}" "$SRC" "$DST"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] skipping permissions and restart"
  exit 0
fi

$SUDO chown -R mimir:mimir "$DST"
$SUDO find "$DST" -type d -exec chmod 755 {} \;
$SUDO find "$DST" -type f -exec chmod 644 {} \;

if [[ "$RESTART" == "1" ]]; then
  $SUDO systemctl restart "$SERVICE_NAME"
fi

echo "✅ Deployed slow movie sources while preserving data and videos"