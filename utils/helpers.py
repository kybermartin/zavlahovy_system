# utils/helpers.py
"""
Pomocné funkcie pre zavlažovací systém.
"""

import json
import os
from datetime import datetime

def load_json_file(filename, default=None):
    """
    Bezpečné načítanie JSON súboru
    
    Args:
        filename (str): Cesta k súboru
        default: Predvolená hodnota pri chybe
    
    Returns:
        dict: Načítané dáta alebo default
    """
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Chyba pri načítaní {filename}: {e}")
    
    return default if default is not None else {}

def save_json_file(filename, data):
    """
    Bezpečné uloženie JSON súboru
    
    Args:
        filename (str): Cesta k súboru
        data (dict): Dáta na uloženie
    
    Returns:
        bool: True ak úspešné
    """
    try:
        # Vytvorenie adresára ak neexistuje
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Chyba pri ukladaní {filename}: {e}")
        return False

def time_to_minutes(time_str):
    """
    Konverzia času "HH:MM" na minúty od polnoci
    
    Args:
        time_str (str): Čas vo formáte "HH:MM"
    
    Returns:
        int: Počet minút alebo 0 pri chybe
    """
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return t.hour * 60 + t.minute
    except:
        return 0

def minutes_to_time(minutes):
    """
    Konverzia minút od polnoci na reťazec "HH:MM"
    
    Args:
        minutes (int): Počet minút (0-1439)
    
    Returns:
        str: Čas vo formáte "HH:MM"
    """
    minutes = max(0, min(1439, minutes))
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def format_duration(seconds):
    """
    Formátovanie trvania v sekundách
    
    Args:
        seconds (int): Počet sekúnd
    
    Returns:
        str: Formátované trvanie (napr. "2h 30m")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def validate_pressure(pressure):
    """
    Validácia hodnoty tlaku
    
    Args:
        pressure (int/float): Hodnota tlaku
    
    Returns:
        tuple: (bool, str) - (platnosť, chybová správa)
    """
    try:
        p = float(pressure)
        if 0 <= p <= 100:
            return True, "OK"
        else:
            return False, "Tlak musí byť 0-100%"
    except:
        return False, "Neplatná hodnota tlaku"

def get_status_emoji(status):
    """
    Konverzia stavu na emoji pre LCD
    
    Args:
        status (str): Stav (BEZI, VYP, AUTO, MANUAL)
    
    Returns:
        str: Emoji reprezentácia
    """
    emoji_map = {
        'BEZI': '⏵',
        'VYP': '⏸',
        'AUTO': '🔄',
        'MANUAL': '👤',
        'OK': '✅',
        'CHYBA': '⚠️'
    }
    return emoji_map.get(status, '?')

def safe_gpio_cleanup(pins):
    """
    Bezpečné vyčistenie GPIO pinov
    
    Args:
        pins (list): Zoznam pinov na vyčistenie
    """
    import RPi.GPIO as GPIO
    try:
        for pin in pins:
            try:
                GPIO.cleanup(pin)
            except:
                pass
    except:
        pass