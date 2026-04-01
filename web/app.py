# web/app.py
"""
Flask webová aplikácia pre ovládanie zavlažovacieho systému.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
from datetime import datetime
import time
import os
import sys





# Pridanie cesty pre import modulov
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.irrigation_plan import IrrigationPlan
import config

app = Flask(__name__)

# Globálne premenné pre prístup k systému
# Tieto sa nastavia pri štarte z main.py
pump_controller = None
irrigation_plan = None

# Pomocná funkcia
def get_local_time():
    """Získa lokálny čas (najprv z RTC, potom zo systému)"""
    pump = pump_controller
    
    # Skúsime získať čas z RTC cez pump_controller
    if pump and hasattr(pump, 'rtc') and pump.rtc and pump.rtc.initialized:
        local_time = pump.rtc.read_rtc_local()
        if local_time:
            return local_time
    
    # Fallback na systémový čas
    return datetime.now()


@app.route('/')
def index():
    """Hlavný dashboard"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API pre získanie aktuálneho stavu systému"""
    if not pump_controller:
        return jsonify({'error': 'Systém nie je inicializovaný'}), 500
    
    # Získanie stavov
    tlakove = pump_controller.get_tlakove_status()
    nasavacie = pump_controller.get_nasavacie_status()
    ventily = pump_controller.get_valve_states()
    
    # Aktuálny čas
    now = get_local_time()
    
    # Nájdenie aktívneho intervalu v pláne
    active_plan = None
    if irrigation_plan and pump_controller.active_interval:
        if 'id' in pump_controller.active_interval:
            active_plan = pump_controller.active_interval
    
    response = {
        'cas': now.strftime('%H:%M:%S'),
        'datum': now.strftime('%d.%m.%Y'),
        'tlakove': tlakove,
        'nasavacie': nasavacie,
        'ventily': ventily,
        'aktivny_plan': active_plan,
        'system_time': now.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(response)

@app.route('/api/schedule', methods=['GET'])
def api_get_schedule():
    """API pre získanie plánu"""
    if not irrigation_plan:
        return jsonify({'error': 'Plán nie je inicializovaný'}), 500
    
    intervals = irrigation_plan.get_all_intervals()
    return jsonify({'intervals': intervals})

@app.route('/api/schedule', methods=['POST'])
def api_update_schedule():
    """API pre aktualizáciu plánu"""
    if not irrigation_plan:
        return jsonify({'error': 'Plán nie je inicializovaný'}), 500
    
    data = request.json
    if not data or 'intervals' not in data:
        return jsonify({'error': 'Chýbajú dáta'}), 400
    
    success = True
    messages = []
    
    for interval_data in data['intervals']:
        interval_id = interval_data.get('id')
        if not interval_id:
            continue
        
        # Validácia
        valid, msg = irrigation_plan.validate_interval(
            interval_data['start'],
            interval_data['stop'],
            interval_data['okruh'],
            interval_data['tlak']
        )
        
        if valid:
            success = irrigation_plan.update_interval(
                interval_id,
                interval_data['start'],
                interval_data['stop'],
                interval_data['okruh'],
                interval_data['tlak'],
                interval_data['aktivny']
            )
            if not success:
                messages.append(f"Chyba pri ukladaní intervalu {interval_id}")
        else:
            success = False
            messages.append(f"Interval {interval_id}: {msg}")
    
    if success:
        return jsonify({'status': 'ok', 'message': 'Plán uložený'})
    else:
        return jsonify({'status': 'error', 'messages': messages}), 400

@app.route('/api/control/pump', methods=['POST'])
def api_control_pump():
    """API pre manuálne ovládanie čerpadiel"""
    if not pump_controller:
        return jsonify({'error': 'Systém nie je inicializovaný'}), 500
    
    data = request.json
    pump_type = data.get('pump')  # 'tlakove' alebo 'nasavacie'
    action = data.get('action')    # 'start', 'stop', 'mode'
    
    if pump_type == 'tlakove':
        if action == 'mode':
            auto_mode = data.get('auto', True)
            pump_controller.set_tlakove_mode(auto_mode)
            return jsonify({'status': 'ok', 'mode': 'auto' if auto_mode else 'manual'})
        
        elif action == 'start':
            okruh = data.get('okruh', 1)
            tlak = data.get('tlak', 80)
            result = pump_controller.manual_tlakove_start(okruh, tlak)
            return jsonify({'status': 'ok' if result else 'error'})
        
        elif action == 'stop':
            pump_controller.manual_tlakove_stop()
            return jsonify({'status': 'ok'})
    
    elif pump_type == 'nasavacie':
        if action == 'mode':
            auto_mode = data.get('auto', True)
            pump_controller.set_nasavacie_mode(auto_mode)
            return jsonify({'status': 'ok', 'mode': 'auto' if auto_mode else 'manual'})
        
        elif action == 'start':
            result = pump_controller.manual_nasavacie_start()
            return jsonify({'status': 'ok' if result else 'error'})
        
        elif action == 'stop':
            result = pump_controller.manual_nasavacie_stop()
            return jsonify({'status': 'ok' if result else 'error'})
    
    return jsonify({'error': 'Neplatný príkaz'}), 400

@app.route('/api/control/valve', methods=['POST'])
def api_control_valve():
    """API pre manuálne ovládanie ventilov"""
    if not pump_controller:
        return jsonify({'error': 'Systém nie je inicializovaný'}), 500
    
    data = request.json
    okruh = data.get('okruh', 1)
    action = data.get('action')  # 'open', 'close'
    
    if okruh < 1 or okruh > 4:
        return jsonify({'error': 'Neplatný okruh'}), 400
    
    if action == 'open':
        tlak = data.get('tlak', 80)
        pump_controller.serva[okruh-1].open_valve(tlak)
        return jsonify({'status': 'ok', 'pozicia': tlak})
    
    elif action == 'close':
        pump_controller.serva[okruh-1].close_valve()
        return jsonify({'status': 'ok'})
    
    return jsonify({'error': 'Neplatná akcia'}), 400

@app.route('/api/time')
def api_time():
    """API pre získanie aktuálneho lokálneho času"""
    now = get_local_time()
    
    # Získanie informácií o RTC
    pump =  pump_controller
    rtc_info = None
    if pump and hasattr(pump, 'rtc') and pump.rtc:
        rtc_info = {
            'connected': pump.rtc.initialized,
            'device': pump.rtc.rtc_device if pump.rtc.initialized else None
        }
    
    return jsonify({
        'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
        'date': now.strftime('%d.%m.%Y'),
        'time': now.strftime('%H:%M:%S'),
        'timestamp': now.timestamp(),
        'timezone': time.tzname,
        'utc_offset': time.timezone // -3600,
        'is_dst': time.localtime().tm_isdst,
        'rtc': rtc_info
    })


@app.route('/api/rtc/status')
def api_rtc_status():
    """API pre získanie stavu RTC modulu"""
    pump =  pump_controller
    
    if not pump or not hasattr(pump, 'rtc'):
        return jsonify({'error': 'RTC handler nedostupný'}), 500
    
    rtc = pump.rtc
    return jsonify(rtc.get_status())
    

@app.route('/api/time', methods=['POST'])
def api_set_time():
    """API pre nastavenie systémového času"""
    data = request.json
    time_str = data.get('time')
    
    if not time_str:
        return jsonify({'error': 'Chýba čas'}), 400
    
    try:
        # Formát: YYYY-MM-DD HH:MM:SS
        new_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        
        # V reálnom systéme by sme tu volali príkaz na nastavenie času
        # subprocess.run(['sudo', 'date', '-s', new_time.strftime('%Y-%m-%d %H:%M:%S')])
        
        return jsonify({'status': 'ok', 'new_time': new_time.strftime('%Y-%m-%d %H:%M:%S')})
    except ValueError:
        return jsonify({'error': 'Neplatný formát času'}), 400

@app.route('/settings')
def settings_page():
    """Stránka s nastaveniami"""
    return render_template('settings.html')

@app.route('/manual')
def manual_page():
    """Stránka pre manuálne ovládanie"""
    return render_template('manual.html')

@app.route('/schedule')
def schedule_page():
    """Stránka pre nastavenie plánov"""
    return render_template('schedule.html')

# Inicializácia pri štarte
def init_app(pump, plan):
    """Inicializácia web app s odkazmi na komponenty"""
    global pump_controller, irrigation_plan
    pump_controller = pump
    irrigation_plan = plan
    
    print("Web aplikácia inicializovaná")