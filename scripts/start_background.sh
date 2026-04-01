#!/bin/bash
# Skript pre spustenie systému na pozadí

PROJECT_DIR="/home/kybermartin/zavlahovy_system"
PID_FILE="$PROJECT_DIR/logs/system.pid"
LOG_FILE="$PROJECT_DIR/logs/system.log"

cd "$PROJECT_DIR"
source venv/bin/activate

# Spustenie v pozadí
nohup python3 main.py > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Systém spustený na pozadí s PID: $!"
echo "Log: $LOG_FILE"
echo "Pre zastavenie: ./scripts/stop.sh"
