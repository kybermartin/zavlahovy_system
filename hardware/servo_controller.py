# hardware/servo_controller.py
"""
Ovládanie servomotorov SG90 pre reguláciu ventilov.
"""

import RPi.GPIO as GPIO
import time

class ServoController:
    """Trieda pre ovládanie jedného serva SG90"""
    
    # Rozsah PWM pre SG90
    PWM_FREQ = 50  # 50 Hz = 20ms perióda
    DUTY_MIN = 2.5  # 0° (zatvorené)
    DUTY_MAX = 12.5  # 180° (otvorené)
    
    def __init__(self, pin, servo_id=1):
        """
        Inicializácia serva
        
        Args:
            pin (int): GPIO pin pre PWM (BCM)
            servo_id (int): Identifikátor serva (1-4)
        """
        self.pin = pin
        self.servo_id = servo_id
        self.current_position = 0  # 0-100%
        self.current_duty = self.DUTY_MIN
        
        # Nastavenie GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        # Inicializácia PWM
        self.pwm = GPIO.PWM(self.pin, self.PWM_FREQ)
        self.pwm.start(self.DUTY_MIN)
        
        print(f"Servo {servo_id} inicializované na pine {pin}")
        time.sleep(0.5)  # Počkáme na stabilizáciu
    
    def set_position(self, percent):
        """
        Nastavenie polohy serva (0-100%)
        0% = zatvorené, 100% = plne otvorené
        
        Args:
            percent (int/float): Požadovaná poloha 0-100
        """
        # Obmedzenie na rozsah 0-100
        percent = max(0, min(100, percent))
        
        # Prepočet percent na duty cycle
        duty = self.DUTY_MIN + (percent / 100.0) * (self.DUTY_MAX - self.DUTY_MIN)
        
        # Nastavenie PWM
        self.pwm.ChangeDutyCycle(duty)
        self.current_position = percent
        self.current_duty = duty
        
        print(f"Servo {self.servo_id} nastavené na {percent}% (duty={duty:.1f}%)")
        time.sleep(0.3)  # Počkáme na fyzický pohyb
    
    def open_valve(self, pressure=None):
        """
        Otvorenie ventilu s nastavením tlaku
        
        Args:
            pressure (int): Tlak v % (0-100), ak None použije 100%
        """
        if pressure is None:
            pressure = 100
        self.set_position(pressure)
        print(f"Ventil {self.servo_id} otvorený (tlak {pressure}%)")
    
    def close_valve(self):
        """Zatvorenie ventilu"""
        self.set_position(0)
        print(f"Ventil {self.servo_id} zatvorený")
    
    def get_position(self):
        """Vráti aktuálnu polohu v percentách"""
        return self.current_position
    
    def is_open(self):
        """Vráti True ak je ventil otvorený (viac ako 5%)"""
        return self.current_position > 5
    
    def stop(self):
        """Zastavenie PWM signálu"""
        self.pwm.ChangeDutyCycle(0)
    
    def __del__(self):
        """Čistenie pri ukončení"""
        try:
            self.close_valve()
            self.stop()
            self.pwm.stop()
            GPIO.cleanup(self.pin)
        except:
            pass