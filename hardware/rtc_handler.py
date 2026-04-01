# hardware/rtc_handler.py
"""
Obsluha RTC modulu DS3231 cez sysfs (systémový súborový systém).
Používa rovnaký mechanizmus ako príkaz hwclock.
"""

import subprocess
import time
from datetime import datetime, timedelta
import os
import threading

class RTCHandler:
    """Trieda pre obsluhu RTC DS3231 cez sysfs"""
    
    def __init__(self):
        """
        Inicializácia RTC handlera
        """
        self.initialized = False
        self.rtc_device = None
        self._lock = threading.Lock()
        
        print("\n🔍 Kontrola RTC modulu DS3231...")
        
        # 1. Nájdenie RTC zariadenia
        self.rtc_device = self._find_rtc_device()
        
        if self.rtc_device:
            self.initialized = True
            print(f"   ✅ RTC modul nájdený: {self.rtc_device}")
            
            # Zobrazenie času pre kontrolu
            rtc_time = self.read_rtc_local()
            if rtc_time:
                print(f"   🕐 Čas na RTC: {rtc_time.strftime('%d.%m.%Y %H:%M:%S')}")
        else:
            print("   ❌ RTC modul nebol nájdený")
            print("   Skontrolujte: sudo hwclock -r")
    
    def _find_rtc_device(self):
        """
        Nájde prvý dostupný RTC device
        
        Returns:
            str: Cesta k RTC device (napr. /dev/rtc0) alebo None
        """
        # Skúsime /dev/rtc0, /dev/rtc1, atď.
        for i in range(0, 10):
            rtc_path = f"/dev/rtc{i}"
            if os.path.exists(rtc_path):
                # Skúsime prečítať čas z tohto RTC
                try:
                    result = subprocess.run(['sudo', 'hwclock', '-r', '-f', rtc_path],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return rtc_path
                except:
                    pass
        
        # Skúsime /sys/class/rtc/rtc0
        if os.path.exists('/sys/class/rtc/rtc0'):
            return '/dev/rtc0'
        
        # Skúsime zistiť cez hwclock
        try:
            result = subprocess.run(['sudo', 'hwclock', '-r'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # hwclock funguje, použijeme /dev/rtc0
                return '/dev/rtc0'
        except:
            pass
        
        return None
    
    def _get_utc_offset(self):
        """
        Získa aktuálny UTC offset v hodinách
        
        Returns:
            int: Počet hodín offsetu (1 pre zimný čas, 2 pre letný)
        """
        # Zistíme či je letný čas
        is_dst = time.localtime().tm_isdst
        
        # Pre strednú Európu: UTC+1 (zima) alebo UTC+2 (leto)
        return 2 if is_dst else 1
    
    def _utc_to_local(self, utc_dt):
        """
        Konverzia UTC datetime na lokálny datetime
        
        Args:
            utc_dt (datetime): UTC čas
        
        Returns:
            datetime: Lokálny čas
        """
        if utc_dt is None:
            return None
        offset = self._get_utc_offset()
        return utc_dt + timedelta(hours=offset)
    
    def _local_to_utc(self, local_dt):
        """
        Konverzia lokálneho datetime na UTC
        
        Args:
            local_dt (datetime): Lokálny čas
        
        Returns:
            datetime: UTC čas
        """
        if local_dt is None:
            return None
        offset = self._get_utc_offset()
        return local_dt - timedelta(hours=offset)
    
    def read_rtc_utc(self):
        """
        Prečíta čas z RTC modulu (UTC) pomocou hwclock
        
        Returns:
            datetime: Aktuálny UTC čas z RTC alebo None pri chybe
        """
        if not self.initialized:
            return None
        
        try:
            # Použijeme hwclock na čítanie času v UTC
            if self.rtc_device:
                cmd = ['sudo', 'hwclock', '-r', '-u', '-f', self.rtc_device]
            else:
                cmd = ['sudo', 'hwclock', '-r', '-u']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Výstup je v tvare: "2026-03-30 15:30:00.123456+00:00"
                time_str = result.stdout.strip().split()[0] + ' ' + result.stdout.strip().split()[1]
                # Odstránime milisekundy
                time_str = time_str.split('.')[0]
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            else:
                print(f"Chyba hwclock: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Chyba pri čítaní RTC: {e}")
            return None
    
    def read_rtc_local(self):
        """
        Prečíta čas z RTC a prevedie na lokálny čas
        
        Returns:
            datetime: Aktuálny lokálny čas
        """
        utc = self.read_rtc_utc()
        return self._utc_to_local(utc)
    
    def write_rtc_utc(self, utc_dt):
        """
        Nastaví čas na RTC module (UTC) pomocou hwclock
        
        Args:
            utc_dt (datetime): UTC čas na nastavenie
        
        Returns:
            bool: True ak úspešné
        """
        if not self.initialized:
            return False
        
        try:
            # Formát pre hwclock: "YYYY-MM-DD HH:MM:SS"
            time_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.rtc_device:
                cmd = ['sudo', 'hwclock', '-w', '-u', '--date', time_str, '-f', self.rtc_device]
            else:
                cmd = ['sudo', 'hwclock', '-w', '-u', '--date', time_str]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"✓ RTC nastavený na UTC: {time_str}")
                return True
            else:
                print(f"Chyba pri zápise do RTC: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Chyba pri zápise do RTC: {e}")
            return False
    
    def write_rtc_local(self, local_dt):
        """
        Nastaví čas na RTC module (lokálny čas sa prevedie na UTC)
        
        Args:
            local_dt (datetime): Lokálny čas na nastavenie
        
        Returns:
            bool: True ak úspešné
        """
        utc = self._local_to_utc(local_dt)
        return self.write_rtc_utc(utc)
    
    def set_system_time_from_rtc(self):
        """
        Nastaví systémový čas RPi podľa RTC modulu.
        Používa hwclock --hctosys pre nastavenie systémového času.
        """
        if not self.initialized:
            return False
        
        try:
            if self.rtc_device:
                cmd = ['sudo', 'hwclock', '-s', '-f', self.rtc_device]
            else:
                cmd = ['sudo', 'hwclock', '-s']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"✓ Systémový čas nastavený podľa RTC")
                return True
            else:
                print(f"Chyba pri nastavovaní systémového času: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Chyba pri nastavovaní systémového času: {e}")
            return False
    
    def sync_rtc_from_system(self):
        """
        Synchronizuje RTC podľa systémového času
        Používa hwclock --systohc
        """
        now = datetime.now()
        return self.write_rtc_local(now)
    
    def get_time_string(self):
        """
        Vráti aktuálny lokálny čas ako reťazec pre LCD
        
        Returns:
            str: Čas vo formáte "HH:MM"
        """
        local_time = self.read_rtc_local()
        if local_time:
            return local_time.strftime("%H:%M")
        
        # Fallback na systémový čas
        return datetime.now().strftime("%H:%M")
    
    def get_datetime_string(self):
        """
        Vráti lokálny dátum a čas ako reťazec
        
        Returns:
            str: Dátum a čas vo formáte "DD.MM. HH:MM"
        """
        local_time = self.read_rtc_local()
        if local_time:
            return local_time.strftime("%d.%m. %H:%M")
        
        # Fallback na systémový čas
        return datetime.now().strftime("%d.%m. %H:%M")
    
    def get_full_datetime_string(self):
        """
        Vráti kompletný dátum a čas
        
        Returns:
            str: Dátum a čas vo formáte "DD.MM.YYYY HH:MM:SS"
        """
        local_time = self.read_rtc_local()
        if local_time:
            return local_time.strftime("%d.%m.%Y %H:%M:%S")
        return datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    def get_timezone_info(self):
        """
        Získa informácie o časovej zóne
        
        Returns:
            dict: Informácie o časovej zóne
        """
        import time
        return {
            'timezone': time.tzname,
            'is_dst': time.localtime().tm_isdst,
            'utc_offset': time.timezone // -3600,
            'local_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'utc_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_status(self):
        """
        Získa informácie o RTC pre debug
        
        Returns:
            dict: Informácie o RTC
        """
        utc = self.read_rtc_utc()
        local = self.read_rtc_local()
        system = datetime.now()
        
        return {
            'connected': self.initialized,
            'device': self.rtc_device,
            'utc': utc.strftime('%Y-%m-%d %H:%M:%S') if utc else None,
            'local': local.strftime('%Y-%m-%d %H:%M:%S') if local else None,
            'system': system.strftime('%Y-%m-%d %H:%M:%S'),
            'utc_offset': self._get_utc_offset(),
            'timezone': time.tzname
        }
    
    def print_status(self):
        """Vytlačí stav RTC"""
        print("\n" + "=" * 50)
        print("RTC DS3231 - Stav (cez sysfs)")
        print("=" * 50)
        
        if not self.initialized:
            print("❌ RTC modul nie je dostupný")
            print("\nRiešenie:")
            print("1. Skontrolujte či funguje: sudo hwclock -r")
            print("2. Skontrolujte zapojenie")
            return
        
        print(f"Zariadenie:    {self.rtc_device}")
        
        utc = self.read_rtc_utc()
        local = self.read_rtc_local()
        
        print(f"Čas (UTC):     {utc}")
        print(f"Čas (lokálny): {local}")
        print(f"Systémový:     {datetime.now()}")
        print(f"UTC offset:    +{self._get_utc_offset()} hodín")
        print("=" * 50)
    
    def __del__(self):
        """Čistenie pri ukončení"""
        pass


# ============================================
# JEDNODUCHÝ TEST PRE SPUSTENIE
# ============================================

if __name__ == "__main__":
    print("Test RTC handlera")
    print("=" * 50)
    
    rtc = RTCHandler()
    rtc.print_status()
    
    print("\nTest čítania času:")
    print(f"  Lokálny čas: {rtc.read_rtc_local()}")
    print(f"  Reťazec pre LCD: {rtc.get_datetime_string()}")
    
    print("\nInformácie o časovej zóne:")
    tz_info = rtc.get_timezone_info()
    for key, value in tz_info.items():
        print(f"  {key}: {value}")