# MacBook Pro 2019 — Radeon Pro 5500M: 30 W / 35 W experiment

[Русский](README.ru.md)

**Observed on one MacBookPro16,1: a custom codeless IOKit personality selected by Apple's driver coincided with reported GPU power of 34–35 W or 30 W at 99% GPU activity.** This repository documents the mechanism, reproducible profile generation and original measurement snapshots. It is not a universal EFI or a validated production power limiter.

## Tested machine and software

| Item | Tested value |
|---|---|
| Mac | MacBook Pro 16-inch, 2019; MacBookPro16,1 |
| CPU | 8-core Intel Core i9, 2.4 GHz base |
| GPU | Radeon Pro 5500M, 8 GB; PCI 1002:7340 |
| OS | macOS 15.7.9, build 24G830; Darwin 24.6.0 |
| Bootloader | OpenCore `REL-106-2025-11-03` (1.0.6) |
| Controller | `AMDRadeonNavi14Controller`, `ATY,Boa` |
| Measurement dates | 2026-09-28, as recorded by the local system clock |

## Evidence

| Configuration | GPU activity | Driver-reported power | Core clock | Temperature | Report |
|---|---:|---:|---:|---:|---|
| Earlier WEG injection attempt, ineffective | 99% | 48 W | 1279 MHz | 74 °C | [baseline](evidence/baseline-48w.txt) |
| Boa35-v3 | 99% | 34–35 W | 823–850 MHz | 71 °C | [35 W](evidence/profile-35w.txt) |
| Boa30-v4 | 99% | 30 W | 522 MHz | 71 °C | [30 W](evidence/profile-30w.txt) |

These are short snapshots, not a controlled FPS comparison or a completed endurance test. Duplicate telemetry rows are not independent trials. The workload was discussed as Heaven, but the running process during the 30 W session was **Unigine Valley**. Exact matching settings and workload identity for earlier snapshots were not archived. CPU power settings also changed between sessions. Do not infer an efficiency gain, a fixed performance penalty, or an absolute hardware-enforced ceiling from this table. `Total Power(W)` is driver telemetry, not wall power or an independently calibrated measurement.

**A previous boot with the 30 W profile produced a black screen. Its cause remains unresolved.** A later boot with the same profile succeeded, selected numeric 30, and produced the loaded snapshot above. No fix for the black screen is claimed. Missing telemetry also occurred before readings returned; missing readings alone do not establish driver failure.

### Temperature, fan speed and test conditions

The owner's follow-up observations on this particular machine are:

| GPU power setting | Cooling needed / observed | GPU temperature under full GPU load |
|---|---|---|
| 35 W | Fans manually raised to approximately 75–90% to keep temperatures from climbing beyond roughly 75 °C | Up to approximately 75 °C with that cooling |
| 30 W | Fans at approximately 5,000 RPM | Approximately 70 °C |

The owner reports the 30 W result both in macOS and in Windows through Boot Camp, with a thermal modification applied to the laptop and CPU Turbo Boost disabled. The practical benefit reported is lower required fan speed under full GPU load while maintaining about 70 °C. These results describe a modified machine; they should not be presented as stock cooling performance or attributed solely to the GPU profile. The thermal modification's exact construction is not documented here.

**The Windows result uses a separate power-control utility referred to by the owner as “Power Tools”; its exact name, version and settings have not been recorded.** The macOS codeless profile in this repository does not apply a Windows power limit. The two OS results are owner observations, not a controlled cross-platform benchmark.

The archived 30 W snapshot shows 71 °C; a later live reading showed 77 °C at 29 W and 99% GPU activity. These readings are retained as observations at different times, not replaced by the owner's approximate 70 °C result. The owner also observed temperatures rising as fan speed decreased. Synchronized fan RPM/temperature logs, ambient temperature, run duration and fixed-fan comparisons were not archived. Fan percentages cannot be converted to RPM from these records. Thus the cooling comparison is explicitly owner-reported, rather than a measured causal result. The later 77 °C live reading is not included among the archived raw reports.

## How it works

The generator copies the installed driver's `AMDRadeonNavi14Controller` personality, preserving the native driver identifier and class, and changes five properties:

1. `ATY,Boa/aty_config/CFG_PTPL2_MAX`: integer 50 → 35 or 30.
2. `IOPCIMatch`: narrow to `0x73401002`.
3. `IOProbeScore`: 6000 → 6100.
4. Add a matching requirement `IOPropertyMatch/radeon35-profile-enable` with the corresponding marker bytes.
5. Add the diagnostic string `Radeon35ProfileVersion`.

