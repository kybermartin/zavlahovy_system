# core/scheduler.py
"""
Hlavný plánovač úloh.
Beží ako samostatné vlákno a kontroluje časové intervaly.
"""

import threading
import time
from datetime import datetime

class Scheduler(threading.Thread):
    """Plánovač pre automatické spúšťanie závlahy"""
    
    def __init__(self, irrigation_plan, pump_controller, lcd=None):
        """
        Inicializácia plánovača
        
        Args:
            irrigation_plan: IrrigationPlan objekt
            pump_controller: PumpController objekt
            lcd: LCDHandler pre zobrazovanie (voliteľné)
        """
        super().__init__()
        self.irrigation_plan = irrigation_plan
        self.pump = pump_controller
        self.lcd = lcd
        self.running = True
        self.last_check_minute = -1
        self.daemon = True
        
        print("Scheduler inicializovaný")
    
    def run(self):
        """Hlavná slučka plánovača"""
        print("Scheduler spustený")
        
        while self.running:
            try:
                now = datetime.now()
                
                # Kontrola každú celú minútu
                if now.second == 0 and now.minute != self.last_check_minute:
                    self._check_schedule(now)
                    self.last_check_minute = now.minute
                
                # Krátky spánok pre zníženie záťaže CPU
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Chyba v scheduleri: {e}")
                time.sleep(5)
        
        print("Scheduler ukončený")
    
    def _check_schedule(self, now):
        """
        Kontrola plánu a spustenie/zastavenie podľa potreby
        
        Args:
            now (datetime): Aktuálny čas
        """
        current_interval = self.irrigation_plan.get_active_interval(now)
        
        # Logovanie pre debug
        if current_interval:
            print(f"CHECK: Nájdený aktívny interval: {current_interval}")
        else:
            # Pre tichý režim odkomentovať
            # print(f"CHECK: Žiadny aktívny interval o {now.strftime('%H:%M')}")
            pass
        
        # Prípad 1: Mal by bežať interval a nebeží žiadny
        if current_interval and not self.pump.active_interval:
            print(f"PLÁN: Štartujem interval {current_interval['id']}")
            self.pump.start_irrigation(current_interval)
            
            if self.lcd:
                self.lcd.show_message(
                    f"START: OK{current_interval['okruh']}",
                    f"{current_interval['tlak']}% {current_interval['start']}"
                )
        
        # Prípad 2: Nemal by bežať a beží nejaký
        elif not current_interval and self.pump.active_interval:
            # Kontrola či to nie je manuálne spustené
            if 'manual' not in self.pump.active_interval:
                print(f"PLÁN: Zastavujem interval {self.pump.active_interval['id']}")
                self.pump.stop_irrigation()
                
                if self.lcd:
                    self.lcd.show_message("ZAVLAHA", "UKONCENA")
        
        # Prípad 3: Beží a mal by bežať, ale možno iný interval
        elif current_interval and self.pump.active_interval:
            # Ak beží iný interval ako by mal, prepneme
            if ('id' in current_interval and 'id' in self.pump.active_interval and 
                current_interval['id'] != self.pump.active_interval.get('id')):
                
                print(f"PLÁN: Prepínam z intervalu {self.pump.active_interval['id']} na {current_interval['id']}")
                self.pump.stop_irrigation()
                time.sleep(2)  # Krátka pauza medzi intervalmi
                self.pump.start_irrigation(current_interval)
    
    def stop(self):
        """Zastavenie plánovača"""
        self.running = False
        print("Scheduler dostal príkaz na zastavenie")
    
    def force_check(self):
        """Vynútená okamžitá kontrola plánu"""
        self._check_schedule(datetime.now())