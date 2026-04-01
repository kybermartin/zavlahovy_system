# hardware/lcd_handler.py
"""
Obsluha LCD displeja 1602A cez I2C adaptér PCF8574.
"""

import time
import smbus2

class LCDHandler:
    """Trieda pre obsluhu LCD 1602A s I2C adaptérom"""
    
    # Príkazy pre LCD
    LCD_CLEAR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_DISPLAY_CONTROL = 0x08
    LCD_FUNCTION_SET = 0x20
    LCD_SET_DDRAM_ADDR = 0x80
    
    # Bity pre riadenie
    LCD_ENABLE_BIT = 0b00000100
    LCD_RW_BIT = 0b00000010
    LCD_RS_BIT = 0b00000001
    LCD_BACKLIGHT_BIT = 0b00001000
    
    def __init__(self, i2c_addr=0x27, bus_num=1, cols=16, rows=2):
        """
        Inicializácia LCD displeja
        
        Args:
            i2c_addr (int): I2C adresa adaptéra
            bus_num (int): Číslo I2C zbernice
            cols (int): Počet stĺpcov (16)
            rows (int): Počet riadkov (2)
        """
        self.addr = i2c_addr
        self.cols = cols
        self.rows = rows
        self.backlight = True
        self.bus = None
        self.initialized = False
        
        try:
            self.bus = smbus2.SMBus(bus_num)
            self.initialized = True
        except Exception as e:
            print(f"Chyba: Nepodarilo sa pripojiť k I2C zbernici: {e}")
            return
    
    def init_display(self):
        """Inicializácia LCD displeja - musí sa zavolať pri štarte"""
        if not self.initialized:
            return
            
        try:
            time.sleep(0.05)  # Počkáme na stabilizáciu napätia
            
            # Inicializačná sekvencia pre 4-bitový mód
            self._write_byte(0x30, 0)  # Funkcia set 8-bit
            time.sleep(0.005)
            self._write_byte(0x30, 0)  # Opakujeme
            time.sleep(0.001)
            self._write_byte(0x30, 0)  # Opakujeme
            self._write_byte(0x20, 0)  # Prepneme na 4-bit
            
            # Nastavenie funkcie: 4-bit, 2 riadky, 5x8 font
            self._write_command(0x28)
            
            # Vypnutie displeja
            self._write_command(0x08)
            
            # Vyčistenie displeja
            self.clear()
            
            # Nastavenie režimu: inkrement, bez posunu
            self._write_command(0x06)
            
            # Zapnutie displeja: zap, kurzor vyp, blikanie vyp
            self._write_command(0x0C)
            
            print("LCD inicializované")
            
        except Exception as e:
            print(f"Chyba pri inicializácii LCD: {e}")
            self.initialized = False
    
    def clear(self):
        """Vyčistenie displeja"""
        if not self.initialized:
            return
        self._write_command(self.LCD_CLEAR)
        time.sleep(0.002)
    
    def home(self):
        """Návrat kurzora na pozíciu 0,0"""
        if not self.initialized:
            return
        self._write_command(self.LCD_HOME)
        time.sleep(0.002)
    
    def set_cursor(self, col, row):
        """
        Nastavenie kurzora na pozíciu
        
        Args:
            col (int): Stĺpec (0-15)
            row (int): Riadok (0-1)
        """
        if not self.initialized:
            return
            
        addr = col
        if row == 1:
            addr += 0x40  # Druhý riadok začína na adrese 0x40
        self._write_command(self.LCD_SET_DDRAM_ADDR | addr)
    
    def show_message(self, line1="", line2=""):
        """
        Zobrazenie správy na dvoch riadkoch
        
        Args:
            line1 (str): Text pre prvý riadok
            line2 (str): Text pre druhý riadok
        """
        if not self.initialized:
            print(f"LCD: {line1} | {line2}")
            return
            
        # Vyčistíme a nastavíme kurzor na začiatok
        self.clear()
        
        # Prvý riadok
        self.set_cursor(0, 0)
        self._write_string(line1[:self.cols].ljust(self.cols))
        
        # Druhý riadok
        self.set_cursor(0, 1)
        self._write_string(line2[:self.cols].ljust(self.cols))
    
    def set_backlight(self, state):
        """
        Zapne/vypne podsvietenie
        
        Args:
            state (bool): True = zap, False = vyp
        """
        self.backlight = state
        # Pošleme prázdny byte pre aktualizáciu podsvietenia
        if self.bus is not None and self.initialized:
            try:
                self._write_byte(0x00, 0)
            except Exception:
                # Počas čistenia ignorujeme chybu
                if hasattr(self, '_cleaning'):
                    pass
                else:
                    raise
    
    def _write_string(self, text):
        """Zápis reťazca na aktuálnu pozíciu"""
        for char in text:
            self._write_byte(ord(char), 1)
    
    def _write_command(self, cmd):
        """Zápis príkazu do LCD"""
        self._write_byte(cmd, 0)
    
    def _write_byte(self, value, mode):
        """
        Zápis bajtu do LCD cez I2C
        
        Args:
            value (int): Hodnota na zápis
            mode (int): 0 = command, 1 = data
        """
        # Odošleme vyššie 4 bity
        high = value & 0xF0
        self._send_nibble(high, mode)
        
        # Odošleme nižšie 4 bity
        low = (value << 4) & 0xF0
        self._send_nibble(low, mode)
    
    def _send_nibble(self, nibble, mode):
        """
        Odoslanie 4-bitového nibblu
        
        Args:
            nibble (int): 4 bity na odoslanie
            mode (int): 0 = command, 1 = data
        """
        # Pripravíme dáta
        data = nibble | self.LCD_ENABLE_BIT
        
        if mode:
            data |= self.LCD_RS_BIT
        
        if self.backlight:
            data |= self.LCD_BACKLIGHT_BIT
        
        # Odošleme s Enable=1
        try:
            self.bus.write_byte(self.addr, data)
        except Exception:
            if hasattr(self, '_cleaning'):
                return
            raise
        time.sleep(0.000001)
        
        # Odošleme s Enable=0
        try:
            self.bus.write_byte(self.addr, data & ~self.LCD_ENABLE_BIT)
        except Exception:
            if hasattr(self, '_cleaning'):
                return
            raise
        time.sleep(0.00005)
    
    def __del__(self):
        """Čistenie pri ukončení"""
        self._cleaning = True
        try:
            if hasattr(self, 'bus') and self.bus and self.initialized:
                self.clear()
                self.set_backlight(False)
                self.bus.close()
        except Exception:
            # Ignorujeme všetky chyby počas ukončovania
            pass