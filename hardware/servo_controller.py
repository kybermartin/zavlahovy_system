# hardware/servo_controller.py
"""
Ovládanie servomotorov SG90 pre reguláciu ventilov.
Vylepšená verzia s plynulým a pomalým prechodom.
"""

import RPi.GPIO as GPIO
import time
import threading

class ServoController:
    """Trieda pre ovládanie jedného serva SG90 s plynulým prechodom"""
    
    # Rozsah PWM pre SG90
    PWM_FREQ = 50  # 50 Hz = 20ms perióda
    DUTY_MIN = 2.5  # 0° (zatvorené)
    DUTY_MAX = 12.5  # 180° (otvorené)
    
    def __init__(self, pin, servo_id=1, transition_time=2.0):
        """
        Inicializácia serva
        
        Args:
            pin (int): GPIO pin pre PWM (BCM)
            servo_id (int): Identifikátor serva (1-4)
            transition_time (float): Čas prechodu v sekundách (2 sekundy = pomalé)
        """
        self.pin = pin
        self.servo_id = servo_id
        self.transition_time = transition_time  # Čas prechodu medzi polohami
        
        self.current_position = 0  # 0-100%
        self.target_position = 0
        self.current_duty = self.DUTY_MIN
        
        # Pre plynulý prechod
        self.transition_thread = None
        self.transition_running = False
        self.transition_lock = threading.Lock()
        
        # Nastavenie GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        # Inicializácia PWM
        self.pwm = GPIO.PWM(self.pin, self.PWM_FREQ)
        self.pwm.start(self.DUTY_MIN)
        
        print(f"Servo {servo_id} inicializované na pine {pin} (čas prechodu: {transition_time}s)")
        time.sleep(0.5)  # Počkáme na stabilizáciu
    
    def set_position(self, percent, immediate=False):
        """
        Nastavenie polohy serva s plynulým prechodom
        
        Args:
            percent (int/float): Požadovaná poloha 0-100
            immediate (bool): Ak True, zmení okamžite (bez plynulého prechodu)
        """
        # Obmedzenie na rozsah 0-100
        percent = max(0, min(100, percent))
        
        with self.transition_lock:
            self.target_position = percent
            
            # Ak už beží prechod, aktualizujeme len cieľ
            if self.transition_running and not immediate:
                print(f"Servo {self.servo_id}: Prebieha prechod, nový cieľ: {percent}%")
                return
            
            # Zastavíme predchádzajúci prechod
            self.transition_running = False
            if self.transition_thread and self.transition_thread.is_alive():
                self.transition_thread.join(timeout=0.5)
            
            if immediate:
                # Okamžitá zmena
                self._set_immediate_position(percent)
            else:
                # Spustíme plynulý prechod v samostatnom vlákne
                self.transition_running = True
                self.transition_thread = threading.Thread(
                    target=self._smooth_transition,
                    args=(percent,)
                )
                self.transition_thread.daemon = True
                self.transition_thread.start()
    
    def _set_immediate_position(self, percent):
        """Okamžité nastavenie polohy (bez prechodu)"""
        duty = self.DUTY_MIN + (percent / 100.0) * (self.DUTY_MAX - self.DUTY_MIN)
        self.pwm.ChangeDutyCycle(duty)
        self.current_position = percent
        self.current_duty = duty
        print(f"Servo {self.servo_id} OKAMŽITE nastavené na {percent}%")
    
    def _smooth_transition(self, target_percent):
        """
        Plynulý prechod z aktuálnej na cieľovú polohu.
        Beží v samostatnom vlákne, aby neblokoval hlavný program.
        
        Args:
            target_percent (float): Cieľová poloha v percentách (0-100)
        """
        # Uložíme si štartovaciu polohu (aktuálna pozícia)
        start_pos = self.current_position
        target_pos = target_percent
        
        # Prepočet percent na duty cycle pre štart a cieľ
        start_duty = self.DUTY_MIN + (start_pos / 100.0) * (self.DUTY_MAX - self.DUTY_MIN)
        target_duty = self.DUTY_MIN + (target_pos / 100.0) * (self.DUTY_MAX - self.DUTY_MIN)
        
        # Vypočítame rozdiel v polohe a duty cycle
        pos_diff = target_pos - start_pos
        duty_diff = target_duty - start_duty
        
        # Ak je rozdiel veľmi malý (menej ako 1% - 2% podľa nastavenia),
        # preskočíme plynulý prechod a nastavíme rovno cieľovú polohu
        if abs(pos_diff) < 2:  # 2% tolerancia
            print(f"Servo {self.servo_id}: Rozdiel malý ({pos_diff:.1f}%), nastavujem priamo")
            self.pwm.ChangeDutyCycle(target_duty)
            self.current_position = target_pos
            self.current_duty = target_duty
            self.transition_running = False
            return
        
        # Vypočítame počet krokov pre plynulý prechod
        # 50 krokov za sekundu = každý krok trvá 20ms
        # To je dostatočne jemné pre plynulý pohyb
        steps = int(self.transition_time * 50)
        
        # Minimalizujeme počet krokov - aspoň 10 krokov pre viditeľný prechod
        if steps < 10:
            steps = 10
        
        # Vypočítame čas medzi jednotlivými krokmi
        step_time = self.transition_time / steps
        
        # Vypočítame zmenu duty cycle na jeden krok
        step_duty = duty_diff / steps
        
        print(f"Servo {self.servo_id}: Plynulý prechod {start_pos:.1f}% -> {target_pos:.1f}% "
              f"({self.transition_time}s, {steps} krokov, {step_time*1000:.1f}ms na krok)")
        
        # Hlavná slučka prechodu - postupne meníme polohu
        for i in range(steps + 1):
            # Na začiatku každého kroku skontrolujeme, či nemáme nový cieľ
            # (používateľ mohol zadať novú polohu počas prechodu)
            with self.transition_lock:
                # Ak prechod už nie je aktívny (bol prerušený), ukončíme vlákno
                if not self.transition_running:
                    print(f"Servo {self.servo_id}: Prechod prerušený používateľom")
                    return
                
                # Vypočítame aktuálnu pozíciu v prechode (lineárna interpolácia)
                progress = i / steps
                
                # Lineárna interpolácia duty cycle
                current_duty = start_duty + (step_duty * i)
                
                # Lineárna interpolácia percent (pre informáciu)
                current_pos = start_pos + (pos_diff * progress)
                
                # Nastavenie PWM na aktuálnu hodnotu
                self.pwm.ChangeDutyCycle(current_duty)
                
                # Aktualizácia aktuálnej polohy a duty cycle
                self.current_duty = current_duty
                self.current_position = current_pos
                
                # Voliteľné: zobrazenie priebehu (každých 10% prechodu)
                if i % (steps // 10) == 0 and i > 0:
                    print(f"Servo {self.servo_id}: Prechod {progress*100:.0f}% - {current_pos:.1f}%")
            
            # Počkáme na ďalší krok
            time.sleep(step_time)
        
        # Dokončenie prechodu - nastavíme presnú cieľovú hodnotu
        with self.transition_lock:
            # Pre istotu nastavíme presne cieľovú duty cycle
            self.pwm.ChangeDutyCycle(target_duty)
            self.current_position = target_pos
            self.current_duty = target_duty
            self.transition_running = False
        
        print(f"Servo {self.servo_id}: Prechod DOKONČENÝ na {target_pos}%")
        
    def open_valve(self, pressure=None, immediate=False):
        """
        Otvorenie ventilu s nastavením tlaku
        
        Args:
            pressure (int): Tlak v % (0-100), ak None použije 100%
            immediate (bool): Ak True, zmení okamžite
        """
        if pressure is None:
            pressure = 100
        self.set_position(pressure, immediate)
        print(f"Ventil {self.servo_id} otváraný (tlak {pressure}%)")
    
    def close_valve(self, immediate=False):
        """
        Zatvorenie ventilu
        
        Args:
            immediate (bool): Ak True, zmení okamžite
        """
        self.set_position(0, immediate)
        print(f"Ventil {self.servo_id} zatváraný")
    
    def get_position(self):
        """Vráti aktuálnu polohu v percentách"""
        return self.current_position
    
    def is_open(self):
        """Vráti True ak je ventil otvorený (viac ako 5%)"""
        return self.current_position > 5
    
    def stop_transition(self):
        """Zastavenie prebiehajúceho prechodu"""
        with self.transition_lock:
            self.transition_running = False
        print(f"Servo {self.servo_id}: Prechod zastavený")
    
    def set_transition_time(self, seconds):
        """
        Nastavenie času prechodu
        
        Args:
            seconds (float): Čas prechodu v sekundách
        """
        self.transition_time = max(0.5, min(10.0, seconds))
        print(f"Servo {self.servo_id}: Čas prechodu nastavený na {self.transition_time}s")
    
    def stop(self):
        """Zastavenie PWM signálu"""
        self.stop_transition()
        self.pwm.ChangeDutyCycle(0)
    
    def __del__(self):
        """Čistenie pri ukončení"""
        try:
            self.stop_transition()
            self.close_valve(immediate=True)
            self.stop()
            self.pwm.stop()
            GPIO.cleanup(self.pin)
        except:
            pass