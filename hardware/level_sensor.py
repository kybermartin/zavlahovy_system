# hardware/level_sensor.py
"""
Zjednodušená trieda pre hladinové senzory.
Dva spínače: jeden pre minimálnu hladinu, druhý pre maximálnu.
Spínače sú NC (Normally Closed) - v suchom stave sú zopnuté.
"""

import RPi.GPIO as GPIO
import time
from enum import Enum

class LevelState(Enum):
    """Stavy hladiny"""
    EMPTY = "empty"         # Nádrž prázdna
    NORMAL = "normal"       # Hladina v normálnom rozsahu
    FULL = "full"           # Nádrž plná
    ERROR = "error"         # Chybový stav (oba spínače aktivované súčasne)

class LevelSensor:
    """
    Zjednodušená trieda pre dva hladinové spínače (NC typ).
    Spínače sa čítajú priamo pri volaní metód.
    """
    
    def __init__(self, pin_min, pin_max, name="level_sensor", debounce_time=0.1):
        """
        Inicializácia hladinových spínačov
        
        Args:
            pin_min (int): GPIO pin pre spínač minimálnej hladiny
            pin_max (int): GPIO pin pre spínač maximálnej hladiny
            name (str): Identifikácia senzora
            debounce_time (float): Čas na ošetrenie zákmitov (sekundy) - len pre informáciu
        """
        self.pin_min = pin_min
        self.pin_max = pin_max
        self.name = name
        self.debounce_time = debounce_time
        
        # Nastavenie GPIO (NC spínače - pull-up)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_min, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.pin_max, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"Hladinový senzor '{name}' inicializovaný (NC typ, bez interruptov)")
        print(f"  Spínač MIN (0 cm): pin {pin_min}")
        print(f"  Spínač MAX (100 cm): pin {pin_max}")
    
    # ============================================
    # ZÁKLADNÉ METÓDY
    # ============================================
    
    def _read_pin(self, pin):
        """Prečíta stav pinu s ošetrením polarity"""
        # NC spínače: LOW = aktivovaný (mokrý), HIGH = normálny (suchý)
        return GPIO.input(pin) == GPIO.LOW
    
    def is_min_active(self):
        """Vráti True ak je aktivovaný spínač minimálnej hladiny (prázdna)"""
        return self._read_pin(self.pin_min)
    
    def is_max_active(self):
        """Vráti True ak je aktivovaný spínač maximálnej hladiny (plná)"""
        return self._read_pin(self.pin_max)
    
    def is_empty(self):
        """Vráti True ak je nádrž prázdna (minimálny spínač aktivovaný)"""
        return self.is_min_active() and not self.is_max_active()
    
    def is_full(self):
        """Vráti True ak je nádrž plná (maximálny spínač aktivovaný)"""
        return self.is_max_active() and not self.is_min_active()
    
    def is_normal(self):
        """Vráti True ak je hladina v normálnom rozsahu (žiadny spínač aktivovaný)"""
        return not self.is_min_active() and not self.is_max_active()
    
    def is_error(self):
        """Vráti True ak je chybový stav (oba spínače aktivované)"""
        return self.is_min_active() and self.is_max_active()
    
    def get_level_state(self):
        """Získa aktuálny stav hladiny"""
        if self.is_empty():
            return LevelState.EMPTY
        elif self.is_full():
            return LevelState.FULL
        elif self.is_normal():
            return LevelState.NORMAL
        else:
            return LevelState.ERROR
    
    def get_level_percent(self):
        """Vráti percentuálnu hodnotu hladiny (0, 50 alebo 100%)"""
        if self.is_empty():
            return 0
        elif self.is_full():
            return 100
        elif self.is_normal():
            return 50
        else:
            return -1  # Chybový stav
    
    def read_with_debounce(self):
        """
        Čítanie s ošetrením zákmitov (jednoduché čítanie bez oneskorenia)
        Pre jednoduchosť vracia aktuálne stavy bez oneskorenia.
        
        Returns:
            tuple: (min_state, max_state) - True = aktivovaný (mokrý), False = suchý
        """
        return self.is_min_active(), self.is_max_active()
    
    def get_status_string(self):
        """Vráti stav ako reťazec pre LCD"""
        if self.is_empty():
            return "PRÁZDNA"
        elif self.is_full():
            return "PLNÁ"
        elif self.is_normal():
            return "NORMÁL"
        else:
            return "CHYBA!"
    
    # ============================================
    # SIMULÁCIA PRE TESTOVANIE (voliteľné)
    # ============================================
    
    def simulate_empty(self):
        """Simuluje prázdnu nádrž (aktivuje MIN spínač)"""
        print(f"🔧 {self.name}: Simulácia - PRÁZDNA NÁDRŽ")
    
    def simulate_full(self):
        """Simuluje plnú nádrž (aktivuje MAX spínač)"""
        print(f"🔧 {self.name}: Simulácia - PLNÁ NÁDRŽ")
    
    def simulate_normal(self):
        """Simuluje normálnu hladinu (žiadny spínač aktivovaný)"""
        print(f"🔧 {self.name}: Simulácia - NORMÁLNA HLADINA")
    
    # ============================================
    # ČISTENIE
    # ============================================
    
    def __del__(self):
        """Čistenie pri ukončení"""
        try:
            GPIO.cleanup(self.pin_min)
            GPIO.cleanup(self.pin_max)
        except:
            pass