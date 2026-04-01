# Zavlažovací systém pre Raspberry Pi

## Popis
Programovateľný riadiaci systém na zavlažovanie záhrady s podporou:
- Manuálneho a automatického režimu
- 4 časových intervalov denne
- 4 okruhov s reguláciou tlaku
- Webového rozhrania
- LCD displeja 1602A
- RTC modulu DS3231

## Inštalácia

```bash
# 1. Nakopírujte súbory do adresára
cd ~/zavlahovy_system

# 2. Spustite inštaláciu
./install_dependencies.sh

# 3. Reštartujte Raspberry Pi
sudo reboot
```

## Spustenie

Po reštarte:

```bash
cd ~/zavlahovy_system

# Aktivácia virtuálneho prostredia
source scripts/activate.sh

# Spustenie systému
python3 main.py
```

Alebo spustenie na pozadí:
```bash
./scripts/start_background.sh
```

## Prístup k web rozhraniu
Otvorte prehliadač na adrese: `http://192.168.5.56:5000`

## Adresárová štruktúra
- `/hardware` - Ovládacie triedy pre hardvér
- `/core` - Hlavná logika systému
- `/web` - Webové rozhranie (Flask)
- `/data` - Konfiguračné súbory
- `/logs` - Log súbory
- `/scripts` - Pomocné skripty
- `/venv` - Virtuálne Python prostredie

## Ovládanie
- **Dashboard** - Prehľad stavu
- **Plány** - Nastavenie časových intervalov
- **Manuálne** - Ručné ovládanie čerpadiel
- **Nastavenia** - Konfigurácia systému
