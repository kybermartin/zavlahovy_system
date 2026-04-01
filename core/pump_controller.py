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
    
    def __init__(self, relay_tlakove, relay_nasavacie, serva, level_sensors, lcd=None, rtc=None):
        """
        Inicializácia ovládača čerpadiel
        
        Args:
            relay_tlakove: RelayController pre tlakové čerpadlo
            relay_nasavacie: RelayController pre nasávacie čerpadlo
            serva: List ServoController objektov (4 ks)
            level_sensors: List LevelSensor objektov (2 ks)
            lcd: LCDHandler pre zobrazovanie stavu (voliteľné)
            rtc: RTCHandler pre prístup k reálnemu času (voliteľné)
        """
        self.tlakove = relay_tlakove
        self.nasavacie = relay_nasavacie
        self.serva = serva
        self.level_sensors = level_sensors
        self.lcd = lcd
        self.rtc = rtc  # Pridané pre prístup k RTC
        
        # Režimy (True = auto, False = manual)
        self.tlakove_auto_mode = True
        self.nasavacie_auto_mode = True
        
        # Aktuálne spustený interval
        self.active_interval = None
        
        # Ochrana pred suchým chodom
        self.dry_run_timer = None
        self.dry_run_active = False
        self.dry_run_delay = 30  # sekundy
        
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
        # Plynulé otvorenie ventilu (immediate=False = plynulý prechod)
        self.serva[okruh-1].open_valve(tlak, immediate=False)
        
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
        try:
            print("MANUÁLNE: Zastavujem tlakové čerpadlo")
            
            # Skontrolujeme či čerpadlo vôbec beží
            if not self.tlakove.is_on():
                print("Tlakové čerpadlo už bolo vypnuté")
                return True
            
            # Vypneme čerpadlo
            self.tlakove.off()
            
            # Zatvorenie všetkých ventilov (pre istotu)
            for i, servo in enumerate(self.serva):
                try:
                    if servo.is_open():
                        print(f"Zatváram ventil {i+1}")
                        servo.close_valve(immediate=False)
                except Exception as e:
                    print(f"Chyba pri zatváraní ventilu {i+1}: {e}")
            
            self.active_interval = None
            self._update_lcd()
            
            print("✓ Tlakové čerpadlo zastavené")
            return True
            
        except Exception as e:
            print(f"✗ Chyba pri zastavovaní tlakového čerpadla: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_irrigation(self, interval):
        """
        Automatické spustenie závlahy podľa intervalu s plynulým prechodom
        
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
        
        self.tlakove.on()
        time.sleep(1)  # Krátka pauza pre nábeh čerpadla
        
        # Plynulé otvorenie ventilu
        self.serva[okruh-1].open_valve(tlak, immediate=False)
        
        self.active_interval = interval
        self._update_lcd()
        
        return True

    def stop_irrigation(self):
        """Automatické zastavenie závlahy s plynulým zatváraním"""
        if not self.active_interval:
            return
        
        print(f"AUTO: Zastavujem interval - okruh {self.active_interval['okruh']}")
        
        # Plynulé zatvorenie všetkých ventilov
        for servo in self.serva:
            try:
                servo.close_valve(immediate=False)
            except Exception as e:
                print(f"Chyba pri zatváraní serva: {e}")
        
        # Počkáme na zatvorenie (približne čas prechodu)
        time.sleep(2)  # 2 sekundy na zatvorenie
        
        # Vypnutie čerpadla
        try:
            self.tlakove.off()
        except Exception as e:
            print(f"Chyba pri vypínaní čerpadla: {e}")
        
        self.active_interval = None
        self._update_lcd()
    
    def emergency_stop(self):
        """Núdzové zastavenie všetkého"""
        print("!!! NÚDZOVÉ ZASTAVENIE !!!")
        try:
            self.tlakove.off()
        except:
            pass
        try:
            self.nasavacie.off()
        except:
            pass
        
        for servo in self.serva:
            try:
                servo.close_valve(immediate=True)
            except:
                pass
        
        self.active_interval = None
        self.dry_run_active = False
        if self.dry_run_timer:
            try:
                self.dry_run_timer.cancel()
            except:
                pass
            self.dry_run_timer = None
    
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
            print("Čerpadlo je v AUTO móde, manuálne ovládanie blokované")
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
                time.sleep(1)  # Kontrola každú sekundu
            except Exception as e:
                print(f"Chyba v monitorovacej slučke: {e}")
                time.sleep(5)
    
    def _check_levels(self):
        """Kontrola hladinových senzorov a ovládanie nasávacieho čerpadla"""
        if not self.nasavacie_auto_mode:
            return
        
        if not self.level_sensors or len(self.level_sensors) < 2:
            return
        
        try:
            # Získanie stavov z plavákového spínača
            sensor = self.level_sensors[0]  # Hlavný senzor
            
            # Kontrola stavov
            if sensor.is_empty():
                # Nádrž prázdna - zapnúť čerpadlo
                if not self.nasavacie.is_on():
                    print("🌊 HLADINA: Nádrž prázdna, spúšťam čerpadlo")
                    self.nasavacie.on()
                    self._start_dry_run_timer()
                else:
                    self._cancel_dry_run_timer()
            
            elif sensor.is_full():
                # Nádrž plná - vypnúť čerpadlo
                if self.nasavacie.is_on():
                    print("🌊 HLADINA: Nádrž plná, zastavujem čerpadlo")
                    self.nasavacie.off()
                    self._cancel_dry_run_timer()
            
            elif sensor.is_normal():
                # Normálny stav - čerpadlo beží podľa potreby
                self._cancel_dry_run_timer()
            
            elif sensor.is_error():
                # Chybový stav - núdzovo vypnúť
                print("⚠️ HLADINA: Chybový stav! Vypínam čerpadlo")
                if self.nasavacie.is_on():
                    self.nasavacie.off()
                    
        except Exception as e:
            print(f"Chyba pri čítaní senzorov: {e}")
        
    def _start_dry_run_timer(self):
        """Spustenie časovača pre ochranu pred suchým chodom"""
        self._cancel_dry_run_timer()
        
        self.dry_run_timer = threading.Timer(self.dry_run_delay, self._dry_run_protection)
        self.dry_run_timer.daemon = True
        self.dry_run_timer.start()
        print(f"Ochrana pred suchým chodom aktivovaná ({self.dry_run_delay}s)")
    
    def _cancel_dry_run_timer(self):
        """Zrušenie časovača pre suchý chod"""
        if self.dry_run_timer:
            try:
                self.dry_run_timer.cancel()
            except:
                pass
            self.dry_run_timer = None
    
    def _dry_run_protection(self):
        """Ochrana pred suchým chodom - vypne čerpadlo"""
        print("!!! OCHRANA: Suchý chod detekovaný, vypínam nasávacie čerpadlo !!!")
        try:
            self.nasavacie.off()
        except:
            pass
        self.dry_run_active = True
        
        # Zobrazenie na LCD
        if self.lcd:
            self.lcd.show_message("POZOR!", "Suchy chod!")
    
    def set_dry_run_delay(self, seconds):
        """
        Nastavenie oneskorenia pre ochranu pred suchým chodom
        
        Args:
            seconds (int): Počet sekúnd
        """
        self.dry_run_delay = max(5, min(120, seconds))
        print(f"Ochrana pred suchým chodom nastavená na {self.dry_run_delay}s")
    
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
        try:
            is_on = self.nasavacie.is_on()
        except:
            is_on = False
        
        if is_on:
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
            try:
                states.append({
                    'okruh': i+1,
                    'pozicia': servo.get_position(),
                    'otvoreny': servo.is_open()
                })
            except:
                states.append({
                    'okruh': i+1,
                    'pozicia': 0,
                    'otvoreny': False
                })
        return states
    
    def _update_lcd(self):
        """Aktualizácia LCD displeja"""
        if self.lcd:
            try:
                tlakove = self.get_tlakove_status()
                nasavacie = self.get_nasavacie_status()
                
                # Použijeme lokálny čas z RTC (ak je k dispozícii)
                if hasattr(self, 'rtc') and self.rtc and self.rtc.initialized:
                    cas = self.rtc.get_time_string()
                else:
                    cas = datetime.now().strftime("%H:%M")
                
                if self.active_interval:
                    row1 = f"OK{self.active_interval['okruh']}:{self.active_interval['tlak']}%"
                    row2 = f"T:{tlakove['text']} N:{nasavacie['text']}"
                else:
                    row1 = f"{cas} ZAVLAHA"
                    row2 = f"T:{tlakove['text']} N:{nasavacie['text']}"
                
                self.lcd.show_message(row1[:16], row2[:16])
            except Exception as e:
                print(f"Chyba pri aktualizácii LCD: {e}")
    
    # ============================================
    # LEVEL SENSOR INFO (pre plavákový spínač)
    # ============================================
    
    def get_level_info(self):
        """
        Získa informácie o hladine z plavákového spínača
        
        Returns:
            dict: Informácie o hladine
        """
        if not self.level_sensors or len(self.level_sensors) < 2:
            return {
                'available': False,
                'height': 0,
                'level_count': 0,
                'rising': False,
                'falling': False,
                'empty': True,
                'full': False
            }
        
        try:
            # Skúsime získať výšku z plavákového spínača
            sensor = self.level_sensors[0]
            
            # Kontrola či má plavákový spínač potrebné metódy
            if hasattr(sensor, 'get_current_height'):
                height = sensor.get_current_height()
                level_count = sensor.get_level_count()
                rising = sensor.is_rising()
                falling = sensor.is_falling()
                empty = sensor.is_empty()
                full = sensor.is_full() if hasattr(sensor, 'is_full') else (height >= 100)
            else:
                # Fallback na jednoduché senzory
                spodny_mokry = sensor.is_wet()
                horny_mokry = self.level_sensors[1].is_wet()
                
                if not spodny_mokry and not horny_mokry:
                    height = 0
                    level_count = 0
                    empty = True
                    full = False
                elif spodny_mokry and horny_mokry:
                    height = 100
                    level_count = 10
                    empty = False
                    full = True
                elif spodny_mokry and not horny_mokry:
                    height = 50
                    level_count = 5
                    empty = False
                    full = False
                else:
                    height = 0
                    level_count = 0
                    empty = True
                    full = False
                
                rising = False
                falling = False
            
            return {
                'available': True,
                'height': height,
                'level_count': level_count,
                'rising': rising,
                'falling': falling,
                'empty': empty,
                'full': full
            }
            
        except Exception as e:
            print(f"Chyba pri získavaní informácií o hladine: {e}")
            return {
                'available': False,
                'height': 0,
                'level_count': 0,
                'rising': False,
                'falling': False,
                'empty': True,
                'full': False
            }