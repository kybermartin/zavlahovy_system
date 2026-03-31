# core/pump_controller.py
"""
Hlavný ovládač čerpadiel a ventilov.
Obsahuje logiku pre manuálny aj automatický režim.
"""

import time
import threading
from datetime import datetime

class PumpController:
    """Trieda pre komplexné ovládanie čerpadiel a ventilov"""
    
    def __init__(self, relay_tlakove, relay_nasavacie, serva, level_sensors, lcd=None):
        """
        Inicializácia ovládača čerpadiel
        
        Args:
            relay_tlakove: RelayController pre tlakové čerpadlo
            relay_nasavacie: RelayController pre nasávacie čerpadlo
            serva: List ServoController objektov (4 ks)
            level_sensors: List LevelSensor objektov (2 ks)
            lcd: LCDHandler pre zobrazovanie stavu (voliteľné)
        """
        self.tlakove = relay_tlakove
        self.nasavacie = relay_nasavacie
        self.serva = serva
        self.level_sensors = level_sensors
        self.lcd = lcd
        
        # Režimy (True = auto, False = manual)
        self.tlakove_auto_mode = True
        self.nasavacie_auto_mode = True
        
        # Aktuálne spustený interval
        self.active_interval = None
        
        # Ochrana pred suchým chodom
        self.dry_run_timer = None
        self.dry_run_active = False
        
        # Thread pre monitorovanie nasávacieho čerpadla
        self.monitor_thread = None
        self.monitoring = False
        
        print("PumpController inicializovaný")
    
    # ============================================
    # TLAKOVÉ ČERPADLO (ZÁVLAHA)
    # ============================================
    
    def set_tlakove_mode(self, auto_mode):
        """
        Nastavenie režimu pre tlakové čerpadlo
        
        Args:
            auto_mode (bool): True = auto, False = manual
        """
        self.tlakove_auto_mode = auto_mode
        print(f"Tlakové čerpadlo prepnuté na {'AUTO' if auto_mode else 'MANUAL'} mód")
        
        # Ak prepíname na manuálny, zastavíme automatiku
        if not auto_mode and self.active_interval:
            self.stop_irrigation()
    
    def manual_tlakove_start(self, okruh, tlak):
        """
        Manuálne spustenie tlakového čerpadla
        
        Args:
            okruh (int): Číslo okruhu (1-4)
            tlak (int): Tlak v percentách (0-100)
        
        Returns:
            bool: True ak bolo spustené
        """
        # Kontrola platnosti okruhu
        if okruh < 1 or okruh > 4:
            print(f"Chyba: Neplatný okruh {okruh}")
            return False
        
        # Ak beží automatika, zastavíme ju
        if self.active_interval:
            self.stop_irrigation()
        
        # Spustenie
        print(f"MANUÁLNE: Spúšťam okruh {okruh} s tlakom {tlak}%")
        self.tlakove.on()
        self.serva[okruh-1].open_valve(tlak)
        
        # Vytvoríme fiktívny interval pre LCD
        self.active_interval = {
            'okruh': okruh,
            'tlak': tlak,
            'manual': True
        }
        
        self._update_lcd()
        return True
    
    def manual_tlakove_stop(self):
        """Manuálne zastavenie tlakového čerpadla"""
        print("MANUÁLNE: Zastavujem tlakové čerpadlo")
        self.tlakove.off()
        
        # Zatvorenie všetkých ventilov
        for servo in self.serva:
            servo.close_valve()
        
        self.active_interval = None
        self._update_lcd()
    
    def start_irrigation(self, interval):
        """
        Automatické spustenie závlahy podľa intervalu
        
        Args:
            interval (dict): Interval s kľúčmi 'okruh', 'tlak'
        
        Returns:
            bool: True ak bolo spustené
        """
        if not self.tlakove_auto_mode:
            print("Auto mód je vypnutý, nespúšťam")
            return False
        
        if self.active_interval:
            print("Už beží iný interval")
            return False
        
        okruh = interval['okruh']
        tlak = interval['tlak']
        
        print(f"AUTO: Spúšťam interval - okruh {okruh}, tlak {tlak}%")
        
        # Zapneme čerpadlo
        self.tlakove.on()
        time.sleep(1)  # Krátka pauza pre nábeh čerpadla
        
        # Otvoríme ventil
        self.serva[okruh-1].open_valve(tlak)
        
        self.active_interval = interval
        self._update_lcd()
        
        return True
    
    def stop_irrigation(self):
        """Automatické zastavenie závlahy"""
        if not self.active_interval:
            return
        
        print(f"AUTO: Zastavujem interval - okruh {self.active_interval['okruh']}")
        
        # Zatvorenie ventilov
        for servo in self.serva:
            servo.close_valve()
        time.sleep(1)  # Počkáme na zatvorenie
        
        # Vypnutie čerpadla
        self.tlakove.off()
        
        self.active_interval = None
        self._update_lcd()
    
    def emergency_stop(self):
        """Núdzové zastavenie všetkého"""
        print("!!! NÚDZOVÉ ZASTAVENIE !!!")
        self.tlakove.off()
        self.nasavacie.off()
        
        for servo in self.serva:
            try:
                servo.close_valve()
            except:
                pass
        
        self.active_interval = None
        self.dry_run_active = False
        if self.dry_run_timer:
            self.dry_run_timer.cancel()
    
    # ============================================
    # NASAVACIE ČERPADLO
    # ============================================
    
    def set_nasavacie_mode(self, auto_mode):
        """
        Nastavenie režimu pre nasávacie čerpadlo
        
        Args:
            auto_mode (bool): True = auto, False = manual
        """
        self.nasavacie_auto_mode = auto_mode
        print(f"Nasávacie čerpadlo prepnuté na {'AUTO' if auto_mode else 'MANUAL'} mód")
        
        if auto_mode:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def manual_nasavacie_start(self):
        """Manuálne spustenie nasávacieho čerpadla"""
        if self.nasavacie_auto_mode:
            print("Čerpadlo je v AUTO móde, manuálne ovládanie blokované")
            return False
        
        print("MANUÁLNE: Spúšťam nasávacie čerpadlo")
        self.nasavacie.on()
        return True
    
    def manual_nasavacie_stop(self):
        """Manuálne zastavenie nasávacieho čerpadla"""
        if self.nasavacie_auto_mode:
            return False
        
        print("MANUÁLNE: Zastavujem nasávacie čerpadlo")
        self.nasavacie.off()
        return True
    
    def start_monitoring(self):
        """Spustenie monitorovania hladín v samostatnom vlákne"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("Monitorovanie hladín spustené")
    
    def stop_monitoring(self):
        """Zastavenie monitorovania hladín"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("Monitorovanie hladín zastavené")
    
    def _monitor_loop(self):
        """Hlavná slučka pre monitorovanie hladín"""
        while self.monitoring and self.nasavacie_auto_mode:
            try:
                self._check_levels()
                time.sleep(2)  # Kontrola každé 2 sekundy
            except Exception as e:
                print(f"Chyba v monitorovacej slučke: {e}")
                time.sleep(5)
    
    def _check_levels(self):
        """Kontrola hladinových senzorov a ovládanie nasávacieho čerpadla"""
        if not self.nasavacie_auto_mode:
            return
        
        # Čítanie senzorov (s ošetrením zákmitov)
        spodny_mokry = self.level_sensors[0].read_with_debounce()
        horny_mokry = self.level_sensors[1].read_with_debounce()
        
        # Logika pre nasávacie čerpadlo
        if not spodny_mokry and not horny_mokry:
            # Spodný suchý (málo vody), horný suchý (nádrž nie je plná)
            if not self.nasavacie.is_on():
                print("HLADINA: Spúšťam nasávacie čerpadlo (nízka hladina)")
                self.nasavacie.on()
                
                # Spustíme timer pre ochranu pred suchým chodom
                self._start_dry_run_timer()
        
        elif horny_mokry:
            # Horný senzor mokrý = nádrž je plná
            if self.nasavacie.is_on():
                print("HLADINA: Zastavujem nasávacie čerpadlo (nádrž plná)")
                self.nasavacie.off()
                self._cancel_dry_run_timer()
        
        elif spodny_mokry and not horny_mokry:
            # Spodný mokrý, horný suchý = čerpáme, ale ešte nie je plno
            # Normálny stav, resetujeme suchý chod timer
            self._cancel_dry_run_timer()
    
    def _start_dry_run_timer(self):
        """Spustenie časovača pre ochranu pred suchým chodom"""
        self._cancel_dry_run_timer()
        
        # 30 sekúnd suchého chodu = vypneme
        self.dry_run_timer = threading.Timer(30.0, self._dry_run_protection)
        self.dry_run_timer.daemon = True
        self.dry_run_timer.start()
        print("Ochrana pred suchým chodom aktivovaná (30s)")
    
    def _cancel_dry_run_timer(self):
        """Zrušenie časovača pre suchý chod"""
        if self.dry_run_timer:
            self.dry_run_timer.cancel()
            self.dry_run_timer = None
    
    def _dry_run_protection(self):
        """Ochrana pred suchým chodom - vypne čerpadlo"""
        print("!!! OCHRANA: Suchý chod detekovaný, vypínam nasávacie čerpadlo !!!")
        self.nasavacie.off()
        self.dry_run_active = True
        
        # Zobrazenie na LCD
        if self.lcd:
            self.lcd.show_message("POZOR!", "Suchy chod!")
    
    # ============================================
    # STAVOVÉ INFORMÁCIE
    # ============================================
    
    def get_tlakove_status(self):
        """Vráti stav tlakového čerpadla"""
        if self.active_interval:
            if 'manual' in self.active_interval:
                return {
                    'mode': 'MANUAL',
                    'state': 'BEZI',
                    'text': 'MAN.BEZI',
                    'okruh': self.active_interval['okruh'],
                    'tlak': self.active_interval['tlak']
                }
            else:
                return {
                    'mode': 'AUTO',
                    'state': 'BEZI',
                    'text': 'AUT.BEZI',
                    'okruh': self.active_interval['okruh'],
                    'tlak': self.active_interval['tlak']
                }
        else:
            return {
                'mode': 'AUTO' if self.tlakove_auto_mode else 'MANUAL',
                'state': 'VYP',
                'text': 'AUT.VYP' if self.tlakove_auto_mode else 'MAN.VYP'
            }
    
    def get_nasavacie_status(self):
        """Vráti stav nasávacieho čerpadla"""
        if self.nasavacie.is_on():
            return {
                'mode': 'AUTO' if self.nasavacie_auto_mode else 'MANUAL',
                'state': 'BEZI',
                'text': 'AUT.BEZI' if self.nasavacie_auto_mode else 'MAN.BEZI'
            }
        else:
            return {
                'mode': 'AUTO' if self.nasavacie_auto_mode else 'MANUAL',
                'state': 'VYP',
                'text': 'AUT.VYP' if self.nasavacie_auto_mode else 'MAN.VYP'
            }
    
    def get_valve_states(self):
        """Vráti stavy všetkých ventilov"""
        states = []
        for i, servo in enumerate(self.serva):
            states.append({
                'okruh': i+1,
                'pozicia': servo.get_position(),
                'otvoreny': servo.is_open()
            })
        return states
    
    def _update_lcd(self):
        """Aktualizácia LCD displeja"""
        if self.lcd:
            tlakove = self.get_tlakove_status()
            nasavacie = self.get_nasavacie_status()
            
            if self.active_interval:
                row1 = f"OK{self.active_interval['okruh']}:{self.active_interval['tlak']}%"
                row2 = f"T:{tlakove['text']} N:{nasavacie['text']}"
            else:
                from datetime import datetime
                cas = datetime.now().strftime("%H:%M")
                row1 = f"{cas} ZAVLAHA"
                row2 = f"T:{tlakove['text']} N:{nasavacie['text']}"
            
            self.lcd.show_message(row1, row2)