OpenCore injects the matching marker onto the GPU. The codeless kext publishes the personality; Apple's existing driver supplies executable code. The 30 W profile retains property names containing `35` for compatibility with this experiment. Its values identify `Boa30-v4`.

Direct PCI property injection did not establish the intended limit. The earlier WEG attempt delivered `<23000000>` into a different configuration dictionary without selecting the intended numeric native profile; power remained 48 W in the recorded sample. Delivery, driver selection and measured power must be checked separately.

## Generate locally

Requires Python 3 and the **exact tested native Info.plist**. No sudo is needed to generate or verify. The source SHA-256 must be:

```
68588f3aeac0a0bf3aedf53379875068ff523e5c73d5a560431a17b99c69501d
```

```sh
python3 scripts/build_profile.py --watts 35 --output build/35w
python3 scripts/build_profile.py --watts 30 --output build/30w
```

Each command creates a codeless kext, `config-fragment.plist`, and a manifest. An existing output directory is refused. **The fragment is not a bootable OpenCore configuration.** No Apple driver files, OpenCore binaries, machine serials or full personal EFI are distributed.

## USB-first installation

For experienced OpenCore users with a working bootable USB and a separate known-good startup route:

1. Back up the complete USB EFI and keep the internal boot setup unchanged for initial testing. This project does not format disks or select a startup disk.
2. Generate one profile. Copy its kext to the USB's `EFI/OC/Kexts`.
3. Merge the supplied `Kernel/Add` entry and `DeviceProperties/Add` properties into the USB's existing `config.plist`, preserving other entries. The PCI path is specific to the tested machine; verify it on your hardware.
4. Disable the other Boa profile. The tested setup enabled only the selected Boa profile; Lilu/WhateverGreen were disabled. Do not disable dependencies blindly on a different configuration.
5. Validate the complete configuration using the `ocvalidate` version matching your OpenCore. The tested USB had `NVRAM/WriteFlash=false` and `Misc/Boot/LauncherOption=Disabled`; it did not set a default startup disk.
6. Boot the USB once using Option → its EFI Boot entry, without holding Control. Do not change security settings merely to follow this guide; machines with different prerequisites are outside this reproduction.

The kext entry is restricted to Darwin 24.6.0, **not to build 24G830**. The build-time hash guard does not protect an already-installed profile after an OS update. Disable/reassess it before updating macOS. This profile does not limit Windows/Boot Camp GPU power, undervolt the GPU, or configure CPU power limits.

## Verify and record a stress run

```sh
python3 scripts/verify.py
python3 scripts/verify.py --samples 600 --interval 2 > stress.jsonl
```

The second command records about 20 minutes while you run the benchmark separately. Use a visible windowed scene, confirm the benchmark renderer is AMD Radeon Pro 5500M, and record resolution, quality, FPS, charger state and CPU settings. Compare 35 and 30 W using the same workload. Check the selected profile, numeric value, GPU activity, power and stability. Empty telemetry means unavailable data, not 0 W. A successful boot does not prove a sustained cap.

If the screen goes black, shut down, unplug the test USB and use the known-good internal startup. Restore the saved USB configuration before retrying. If an internal profile was installed separately, unplugging USB does not undo that installation; restore the corresponding internal backup using your known-good boot route. Never replace internal EFI until you have tested recovery and stability.

## Scope and provenance

Reports are original local script output; filenames were simplified and no shell prompts/usernames are included. The baseline report's escaped PCI/controller text is left intact. Source generator output was compared structurally with both locally tested kexts. This establishes reproducibility of the profile files, not stability on other computers.

Technical references:

- [Apple: IOKit driver matching](https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/Matching/Matching.html)
- [Apple XNU: IOCatalogue](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/Kernel/IOCatalogue.cpp)
- [WhateverGreen 1.6.9 Radeon implementation](https://github.com/acidanthera/WhateverGreen/blob/1.6.9/WhateverGreen/kern_rad.cpp)
- [OpenCorePkg](https://github.com/acidanthera/OpenCorePkg)
- [OCLP boot instructions](https://dortania.github.io/OpenCore-Legacy-Patcher/BOOT.html)

When reporting a reproduction, include model identifier, GPU/VRAM, OS build, native driver hash, OpenCore version, selected profile, benchmark settings, timed telemetry, FPS and failures. Remove serial numbers, UUIDs and personal paths first.
