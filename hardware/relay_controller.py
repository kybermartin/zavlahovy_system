# hardware/relay_controller.py
"""
Ovládanie relé modulov pre čerpadlá.
"""

import RPi.GPIO as GPIO
import time

class RelayController:
    """Trieda pre ovládanie jedného relé modulu"""
    
    # Stavy relé
    OFF = 0
    ON = 1
    
    def __init__(self, pin, active_high=True, name="relay"):
        """
        Inicializácia relé
        
        Args:
            pin (int): GPIO pin pre ovládanie relé (BCM)
            active_high (bool): True = HIGH zapína, False = LOW zapína
            name (str): Identifikácia relé pre logovanie
        """
        self.pin = pin
        self.active_high = active_high
        self.name = name
        self.state = self.OFF
        
        # Nastavenie GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        # Nastavíme počiatočný stav na OFF
        self.off()
        
        print(f"Relé '{name}' inicializované na pine {pin}")
    
    def on(self):
        """Zapnutie relé"""
        if self.active_high:
            GPIO.output(self.pin, GPIO.HIGH)
        else:
            GPIO.output(self.pin, GPIO.LOW)
        self.state = self.ON
        print(f"Relé '{self.name}' ZAPNUTÉ")
    
    def off(self):
        """Vypnutie relé"""
        if self.active_high:
            GPIO.output(self.pin, GPIO.LOW)
        else:
            GPIO.output(self.pin, GPIO.HIGH)
        self.state = self.OFF
        print(f"Relé '{self.name}' VYPNUTÉ")
    
    def toggle(self):
        """Prepnúť stav relé"""
        if self.state == self.OFF:
            self.on()
        else:
            self.off()
    
    def is_on(self):
        """Vráti True ak je relé zapnuté"""
        return self.state == self.ON
    
    def get_state(self):
        """Vráti aktuálny stav ako reťazec"""
        return "ON" if self.is_on() else "OFF"
    
    def pulse(self, duration=1.0):
        """
        Krátky impulz - zapne a po danej dobe vypne
        
        Args:
            duration (float): Dĺžka impulzu v sekundách
        """
        self.on()
        time.sleep(duration)
        self.off()
    
    def __del__(self):
        """Čistenie pri ukončení"""
        try:
            self.off()
            GPIO.cleanup(self.pin)
        except:
            pass