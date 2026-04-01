# main.py
"""
Hlavný spúšťací súbor pre zavlažovací systém.
Inicializuje všetky komponenty a spúšťa vlákna pre plánovač a web server.
"""
import RPi.GPIO as GPIO
import threading
import time
import signal
import sys
import os

# Pridanie cesty pre import modulov
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hardware.rtc_handler import RTCHandler
from hardware.lcd_handler import LCDHandler
from hardware.relay_controller import RelayController
from hardware.servo_controller import ServoController
from hardware.level_sensor import LevelSensor
from core.pump_controller import PumpController
from core.irrigation_plan import IrrigationPlan
from core.scheduler import Scheduler
from web.app import app as web_app
import config

class IrrigationSystem:
    def __init__(self):
        print("=" * 50)
        print("ZAVLAHOVACÍ SYSTÉM - ŠTART")
        print("=" * 50)
        
        
        
        # Vypnutie warningov
        GPIO.setwarnings(False)
        
        # Inicializácia hardvéru
        self.init_hardware()
        
        # Inicializácia logických komponentov
        self.init_core()
        
        # Stav systému
        self.running = True
        self.web_thread = None
        self.scheduler_thread = None
        
    def init_hardware(self):
        """Inicializácia všetkých hardvérových komponentov"""
        try:
            # RTC modul (používa sysfs / hwclock)
            self.rtc = RTCHandler()
            if self.rtc.initialized:
                self.rtc.set_system_time_from_rtc()
                print("✓ Systémový čas nastavený podľa RTC")
            else:
                print("⚠️ RTC modul nedostupný, používam softvérový čas")
            
            # LCD displej
            self.lcd = LCDHandler()
            self.lcd.init_display()
            self.lcd.show_message("System start...", "Zavlaha system")
            print("✓ LCD inicializované")
            
            # Relé pre čerpadlá
            self.relay_tlakove = RelayController(config.RELAY_TLAKOVE_PIN)
            self.relay_nasavacie = RelayController(config.RELAY_NASAVACIE_PIN)
            print("✓ Relé moduly inicializované")
            
            # Servá pre ventily
            self.serva = []
            transition_time = 3.0  # 3 sekundy na celý rozsah
            for i, pin in enumerate(config.SERVO_PINS):
                servo = ServoController(pin, i+1, transition_time=transition_time)
                self.serva.append(servo)
            print(f"✓ Servá inicializované (čas prechodu: {transition_time}s)")
            
            # Hladinové senzory
            self.level_sensor = LevelSensor(
                pin_min=config.LEVEL_SENSOR_MIN_PIN,   # GPIO pre minimálnu hladinu
                pin_max=config.LEVEL_SENSOR_MAX_PIN,   # GPIO pre maximálnu hladinu
                name="hladina",
                debounce_time=0.1
            )
            # Pre kompatibilitu s pump_controller (očakáva list)
            self.level_sensors = [self.level_sensor]
            print("✓ Hladinové senzory inicializované")
            
        except Exception as e:
            print(f"✗ Chyba pri inicializácii hardvéru: {e}")
            sys.exit(1)
    
    def init_core(self):
        """Inicializácia logických komponentov"""
        try:
            # Plán zavlažovania
            self.irrigation_plan = IrrigationPlan(config.SCHEDULE_FILE)
            print("✓ Plán zavlažovania inicializovaný")
            
            # Hlavný ovládač čerpadiel
            self.pump_controller = PumpController(
                self.relay_tlakove,
                self.relay_nasavacie,
                self.serva,
                self.level_sensors,
                self.lcd
            )
            print("✓ Ovládač čerpadiel inicializovaný")
            
            # Plánovač
            self.scheduler = Scheduler(
                self.irrigation_plan,
                self.pump_controller,
                self.lcd
            )
            print("✓ Plánovač inicializovaný")
            
        except Exception as e:
            print(f"✗ Chyba pri inicializácii logiky: {e}")
            sys.exit(1)
    
    def start_web_server(self):
        """Spustenie Flask web serveru v samostatnom vlákne"""
        try:
            """
            web_app.config.update(
                PUMP_CONTROLLER=self.pump_controller,
                IRRIGATION_PLAN=self.irrigation_plan
            )
            """
            from web.app import app as web_app
            
            # Nastavenie globálnych premenných
            import web.app as web_module
            web_module.pump_controller = self.pump_controller
            web_module.irrigation_plan = self.irrigation_plan
           
            
            # Spustenie Flask serveru
            web_app.run(
                host=config.WEB_HOST,
                port=config.WEB_PORT,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            print(f"✗ Chyba pri spúšťaní web servera: {e}")
    
    def run(self):
        """Spustenie hlavnej slučky systému"""
        # Spustenie web servera vo vlákne
        self.web_thread = threading.Thread(target=self.start_web_server)
        self.web_thread.daemon = True
        self.web_thread.start()
        print(f"✓ Web server spustený na http://{config.WEB_HOST}:{config.WEB_PORT}")
        
        # Spustenie plánovača vo vlákne
        self.scheduler_thread = threading.Thread(target=self.scheduler.run)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        print("✓ Plánovač spustený")
        
        # Hlavná slučka pre aktualizáciu LCD
        self.main_loop()
    
    def main_loop(self):
        """Hlavná slučka programu - aktualizácia LCD a obsluha signálov"""
        try:
            while self.running:
                # Aktualizácia LCD displeja (každé 2 sekundy)
                self.update_lcd_display()
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 50)
            print("UKONČOVANIE SYSTÉMU")
            self.cleanup()
    
    def update_lcd_display(self):
        """Aktualizácia informácií na LCD displeji"""
        # Získanie aktuálnych stavov
        tlakove_stav = self.pump_controller.get_tlakove_status()
        nasavacie_stav = self.pump_controller.get_nasavacie_status()
        active_interval = self.pump_controller.active_interval
        
        # Formátovanie pre LCD (2 riadky po 16 znakov)
        if active_interval:
            # Zobrazujeme bežiaci interval
            row1 = f"{self.rtc.get_time_string()} OK{active_interval['okruh']}"
            row2 = f"T:{tlakove_stav['text']} N:{nasavacie_stav['text']}"
        else:
            # Zobrazujeme čakací režim
            row1 = f"{self.rtc.get_time_string()} ZAVLAHA"
            row2 = f"T:{tlakove_stav['text']} N:{nasavacie_stav['text']}"
        
        self.lcd.show_message(row1, row2)
    
    def cleanup(self):
        """Vyčistenie a bezpečné ukončenie"""
        print("Prebieha čistenie...")
        
        # Zastavenie všetkých čerpadiel a zatvorenie ventilov
        self.pump_controller.emergency_stop()
        
        # Vyčistenie LCD
        self.lcd.clear()
        self.lcd.show_message("System stopped", "Dovidenia")
        
        # VYČISTENIE VŠETKÝCH PINOV 
        try:
            GPIO.cleanup()
            print("✓ GPIO piny vyčistené")
        except:
            print(f"Poznámka pri čistení GPIO: {e}")
        
        # Ukončenie
        self.running = False
        print("Systém ukončený")
        sys.exit(0)

if __name__ == "__main__":
    # Spustenie systému
    system = IrrigationSystem()
    system.run()
    