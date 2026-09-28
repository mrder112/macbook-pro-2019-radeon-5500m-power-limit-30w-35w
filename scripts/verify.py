#!/usr/bin/env python3
"""Read profile selection and GPU telemetry without changing the system."""
import argparse
import datetime
import json
import plistlib
import subprocess
import time

def registry(*args):
    return plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg', *args, '-a', '-l']))

def walk(value):
    if isinstance(value, list):
        for child in value:
            yield from walk(child)
    elif isinstance(value, dict):
        yield value
        yield from walk(value.get('IORegistryEntryChildren', []))

def sample():
    nodes = list(walk(registry('-r', '-n', 'GFX0', '-d', '2')))
    gpu = next((n for n in nodes if n.get('device-id') == b'\x40\x73\0\0'), {})
    driver = next((n for n in nodes if n.get('IOClass') == 'AMDRadeonX6000_AmdRadeonControllerNavi14'), {})
    limit = driver.get('ATY,Boa', {}).get('aty_config', {}).get('CFG_PTPL2_MAX')
    marker = driver.get('Radeon35ProfileVersion')
    expected = {'Boa35-v3': 35, 'Boa30-v4': 30}.get(marker)
    keys = ['Device Utilization %', 'GPU Activity(%)', 'Core Clock(MHz)',
            'Memory Clock(MHz)', 'Temperature(C)', 'Total Power(W)']
    accelerators = []
    for n in registry('-r', '-c', 'IOAccelerator', '-d', '1'):
        if 'Navi14' in n.get('IORegistryEntryName', ''):
            stats = n.get('PerformanceStatistics', {})
            accelerators.append({k: stats[k] for k in keys if k in stats})
    return {'time': datetime.datetime.now().isoformat(), 'profile': marker,
            'publisher': driver.get('IOPersonalityPublisher'), 'profile_limit': limit,
            'gpu_limit': gpu.get('CFG_PTPL2_MAX'),
            'numeric_profile_selected': expected is not None and type(limit) is int and limit == expected,
            'telemetry': accelerators,
            'note': 'Missing telemetry is not zero power. A selected profile alone does not prove a power cap.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--samples', type=int, default=1)
    p.add_argument('--interval', type=float, default=2)
    a = p.parse_args()
    if not 1 <= a.samples <= 3600 or a.interval < 0.1:
        p.error('samples must be 1..3600; interval must be >= 0.1 seconds')
    for i in range(a.samples):
        print(json.dumps(sample(), ensure_ascii=False), flush=True)
        if i + 1 < a.samples:
            time.sleep(a.interval)
