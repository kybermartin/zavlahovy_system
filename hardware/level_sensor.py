# hardware/level_sensor.py
"""
Čítanie hladinových spínačov.
"""

import RPi.GPIO as GPIO
import time

class LevelSensor:
    """Trieda pre čítanie hladinového spínača"""
    
    def __init__(self, pin, name="sensor", sensor_type="NO"):
        """
        Inicializácia senzora
        
        Args:
            pin (int): GPIO pin pre čítanie (BCM)
            name (str): Identifikácia senzora
            sensor_type (str): "NO" = normally open, "NC" = normally closed
        """
        self.pin = pin
        self.name = name
        self.sensor_type = sensor_type
        
        # Nastavenie GPIO ako vstup s pull-up rezistorom
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"Hladinový senzor '{name}' inicializovaný na pine {pin} (typ: {sensor_type})")
    
    def read_raw(self):
        """
        Načíta surovú hodnotu z pinu
        
        Returns:
            int: 1 alebo 0 podľa stavu pinu
        """
        return GPIO.input(self.pin)
    
    def is_wet(self):
        """
        Zistí, či je senzor ponorený (voda)
        
        Returns:
            bool: True = je voda, False = sucho
        
        Pre typ NO: 1 = voda, 0 = sucho
        Pre typ NC: 0 = voda, 1 = sucho
        """
        raw = self.read_raw()
        
        if self.sensor_type == "NO":
            return raw == 1  # Normally Open: HIGH = voda
        else:  # NC
            return raw == 0  # Normally Closed: LOW = voda
    
    def is_dry(self):
        """Opačná funkcia k is_wet()"""
        return not self.is_wet()
    
    def read_with_debounce(self, samples=5, delay=0.01):
        """
        Čítanie s ošetrením zákmitov
        
        Args:
            samples (int): Počet vzoriek
            delay (float): Oneskorenie medzi vzorkami (s)
        
        Returns:
            bool: Stabilizovaná hodnota
        """
        values = []
        for _ in range(samples):
            values.append(self.is_wet())
            time.sleep(delay)
        
        # Väčšinové hlasovanie
        return sum(values) > (samples / 2)
    
    def get_status_string(self):
        """Vráti stav ako reťazec pre LCD"""
        return "MOKRY" if self.is_wet() else "SUCHY"