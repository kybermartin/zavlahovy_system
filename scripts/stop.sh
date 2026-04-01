#!/bin/bash
# Skript pre zastavenie systému

PROJECT_DIR="/home/kybermartin/zavlahovy_system"
PID_FILE="$PROJECT_DIR/logs/system.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Zastavujem proces s PID: $PID"
    kill $PID
    rm "$PID_FILE"
    echo "Systém zastavený"
else
    echo "Systém nie je spustený (PID súbor nenájdený)"
fi
