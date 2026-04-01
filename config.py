# config.py
"""
Konfiguračný súbor pre zavlažovací systém.
Obsahuje všetky globálne nastavenia a konštanty.
"""

import os

# ============================================
# PINY PRE GPIO (podľa BCM číslovania)
# ============================================

# Relé moduly
RELAY_TLAKOVE_PIN = 24      # GPIO24 - tlakové čerpadlo
RELAY_NASAVACIE_PIN = 25    # GPIO25 - nasávacie čerpadlo

# Servá pre ventily (PWM piny)
SERVO_PINS = [17, 18, 22, 23]  # GPIO17,18,22,23 pre okruhy 1-4

# Hladinové senzory (zjednodušená verzia - min a max)
LEVEL_SENSOR_MIN_PIN = 26   # GPIO26 - spínač minimálnej hladiny (prázdna nádrž)
LEVEL_SENSOR_MAX_PIN = 27   # GPIO27 - spínač maximálnej hladiny (plná nádrž)

# I2C zariadenia (adresy)
LCD_I2C_ADDR = 0x27         # Adresa LCD 1602A cez I2C (často 0x27 alebo 0x3F)
RTC_I2C_ADDR = 0x68         # Adresa DS3231 RTC modulu

# ============================================
# NASTAVENIA SERVOMOTOROV
# ============================================

# Rozsah PWM pre SG90 (v percentách)
# 2.5% = 0° (zatvorené), 12.5% = 180° (otvorené)
SERVO_CLOSED_POS = 2.5      # Zatvorený ventil
SERVO_OPEN_POS = 12.5       # Plne otvorený ventil

# ============================================
# NASTAVENIA HLDINOVÝCH SENZOROV
# ============================================

# Typ senzora: NO = normally open, NC = normally closed
# Pre NC spínače: HIGH = suchý, LOW = mokrý
LEVEL_SENSOR_TYPE = "NC"    # NC spínače (normálne zopnuté)

# Čas oneskorenia pre ochranu pred suchým chodom (sekundy)
DRY_RUN_PROTECTION_DELAY = 30  # Vypne po 30s suchého chodu

# ============================================
# WEB ROZHRANIE
# ============================================

WEB_HOST = "0.0.0.0"        # Počúva na všetkých rozhraniach
WEB_PORT = 5000             # Port pre web server

# ============================================
# CESTY K SÚBOROM
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# ============================================
# GLOBÁLNE NASTAVENIA
# ============================================

# Predvolené nastavenia pri prvom spustení
DEFAULT_SETTINGS = {
    "tlakove_auto_mode": True,
    "nasavacie_auto_mode": True,
    "timezone": "Europe/Bratislava",
    "lcd_brightness": 50,       # 0-100%
    "dry_run_protection": True
}

# ============================================
# KONŠTANTY PRE INTERVALY
# ============================================

MAX_INTERVALS = 4            # Maximálny počet intervalov za deň
MIN_INTERVAL_LENGTH = 5      # Minimálna dĺžka intervalu v minútach

# ============================================
# LOGOVANIE
# ============================================

LOG_LEVEL = "INFO"           # DEBUG, INFO, WARNING, ERROR
LOG_FILE = os.path.join(BASE_DIR, "system.log")

# ============================================
# KONTROLA PINOV
# ============================================

def validate_pins():
    """Overí, či nedošlo ku kolízii pinov"""
    all_pins = [
        RELAY_TLAKOVE_PIN,
        RELAY_NASAVACIE_PIN,
        LEVEL_SENSOR_MIN_PIN,
        LEVEL_SENSOR_MAX_PIN
    ] + SERVO_PINS
    
    # Skontrolujeme duplicity
    duplicates = [pin for pin in all_pins if all_pins.count(pin) > 1]
    if duplicates:
        raise ValueError(f"Kolízia pinov: {duplicates}")
    
    # Skontrolujeme I2C piny (2,3) - tie sú rezervované
    i2c_pins = [2, 3]
    for pin in all_pins:
        if pin in i2c_pins:
            raise ValueError(f"Pin {pin} je rezervovaný pre I2C!")
    
    return True

# Validácia pri importe
try:
    validate_pins()
except ValueError as e:
    print(f"Chyba v konfigurácii pinov: {e}")