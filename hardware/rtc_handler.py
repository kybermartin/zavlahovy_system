# hardware/rtc_handler.py
"""
Obsluha RTC modulu DS3231.
Zabezpečuje čítanie času z RTC a nastavenie systémového času.
"""

import subprocess
import time
from datetime import datetime
import smbus2

class RTCHandler:
    """Trieda pre obsluhu RTC DS3231 cez I2C"""
    
    def __init__(self, i2c_addr=0x68):
        """
        Inicializácia RTC handlera
        
        Args:
            i2c_addr (int): I2C adresa DS3231 (štandardne 0x68)
        """
        self.addr = i2c_addr
        self.bus = smbus2.SMBus(1)  # I2C bus 1 na RPi
        self.initialized = self.check_connection()
        
        if not self.initialized:
            print("RTC modul nenájdený, používam systémový čas")
    
    def check_connection(self):
        """Overí, či RTC odpovedá na I2C zbernici"""
        try:
            self.bus.read_byte(self.addr)
            return True
        except:
            return False
    
    def read_time(self):
        """
        Načíta čas z RTC modulu
        
        Returns:
            datetime: Aktuálny čas z RTC alebo None pri chybe
        """
        if not self.initialized:
            return None
            
        try:
            # DS3231 ukladá čas v BCD formáte
            data = self.bus.read_i2c_block_data(self.addr, 0x00, 7)
            
            # Konverzia BCD na decimálne
            seconds = self._bcd_to_dec(data[0] & 0x7F)  # Maskujeme 7. bit
            minutes = self._bcd_to_dec(data[1])
            hours = self._bcd_to_dec(data[2] & 0x3F)    # Maskujeme 24h formát
            day = self._bcd_to_dec(data[3])
            date = self._bcd_to_dec(data[4])
            month = self._bcd_to_dec(data[5] & 0x1F)    # Maskujeme storočie
            year = self._bcd_to_dec(data[6]) + 2000
            
            return datetime(year, month, date, hours, minutes, seconds)
            
        except Exception as e:
            print(f"Chyba pri čítaní RTC: {e}")
            return None
    
    def write_time(self, dt=None):
        """
        Nastaví čas na RTC module
        
        Args:
            dt (datetime): Čas na nastavenie, ak None použije aktuálny
        """
        if not self.initialized:
            return False
            
        if dt is None:
            dt = datetime.now()
            
        try:
            # Konverzia decimálne na BCD
            data = [
                self._dec_to_bcd(dt.second),
                self._dec_to_bcd(dt.minute),
                self._dec_to_bcd(dt.hour),
                self._dec_to_bcd(dt.weekday() + 1),  # 1=pondelok, 7=nedeľa
                self._dec_to_bcd(dt.day),
                self._dec_to_bcd(dt.month),
                self._dec_to_bcd(dt.year - 2000)
            ]
            
            self.bus.write_i2c_block_data(self.addr, 0x00, data)
            return True
            
        except Exception as e:
            print(f"Chyba pri zápise do RTC: {e}")
            return False
    
    def set_system_time_from_rtc(self):
        """
        Nastaví systémový čas RPi podľa RTC modulu
        Vyžaduje root oprávnenia
        """
        rtc_time = self.read_time()
        if rtc_time:
            try:
                # Formát pre date command: MMDDhhmmYYYY
                time_str = rtc_time.strftime("%m%d%H%M%Y")
                subprocess.run(["sudo", "date", time_str], check=True)
                print(f"Systémový čas nastavený podľa RTC: {rtc_time}")
                return True
            except:
                print("Nepodarilo sa nastaviť systémový čas (treba root?)")
                return False
        return False
    
    def get_time_string(self):
        """
        Vráti aktuálny čas ako reťazec pre LCD
        
        Returns:
            str: Čas vo formáte "HH:MM"
        """
        now = datetime.now()
        return now.strftime("%H:%M")
    
    def get_datetime_string(self):
        """
        Vráti dátum a čas ako reťazec
        
        Returns:
            str: Dátum a čas vo formáte "DD.MM. HH:MM"
        """
        now = datetime.now()
        return now.strftime("%d.%m. %H:%M")
    
    def _bcd_to_dec(self, bcd):
        """Konverzia BCD na decimálne číslo"""
        return (bcd // 16 * 10) + (bcd % 16)
    
    def _dec_to_bcd(self, dec):
        """Konverzia decimálneho čísla na BCD"""
        return (dec // 10 * 16) + (dec % 10)
    
    def __del__(self):
        """Čistenie pri ukončení"""
        if hasattr(self, 'bus'):
            self.bus.close()