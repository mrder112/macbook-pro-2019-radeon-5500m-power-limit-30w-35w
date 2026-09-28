#!/usr/bin/env python3
"""Generate a codeless profile locally; never modify disks or an existing EFI."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import plistlib

EXPECTED = '68588f3aeac0a0bf3aedf53379875068ff523e5c73d5a560431a17b99c69501d'
SOURCE = '/System/Library/Extensions/AMDRadeonX6000Framebuffer.kext/Contents/Info.plist'
PCI = 'PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)/Pci(0x0,0x0)/Pci(0x0,0x0)'

def build(source, watts, output):
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('Driver differs from tested macOS 15.7.9 build 24G830. Refusing to generate.')
    native = plistlib.loads(raw)
    p = copy.deepcopy(native['IOKitPersonalities']['AMDRadeonNavi14Controller'])
    assert type(p['ATY,Boa']['aty_config']['CFG_PTPL2_MAX']) is int
    assert p['ATY,Boa']['aty_config']['CFG_PTPL2_MAX'] == 50
    marker = 'Boa35-v3' if watts == 35 else 'Boa30-v4'
    version = '0.3.0' if watts == 35 else '0.4.0'
    name = 'RadeonBoa%dProfile' % watts
    p['ATY,Boa']['aty_config']['CFG_PTPL2_MAX'] = watts
    p['IOPCIMatch'] = '0x73401002'
    p['IOProbeScore'] = 6100
    p['IOPropertyMatch']['radeon35-profile-enable'] = (marker + '\0').encode()
    p['Radeon35ProfileVersion'] = marker
    bundle = dict(CFBundleIdentifier='local.radeon.Boa%dProfile' % watts,
                  CFBundleName=name, CFBundleVersion=version,
                  CFBundleShortVersionString=version, CFBundleInfoDictionaryVersion='6.0',
                  CFBundlePackageType='KEXT', OSBundleRequired='Root',
                  OSBundleLibraries={'com.apple.kext.AMDRadeonX6000Framebuffer': '7.0.0'},
                  IOKitPersonalities={'Radeon5500M-' + marker: p})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    target = output / (name + '.kext') / 'Contents'
    target.mkdir(parents=True)
    (target / 'Info.plist').write_bytes(plistlib.dumps(bundle, sort_keys=False))
    entry = dict(Arch='x86_64', BundlePath=name + '.kext', Comment=marker,
                 Enabled=True, ExecutablePath='', MinKernel='24.6.0',
                 MaxKernel='24.6.0', PlistPath='Contents/Info.plist')
    fragment = {'DeviceProperties': {'Add': {PCI: {
        'radeon35-test-version': marker,
        'radeon35-profile-enable': (marker + '\0').encode()}}},
        'Kernel': {'Add': [entry]}}
    (output / 'config-fragment.plist').write_bytes(plistlib.dumps(fragment))
    (output / 'manifest.json').write_text(json.dumps({
        'source_sha256': EXPECTED, 'source_build': '24G830', 'profile': marker,
        'requested_watts': watts, 'complete_opencore_config': False}, indent=2) + '\n')
    print('Generated:', output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watts', type=int, choices=[30, 35], required=True)
    parser.add_argument('--source', default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.watts, args.output)
