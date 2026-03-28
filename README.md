# Open R-Net

[![DEFCON24](https://img.shields.io/badge/DEFCON-24-red.svg)](https://www.defcon.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/mYqJSS5)

![Open R-Net - Wheelchair CAN Bus Hacking](youtube_thumbnail.png)

**Reverse engineering the R-Net CAN bus protocol for power wheelchair accessibility**

*Originally presented at DEFCON24 (August 2016) by Stephen Chavez & Specter*

---

> **10 years in the making.** This project started in May 2016 at a table in a hackerspace with a Saleae logic analyzer, a 5-second capture, and zero idea what protocol we were even looking at. It took us 11 days just to figure out it was CAN — our bits were backwards. By May 29th we'd found the joystick frame. By May 30th we had a $75 Arduino + SparkFun CAN shield and were talking to the bus for the first time. DEFCON accepted our talk on June 7th and gave us 20 minutes — later bumped to 40. We tried bitbanging the bus to kill frames (it resends forever — don't bother). Stephen took the RTD bus across town after work, arriving at the hackerspace an hour late and getting home at 11pm, night after night. We bricked a PM, repaired a stuck MOSFET, attempted JSM handshake emulation with a bash script (got 25% through), and on July 19th pulled off the first "drive-by-wire over IP" demo in a parking lot with a phone as a router and 100 feet of range. We presented at DEFCON24 that August. Then life happened. A decade of late nights, burnt-out transceivers, and slowly peeling back every layer of this proprietary protocol. We reverse-engineered the serial authentication. We cracked the programmer dongle DLL. We dumped the firmware. We mapped 590+ frames on the bus. And now, in 2026, the full research is finally open source. No more $1,500 dongles. No more locked-out configs. No more begging a dealer to change your own wheelchair's speed setting. This is yours now. Use it, break it, build on it. It's been a long ride.

---

## What is this?

This project documents the R-Net CAN bus protocol used in power wheelchairs manufactured by companies like Permobil, Quickie, and others using PG Drives Technology (now Curtiss-Wright) electronics.

**Goal:** Enable alternative control methods for wheelchair users who cannot use a standard joystick - including USB joysticks, Xbox controllers, sip-and-puff devices, and network-based control.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/redragonx/open-rnet.git
cd open-rnet

# Set up CAN interface (Raspberry Pi + PiCAN2)
sudo ip link set can0 up type can bitrate 125000

# Monitor the bus
candump can0 -L

# Run joystick control (FollowJSM method)
python3 contrib/can2RNET/JoyLocal.py
```

See **[Getting Started](docs/GETTING_STARTED.md)** for full hardware setup instructions.

## Documentation

### Protocol

| Document | Description |
|----------|-------------|
| **[Protocol Specification](docs/RNET_PROTOCOL_SPECIFICATION.md)** | Full reverse-engineered R-Net specification |
| **[Protocol Guide](docs/RNET_PROTOCOL_GUIDE.md)** | Protocol overview and quick reference |
| **[Frame Dictionary](reference/RNET_FRAME_DICTIONARY.md)** | Complete frame reference (590+ entries) |
| **[Quick Reference](docs/QUICK_REFERENCE.md)** | Cheat sheet for common CAN operations |

### Device Protocols

| Document | Description |
|----------|-------------|
| **[R-Net Programmer Protocol](docs/RNET_PROGRAMMER_PROTOCOL.md)** | Read/write device configuration memory |
| **[cJSM Display Protocol](docs/CJSM_DISPLAY_PROTOCOL.md)** | Color JSM display text and mode configuration |
| **[Serial Authentication](docs/SERIAL_NUMBERS.md)** | XOR-based serial number challenge/response |
| **[Device Serials](docs/DEVICE_SERIALS.md)** | Known device serial numbers and network mappings |

### Safety & Diagnostics

| Document | Description |
|----------|-------------|
| **[Error Codes](docs/RNET_ERROR_CODES.md)** | Error code definitions and handling |
| **[ESP Protocol](docs/ESP_PROTOCOL.md)** | Electronic Stability Program protocol |
| **[Safety Restrictions](docs/SAFETY_RESTRICTIONS.md)** | Safety restrictions and lockout behavior |
| **[ICS Seating System](docs/ICS_SEATING_SYSTEM.md)** | ICS seating system documentation |

### Firmware & Configuration

| Document | Description |
|----------|-------------|
| **[Firmware Analysis](docs/FIRMWARE_DUMP_ANALYSIS.md)** | BTMouse and LEDJSM firmware dump analysis |
| **[Firmware Reverse Engineering](docs/FIRMWARE_REVERSE_ENGINEERING.md)** | HCS08 microcontroller code analysis |
| **[OBP Enable Guide](docs/OBP_ENABLE_GUIDE.md)** | How to enable On-Board Programming mode |
| **[Config File Format](docs/RNET_CONFIG_FILE_FORMAT.md)** | R-Net Programmer .R-net binary file format |
| **[LEDJSM Config Analysis](docs/LEDJSM_CONFIG_ANALYSIS.txt)** | Detailed config structure analysis |

### Getting Started

| Document | Description |
|----------|-------------|
| **[Getting Started](docs/GETTING_STARTED.md)** | Hardware setup and first steps |
| **[Technical Reference](CLAUDE.md)** | Comprehensive technical notes, algorithms, and protocol details |

## Key Features

- **Complete protocol specification** - Full reverse-engineered R-Net CAN bus protocol
- **Python library** - `can2RNET.py` for SocketCAN communication
- **Control scripts** - USB joystick and Xbox controller support
- **Protocol utilities** - Frame decoder, auth generator, capture analyzer
- **R-Net Programmer tools** - Read/write device configuration memory
- **Config parser** - Parse and compare .R-net configuration files
- **Firmware analysis** - HCS08 firmware dumps and reverse engineering
- **27+ packet captures** - PCAP files for protocol analysis
- **25 configuration files** - Real-world .R-net configs from multiple chair models
- **Three control methods** - FollowJSM, JSMerror, EmulateJSM

## Hardware Requirements

**Option 1: Raspberry Pi + PiCAN2** (~$115)
- Raspberry Pi 3/4
- PiCAN2 HAT with SMPS
- R-Net 4-pin connector

**Option 2: Arduino + CAN Shield** (~$75)
- Arduino UNO
- SparkFun CAN-BUS Shield
- R-Net 4-pin connector

## R-Net Connector Pinout

```
  +---------+
  | 1  |  2 |    1: CAN Lo
  |----+----|    2: CAN Hi
  | 3  |  4 |    3: +24VDC
  +---------+    4: GND
```

## Protocol Overview

R-Net uses **CAN 2.0B at 125Kbps** with:
- Standard frames (11-bit) for control and mode selection
- Extended frames (29-bit) for data and configuration
- XOR-based serial authentication (weak security)
- 10ms joystick frame timing

```
+---------------------------------------------+
|            R-Net Protocol Stack              |
+---------------------------------------------+
| Layer 4: Joystick, Speed, Parameters, Tones |
| Layer 3: Serial Auth, Device Slot Assignment |
| Layer 2: Standard (11-bit) / Extended (29-bit) Frames |
| Layer 1: CAN 2.0B @ 125Kbps                 |
+---------------------------------------------+
```

## Control Methods

| Method | Description | Pros | Cons |
|--------|-------------|------|------|
| **FollowJSM** | Send frame right after JSM | JSM still works | Timing-sensitive |
| **JSMerror** | Trigger JSM error, take over | Reliable | Disables JSM |
| **EmulateJSM** | Spoof complete JSM startup | No JSM needed | Needs known serial |

## Utility Scripts

```bash
# Self-program your chair (interactive)
python3 tools/rnet_self_program.py

# Enable OBP mode (guided, safe — backups first)
python3 tools/rnet_obp_mode.py --enable

# Read OBP parameters
python3 tools/rnet_obp_mode.py --read 0x06 0x01   # Forward Speed

# Decode R-Net frames
python3 tools/rnet_utils.py decode-frame 02000100#0064

# Low-level memory read/write (POP dongle protocol)
python3 tools/rnet_programmer.py read 0x0000 0x100 -o dump.bin

# Parse .R-net config files
python3 tools/rnet_config_parser.py config.R-net --json
```

## Project Structure

```
open-rnet/
+-- tools/                     # User-facing Python tools
|   +-- rnet_self_program.py   # Self-programming tool (start here)
|   +-- rnet_programmer.py     # Low-level POP protocol read/write
|   +-- rnet_obp_mode.py       # OBP (On-Board Programming) mode tool
|   +-- rnet_pop_shell.py     # Interactive POP protocol shell
|   +-- rnet_utils.py          # Protocol analysis utility
|   +-- rnet_config_parser.py  # .R-net config file parser
+-- lib/                       # Core CAN library
|   +-- can2RNET.py            # SocketCAN interface functions
+-- docs/                      # Protocol documentation (18 files)
|   +-- PROGRAMMER_TOOLS_GUIDE.md   # How to use the tools
|   +-- RNET_PROTOCOL_SPECIFICATION.md
|   +-- POP_PROTOCOL.md             # POP protocol from DLL RE
|   +-- RNET_DEVICE_CATALOG.md      # All device types and params
|   +-- ...
+-- hardware/                  # Firmware and setup scripts
|   +-- arduino_slcan/         # SLCAN firmware for Arduino
|   +-- scripts/               # CAN interface shell scripts
+-- captures/                  # 27+ R-Net packet captures
+-- configs/                   # Chair configuration data
|   +-- raw/                   # .R-net files (7 chair models, 25 files)
|   +-- parsed/                # Extracted settings (JSON, CSV)
+-- analysis/                  # Reverse engineering tools
|   +-- firmware/              # Firmware analysis scripts
|   +-- protocol/              # Protocol analysis scripts
+-- reference/                 # Frame dictionary and references
|   +-- RNET_FRAME_DICTIONARY.md   # 590+ frame entries
+-- contrib/                   # Upstream code
|   +-- can2RNET/              # Upstream redragonx/can2rNET
+-- CLAUDE.md                  # Technical reference
+-- LICENSE                    # GPLv3
```

## Safety Warning

**Power wheelchairs are critical medical devices.**

- Always have a physical emergency stop available
- Elevate the wheelchair (wheels off ground) during testing
- Have a spotter present
- Implement software safety limits
- Test thoroughly before real-world use

## Research Findings

### Security Vulnerabilities
- No encryption on any CAN traffic
- XOR-based authentication (challenge values in RTR frames are ignored)
- Timing-based frame spoofing possible (FollowJSM)
- Error injection enables complete control takeover (JSMerror)
- XOR tables extractable from captures or firmware
- No firmware signing (firmware can be modified)

### Discovered Protocols
- Serial number challenge/response authentication algorithm
- Parameter exchange protocol (0x78X/0x79X)
- R-Net Programmer read/write protocol (0x78F/0x793)
- Configuration transfer protocol (0x1E3X-0x1E8X)
- cJSM display text protocol (register 0x8C)
- Bluetooth module status frames
- Mode configuration frames (0x1ECXXXXX)

### Firmware
- Freescale/NXP HCS08 8-bit microcontrollers (MC9S08DZ family)
- Motorola S-Record format firmware dumps
- XOR-based config encryption (key stored in firmware at 0x0160)
- Sentinel value 0x18A7 marks uninitialized config slots

## Contributing

Found something new? Please contribute:
- Document new frame types
- Share anonymized captures
- Improve the Python library
- Add support for new input devices

## References

- [DEFCON24 Technical Presentation](docs/presentations/canPPT.pdf)
- [DEFCON24 Personal Story Presentation](docs/presentations/DEFCON24_chairhacking.pdf)
- [can-utils](https://github.com/linux-can/can-utils)
- [SocketCAN Documentation](https://www.kernel.org/doc/html/latest/networking/can.html)

## Authors

- **Stephen Chavez** - [@redragonx](https://github.com/redragonx)
- **Specter**

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details.

This research is provided for educational and accessibility purposes. Use responsibly and always prioritize safety.

---

*"Hacking wheelchairs for accessibility, not mayhem."* - DEFCON24
