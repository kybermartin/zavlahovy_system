#!/bin/bash
# Skript pre spustenie zavlažovacieho systému

PROJECT_DIR="/home/kybermartin/zavlahovy_system"
LOG_FILE="$PROJECT_DIR/logs/system.log"

echo "Spúšťam zavlažovací systém..."
cd "$PROJECT_DIR"

# Aktivácia venv a spustenie
source venv/bin/activate
python3 main.py >> "$LOG_FILE" 2>&1
