# hardware/level_sensor.py
"""
Zjednodušená trieda pre hladinové senzory.
Dva spínače: jeden pre minimálnu hladinu, druhý pre maximálnu.
Spínače sú NC (Normally Closed) - v suchom stave sú zopnuté.
"""

import RPi.GPIO as GPIO
import time
import threading
from enum import Enum

class LevelState(Enum):
    """Stavy hladiny"""
    EMPTY = "empty"         # Nádrž prázdna (minimálny spínač aktivovaný)
    NORMAL = "normal"       # Hladina v normálnom rozsahu (žiadny spínač aktivovaný)
    FULL = "full"           # Nádrž plná (maximálny spínač aktivovaný)
    ERROR = "error"         # Chybový stav (oba spínače aktivované súčasne)

class LevelSensor:
    """
    Zjednodušená trieda pre dva hladinové spínače (NC typ).
    
    Spínače:
        - min_spínač: aktivuje sa pri minimálnej hladine (0 cm)
        - max_spínač: aktivuje sa pri maximálnej hladine (100 cm)
    
    Normálny stav: oba spínače sú zopnuté (suché)
    """
    
    def __init__(self, pin_min, pin_max, name="level_sensor", debounce_time=0.1):
        """
        Inicializácia hladinových spínačov
        
        Args:
            pin_min (int): GPIO pin pre spínač minimálnej hladiny
            pin_max (int): GPIO pin pre spínač maximálnej hladiny
            name (str): Identifikácia senzora
            debounce_time (float): Čas na ošetrenie zákmitov (sekundy)
        """
        self.pin_min = pin_min
        self.pin_max = pin_max
        self.name = name
        self.debounce_time = debounce_time
        
        # Stavy spínačov (True = zopnutý/suchý, False = rozopnutý/mokrý)
        self._min_state = True      # True = zopnutý (suchý)
        self._max_state = True      # True = zopnutý (suchý)
        self._last_min_state = True
        self._last_max_state = True
        
        # Aktuálny stav hladiny
        self._level_state = LevelState.NORMAL
        
        # Pre detekciu zákmitov
        self._lock = threading.Lock()
        self._min_change_time = 0
        self._max_change_time = 0
        
        # Nastavenie GPIO (NC spínače - pull-up)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_min, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.pin_max, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Pridanie event detekcie pre zmenu stavu
        GPIO.add_event_detect(self.pin_min, GPIO.BOTH, 
                              callback=self._min_changed, 
                              bouncetime=int(debounce_time * 1000))
        GPIO.add_event_detect(self.pin_max, GPIO.BOTH, 
                              callback=self._max_changed, 
                              bouncetime=int(debounce_time * 1000))
        
        # Počiatočné načítanie stavov
        self._update_states()
        
        print(f"Hladinový senzor '{name}' inicializovaný (NC typ)")
        print(f"  Spínač MIN (0 cm): pin {pin_min}")
        print(f"  Spínač MAX (100 cm): pin {pin_max}")
        print(f"  Normálny stav: oba spínače ZOPNUTÉ (suché)")
    
    def _update_states(self):
        """Aktualizácia stavov spínačov"""
        with self._lock:
            self._last_min_state = self._min_state
            self._last_max_state = self._max_state
            
            # NC spínače: LOW = aktivovaný (mokrý), HIGH = normálny (suchý)
            self._min_state = GPIO.input(self.pin_min) == GPIO.HIGH
            self._max_state = GPIO.input(self.pin_max) == GPIO.HIGH
            self._update_level_state()
    
    def _min_changed(self, channel):
        """Callback pri zmene stavu spínača minimálnej hladiny"""
        self._update_states()
        self._min_change_time = time.time()
        self._log_state_change("MIN")
    
    def _max_changed(self, channel):
        """Callback pri zmene stavu spínača maximálnej hladiny"""
        self._update_states()
        self._max_change_time = time.time()
        self._log_state_change("MAX")
    
    def _update_level_state(self):
        """Aktualizácia stavu hladiny na základe spínačov"""
        min_active = not self._min_state   # False = aktivovaný (mokrý)
        max_active = not self._max_state   # False = aktivovaný (mokrý)
        
        if min_active and max_active:
            self._level_state = LevelState.ERROR
            print(f"⚠️ {self.name}: CHYBA - oba spínače aktivované súčasne!")
        elif min_active:
            self._level_state = LevelState.EMPTY
        elif max_active:
            self._level_state = LevelState.FULL
        else:
            self._level_state = LevelState.NORMAL
    
    def _log_state_change(self, spinač):
        """Výpis zmeny stavu pre debug"""
        min_active = not self._min_state
        max_active = not self._max_state
        
        if spinač == "MIN":
            state = "AKTIVOVANÝ (prázdna)" if min_active else "DEAKTIVOVANÝ"
            print(f"📍 {self.name}: MIN spínač {state}")
        else:
            state = "AKTIVOVANÝ (plná)" if max_active else "DEAKTIVOVANÝ"
            print(f"📍 {self.name}: MAX spínač {state}")
        
        # Výpis aktuálneho stavu hladiny
        if self._level_state == LevelState.EMPTY:
            print(f"🌊 {self.name}: NÁDRŽ PRÁZDNA")
        elif self._level_state == LevelState.FULL:
            print(f"🌊 {self.name}: NÁDRŽ PLNÁ")
        elif self._level_state == LevelState.NORMAL:
            print(f"🌊 {self.name}: HLADINA V NORMÁLE")
    
    # ============================================
    # ZÁKLADNÉ METÓDY
    # ============================================
    
    def is_min_active(self):
        """Vráti True ak je aktivovaný spínač minimálnej hladiny (prázdna)"""
        return not self._min_state
    
    def is_max_active(self):
        """Vráti True ak je aktivovaný spínač maximálnej hladiny (plná)"""
        return not self._max_state
    
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
        """
        Získa aktuálny stav hladiny
        
        Returns:
            LevelState: Stav hladiny (EMPTY, NORMAL, FULL, ERROR)
        """
        return self._level_state
    
    def get_level_percent(self):
        """
        Výpočet percentuálnej hladiny (zjednodušená verzia)
        
        Returns:
            int: 0, 50 alebo 100%
        """
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
        Čítanie s ošetrením zákmitov (pre spätnú kompatibilitu)
        
        Returns:
            tuple: (min_state, max_state) - True = suchý, False = mokrý
        """
        with self._lock:
            return self._min_state, self._max_state
    
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
        with self._lock:
            self._min_state = False
            self._max_state = True
            self._update_level_state()
        print(f"🔧 {self.name}: Simulácia - PRÁZDNA NÁDRŽ")
    
    def simulate_full(self):
        """Simuluje plnú nádrž (aktivuje MAX spínač)"""
        with self._lock:
            self._min_state = True
            self._max_state = False
            self._update_level_state()
        print(f"🔧 {self.name}: Simulácia - PLNÁ NÁDRŽ")
    
    def simulate_normal(self):
        """Simuluje normálnu hladinu (žiadny spínač aktivovaný)"""
        with self._lock:
            self._min_state = True
            self._max_state = True
            self._update_level_state()
        print(f"🔧 {self.name}: Simulácia - NORMÁLNA HLADINA")
    
    # ============================================
    # ČISTENIE
    # ============================================
    
    def __del__(self):
        """Čistenie pri ukončení"""
        try:
            GPIO.remove_event_detect(self.pin_min)
            GPIO.remove_event_detect(self.pin_max)
            GPIO.cleanup(self.pin_min)
            GPIO.cleanup(self.pin_max)
        except:
            pass


# ============================================
# TESTOVACÍ KÓD
# ============================================

if __name__ == "__main__":
    print("Test zjednodušeného hladinového senzora")
    print("=" * 50)
    
    # Pre testovanie použijeme simulované GPIO
    # V reálnom prostredí by boli skutočné piny
    
    # Vytvorenie senzora (pre test použijeme fiktívne piny)
    sensor = LevelSensor(pin_min=26, pin_max=27, name="test")
    
    print("\nPočiatočný stav:")
    print(f"  MIN aktívny: {sensor.is_min_active()}")
    print(f"  MAX aktívny: {sensor.is_max_active()}")
    print(f"  Stav: {sensor.get_status_string()}")
    print(f"  Úroveň: {sensor.get_level_percent()}%")
    
    print("\nSimulácia prázdnej nádrže:")
    sensor.simulate_empty()
    print(f"  Stav: {sensor.get_status_string()}")
    print(f"  Úroveň: {sensor.get_level_percent()}%")
    
    print("\nSimulácia normálnej hladiny:")
    sensor.simulate_normal()
    print(f"  Stav: {sensor.get_status_string()}")
    print(f"  Úroveň: {sensor.get_level_percent()}%")
    
    print("\nSimulácia plnej nádrže:")
    sensor.simulate_full()
    print(f"  Stav: {sensor.get_status_string()}")
    print(f"  Úroveň: {sensor.get_level_percent()}%")
    
    print("\n" + "=" * 50)
    print("Test dokončený")