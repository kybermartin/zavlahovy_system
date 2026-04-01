# test_rtc_sysfs.py
#!/usr/bin/env python3
"""Test RTC modulu cez sysfs"""

from hardware.rtc_handler import RTCHandler
import time

def test_rtc():
    print("=" * 60)
    print("TEST RTC MODULU (CEZ SYSFS)")
    print("=" * 60)
    
    rtc = RTCHandler()
    
    # 1. Zobrazenie stavu
    rtc.print_status()
    
    # 2. Synchronizácia
    print("\n1. Synchronizácia systémového času z RTC...")
    if rtc.set_system_time_from_rtc():
        print("   ✅ Hotovo")
    
    time.sleep(1)
    
    # 3. Overenie
    print("\n2. Čas po synchronizácii:")
    print(f"   RTC (lokálny): {rtc.read_rtc_local()}")
    print(f"   Systémový:     {datetime.now()}")
    
    # 4. Skutočný test
    print("\n3. Skutočný test cez hwclock:")
    import subprocess
    result = subprocess.run(['sudo', 'hwclock', '-r'], capture_output=True, text=True)
    print(f"   {result.stdout.strip()}")

if __name__ == "__main__":
    from datetime import datetime
    test_rtc()