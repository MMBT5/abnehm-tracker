#!/bin/bash
# Abnehm-Tracker – Update: Backup, git pull, Image neu bauen, Container neu starten
set -e
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "► Backup..."
bash scripts/backup.sh || echo "  ⚠ Backup übersprungen (Container läuft nicht?)"

echo "► Neueste Version holen..."
git pull --ff-only

echo "► Container neu bauen und starten..."
docker compose up -d --build
echo "✓ Fertig. Logs: docker logs abnehm-tracker -f"
