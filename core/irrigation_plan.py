# core/irrigation_plan.py
"""
Správa plánu zavlažovania - 4 denné intervaly.
Ukladanie a načítanie z JSON súboru.
"""

import json
import os
from datetime import datetime, time

class IrrigationPlan:
    """Trieda pre správu intervalov zavlažovania"""
    
    def __init__(self, filename="data/schedule.json"):
        """
        Inicializácia plánu
        
        Args:
            filename (str): Cesta k JSON súboru s plánom
        """
        self.filename = filename
        self.intervals = []
        self.load()
    
    def load(self):
        """Načítanie plánu z JSON súboru"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.intervals = data.get('intervals', [])
                print(f"Plán načítaný z {self.filename}")
            else:
                # Vytvorenie predvoleného plánu
                self._create_default_plan()
                self.save()
                print("Vytvorený predvolený plán")
        except Exception as e:
            print(f"Chyba pri načítaní plánu: {e}")
            self._create_default_plan()
    
    def _create_default_plan(self):
        """Vytvorenie predvoleného prázdneho plánu"""
        self.intervals = [
            {
                'id': 1,
                'start': '06:00',
                'stop': '06:30',
                'okruh': 1,
                'tlak': 80,
                'aktivny': False
            },
            {
                'id': 2,
                'start': '18:00',
                'stop': '18:30',
                'okruh': 2,
                'tlak': 70,
                'aktivny': False
            },
            {
                'id': 3,
                'start': '00:00',
                'stop': '00:00',
                'okruh': 1,
                'tlak': 50,
                'aktivny': False
            },
            {
                'id': 4,
                'start': '00:00',
                'stop': '00:00',
                'okruh': 2,
                'tlak': 60,
                'aktivny': False
            }
        ]
    
    def save(self):
        """Uloženie plánu do JSON súboru"""
        try:
            # Vytvorenie adresára ak neexistuje
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({'intervals': self.intervals}, f, indent=2, ensure_ascii=False)
            print(f"Plán uložený do {self.filename}")
            return True
        except Exception as e:
            print(f"Chyba pri ukladaní plánu: {e}")
            return False
    
    def get_interval(self, interval_id):
        """
        Získanie intervalu podľa ID
        
        Args:
            interval_id (int): 1-4
        
        Returns:
            dict: Interval alebo None
        """
        for interval in self.intervals:
            if interval['id'] == interval_id:
                return interval
        return None
    
    def update_interval(self, interval_id, start, stop, okruh, tlak, aktivny):
        """
        Aktualizácia existujúceho intervalu
        
        Args:
            interval_id (int): 1-4
            start (str): Čas štartu "HH:MM"
            stop (str): Čas konca "HH:MM"
            okruh (int): 1-4
            tlak (int): 0-100
            aktivny (bool): True ak má byť interval aktívny
        
        Returns:
            bool: True ak úspešné
        """
        interval = self.get_interval(interval_id)
        if interval:
            interval['start'] = start
            interval['stop'] = stop
            interval['okruh'] = okruh
            interval['tlak'] = tlak
            interval['aktivny'] = aktivny
            return self.save()
        return False
    
    def get_active_interval(self, current_datetime=None):
        """
        Zistenie, ktorý interval je práve aktívny
        
        Args:
            current_datetime (datetime): Aktuálny čas, ak None použije now()
        
        Returns:
            dict: Aktívny interval alebo None
        """
        if current_datetime is None:
            current_datetime = datetime.now()
        
        current_time = current_datetime.time()
        
        for interval in self.intervals:
            if not interval['aktivny']:
                continue
            
            try:
                start_time = datetime.strptime(interval['start'], "%H:%M").time()
                stop_time = datetime.strptime(interval['stop'], "%H:%M").time()
                
                # Kontrola či je aktuálny čas v intervale
                if start_time <= current_time <= stop_time:
                    return interval
                    
            except ValueError as e:
                print(f"Chyba v časovom formáte pre interval {interval['id']}: {e}")
        
        return None
    
    def get_next_interval(self, current_datetime=None):
        """
        Zistenie nasledujúceho intervalu, ktorý má štartovať
        
        Args:
            current_datetime (datetime): Aktuálny čas
        
        Returns:
            dict: Nasledujúci interval alebo None
        """
        if current_datetime is None:
            current_datetime = datetime.now()
        
        current_time = current_datetime.time()
        current_time_minutes = current_time.hour * 60 + current_time.minute
        
        next_interval = None
        min_diff = 24 * 60  # Max možný rozdiel
        
        for interval in self.intervals:
            if not interval['aktivny']:
                continue
            
            try:
                start_time = datetime.strptime(interval['start'], "%H:%M").time()
                start_minutes = start_time.hour * 60 + start_time.minute
                
                # Rozdiel od aktuálneho času
                diff = start_minutes - current_time_minutes
                if diff < 0:
                    diff += 24 * 60  # Posun do ďalšieho dňa
                
                if 0 < diff < min_diff:
                    min_diff = diff
                    next_interval = interval
                    
            except ValueError:
                continue
        
        return next_interval
    
    def get_all_intervals(self):
        """Vráti zoznam všetkých intervalov"""
        return self.intervals
    
    def validate_interval(self, start, stop, okruh, tlak):
        """
        Validácia hodnôt intervalu
        
        Args:
            start (str): Čas štartu
            stop (str): Čas konca
            okruh (int): Číslo okruhu
            tlak (int): Tlak v percentách
        
        Returns:
            tuple: (bool, str) - (úspech, chybová správa)
        """
        # Kontrola formátu času
        try:
            start_time = datetime.strptime(start, "%H:%M")
            stop_time = datetime.strptime(stop, "%H:%M")
        except ValueError:
            return False, "Neplatný formát času (použite HH:MM)"
        
        # Kontrola či je stop po start (alebo aspoň rovnaký)
        if stop_time <= start_time:
            return False, "Čas konca musí byť neskôr ako čas štartu"
        
        # Kontrola okruhu
        if okruh < 1 or okruh > 4:
            return False, "Okruh musí byť 1-4"
        
        # Kontrola tlaku
        if tlak < 0 or tlak > 100:
            return False, "Tlak musí byť 0-100%"
        
        return True, "OK"