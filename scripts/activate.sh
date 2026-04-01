#!/bin/bash
# Skript pre aktiváciu virtuálneho prostredia

PROJECT_DIR="/home/kybermartin/zavlahovy_system"

echo "Aktivácia virtuálneho prostredia pre zavlažovací systém"
source "$PROJECT_DIR/venv/bin/activate"

echo "Prostredie aktivované. Pre deaktiváciu použite: deactivate"
echo ""
echo "Pre spustenie systému: python3 main.py"
echo "Pre test: python3 quick_test.py"
