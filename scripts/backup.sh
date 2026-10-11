#!/bin/bash
# Abnehm-Tracker – konsistentes DB-Backup nach <DATA_DIR>/backups/ (letzte 30 behalten)
# Nutzt die SQLite-Backup-API im Container, damit die Kopie auch bei laufendem Betrieb stimmt.
# Cron (täglich 03:00):  0 3 * * * /pfad/zu/abnehm-tracker/scripts/backup.sh
set -e
DATE=$(date +%Y-%m-%d)
docker exec abnehm-tracker python -c "
import sqlite3, os
os.makedirs('/data/backups', exist_ok=True)
src = sqlite3.connect('/data/tracker.db')
dst = sqlite3.connect('/data/backups/tracker_$DATE.db')
src.backup(dst); dst.close(); src.close()"
docker exec abnehm-tracker sh -c 'ls -t /data/backups/tracker_*.db | tail -n +31 | xargs -r rm --'
echo "✓ Backup: backups/tracker_$DATE.db"
