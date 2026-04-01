#!/bin/bash
# Skript pre kontrolu stavu systému

PROJECT_DIR="/home/kybermartin/zavlahovy_system"
PID_FILE="$PROJECT_DIR/logs/system.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "✅ Systém BEŽÍ (PID: $PID)"
        echo ""
        echo "Posledné logy:"
        tail -5 "$PROJECT_DIR/logs/system.log"
    else
        echo "❌ Systém NIE JE spustený (neplatný PID)"
        rm "$PID_FILE"
    fi
else
    echo "❌ Systém NIE JE spustený"
fi
