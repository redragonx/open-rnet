# R-Net Protocol Reverse Engineering Guide

**A comprehensive guide to the R-Net CAN bus protocol used in power wheelchairs**

*Compiled from DEFCON24 research by Stephen Chavez & Specter, with additional protocol analysis from pcap captures.*

---

## Table of Contents

1. [Introduction](#introduction)
2. [Physical Layer](#physical-layer)
3. [Frame Format](#frame-format)
4. [Device Architecture](#device-architecture)
5. [Startup Sequence](#startup-sequence)
6. [Serial Number Authentication](#serial-number-authentication)
7. [Parameter Exchange Protocol](#parameter-exchange-protocol)
8. [Joystick Control](#joystick-control)
9. [Common Frame Reference](#common-frame-reference)
10. [Control Override Methods](#control-override-methods)
11. [Security Analysis](#security-analysis)
12. [Tools & Setup](#tools--setup)

---

## Introduction

R-Net is a proprietary CAN bus protocol developed by PG Drives Technology (now part of Curtiss-Wright) for power wheelchair control systems. This document describes the protocol as reverse-engineered from actual wheelchair systems.

**Disclaimer:** This research is intended for accessibility purposes - enabling alternative control methods for wheelchair users. Always prioritize safety when working with mobility equipment.

### What is R-Net?

R-Net connects various wheelchair modules:
- **JSM** (Joystick Module) - User input device
- **PM** (Power Module) - Main controller, motor driver
- **IOM** (Input/Output Module) - Auxiliary I/O
- **BTM** (Bluetooth Module) - Wireless connectivity
- **ILM** (Indicator Light Module) - Turn signals, hazards
- **cJSM** (Color JSM) - JSM with color display

---

## Physical Layer

### CAN Bus Specifications

| Parameter | Value |
|-----------|-------|
| Protocol | CAN 2.0B |
| Bitrate | 125 Kbps |
| Frame Types | Standard (11-bit) and Extended (29-bit) |

### Connector Pinout

R-Net uses a 4-pin connector (female/device side view):
```
  ┌───┬───┐
  │ 1 │ 2 │
  ├───┼───┤
  │ 3 │ 4 │
  └───┴───┘

Pin 1: CAN Lo (CAN_L)
Pin 2: CAN Hi (CAN_H)
Pin 3: +24VDC Power
Pin 4: Ground (GND)
```

### Termination

Standard 120Ω termination at each end of the bus.

---

## Frame Format

R-Net uses the standard CAN frame format. In `cansend` notation:

```
<can_id>#<data>           Standard data frame
<can_id>#R                Remote Transmission Request (RTR)
```

### Frame ID Conventions

| ID Length | Type | Usage |
|-----------|------|-------|
| 3 hex chars (11-bit) | Standard | Control, mode, profile frames |
| 8 hex chars (29-bit) | Extended | Data, serial, config frames |

### Priority

Lower CAN ID = Higher priority. Critical frames use low IDs:
- `0x000` - Sleep commands (highest priority)
- `0x00C` - Network test
- `0x00E` - Serial heartbeat
- `0x020` - Joystick position

---

## Device Architecture

### Network Topology

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│   JSM   │────│   PM    │────│   IOM   │
│ Slot 1  │     │ Slot 0  │     │ Slot 2  │
└─────────┘     └─────────┘     └─────────┘
                    │
              ┌─────┴─────┐
              │           │
          ┌───────┐   ┌───────┐
          │  BTM  │   │  ILM  │
          │Slot 3 │   │Slot 4 │
          └───────┘   └───────┘
```

### Device Slots

Devices are assigned slots 0-F during enumeration:
- Slot 0: Power Module (PM) - always present
- Slot 1: Joystick Module (JSM) - primary input
- Slot 2+: Additional modules (IOM, BTM, ILM, etc.)

---

## Startup Sequence

### Complete Power-On Handshake

```
Time    JSM                              PM
─────────────────────────────────────────────────────
  0ms   ──[00C#]──────────────────────>  (test network)
 20ms   ──[00E#serial...]─────────────>  (serial heartbeat, 50ms)
 21ms                    <──────────────  [7B3#R] (request s/n exchange)
 25ms                    <──────────────  [1F00KK##R] (challenge seq 0)
        ...8 challenge/response pairs...
 50ms   ──[1F01KKSS#]─────────────────>  (response seq 0)
        ...
100ms   ──[03C30F0F#87...]────────────>  (heartbeat, 100ms)
150ms                    <──────────────  [7B1#] (config mode 1)
200ms                    <──────────────  [7B0#] (config mode 0)
250ms   ──[040#00000000]──────────────>  (open param page)
300ms   ──[781#20810000...]───────────>  (request params)
350ms                    <──────────────  [790#41810000...] (param response)
400ms   ──[041#80000000]──────────────>  (close param page)
450ms                    <──────────────  [050#...] (mode map)
500ms   ──[061#00400000]──────────────>  (select drive mode)
600ms                    <──────────────  [0C180000#0101] (motor enabled)
700ms   ──[02000100#0000]─────────────>  (joystick centered, 10ms)
```

### OBP Mode Entry (On-Board Programming)

If OBP Keycode Entry is enabled (OEM setting), users can enter programming mode via button combo:

1. Hold Horn + On/Off → short bleep
2. Release Horn, keep On/Off → two more bleeps
3. Release On/Off → long bleep (OBP active)

On the CAN bus, this triggers a mode change to Mode 8 (reserved for OBP):
```
TX: 061#40400000     ; Suspend current mode
TX: 061#00480000     ; Select mode 8 (OBP)
```

In OBP, joystick position frames (`02000X00`) **stop** (driving disabled). The JSM sends parameter requests on `0x781`, PM responds on `0x790`. The same parameter exchange protocol used during startup is repurposed for reading/writing configuration values. OBP provides dealer-level access (speed, accel, torque, tremor — not motor voltage or OEM params).

OBP exits after 5 minutes of inactivity. See `docs/OBP_ENABLE_GUIDE.md`.

---

## Serial Number Authentication

### Overview

Each device has an 8-byte serial number. Authentication uses XOR-based key derivation - **not cryptographically secure**.

### Frame ID Structure (29-bit Extended)

```
0x1F [SEQ][SLOT] [KEY][VALUE]
     │    │      │    │
     │    │      │    └── Serial byte or challenge value
     │    │      └─────── Derived key
     │    └────────────── Device slot (0-F)
     └─────────────────── Sequence number (0-7)
```

### Key Derivation Algorithm

```
key[seq] = serial[seq] XOR xor_table[seq]
```

Where:
- `serial[seq]` = byte `seq` of the device serial number
- `xor_table[seq]` = byte `seq` of the network's XOR table
- `key[seq]` = the key used in frame ID for sequence `seq`

### Known XOR Tables

**Table A - Standalone JSM Network:**
```
Serial:    08 90 1C 8A 00 00 00 00
XOR Table: 00 21 02 CC DD 12 7B 45
Keys:      08 B1 1E 46 DD 12 7B 45
```

**Table B - M300 Multi-Device Network:**
```
Serial:    50 C0 1C 8F 00 00 00 00
XOR Table: 83 52 AD 1B ED 06 2C 4E
Keys:      D3 92 B1 94 ED 06 2C 4E
```

### Authentication Flow

```
1. JSM broadcasts serial heartbeat:
   00E#08901C8A00000000

2. PM sends 8 RTR challenges (values ignored by device):
   1F0008XX#R  (seq 0, key=08)
   1F10B1XX#R  (seq 1, key=B1)
   ...

3. JSM responds with serial bytes:
   1F010808#   (seq 0, key=08, serial[0]=08)
   1F11B190#   (seq 1, key=B1, serial[1]=90)
   ...

4. PM validates responses against stored serials
```

### Security Weakness

The challenge value in RTR frames is **completely ignored** by devices. They respond based solely on the key in the frame ID. This means:
- No replay protection
- XOR table can be extracted from any capture
- Any device can be impersonated if XOR table is known

---

## Parameter Exchange Protocol

### Frame Assignments

| Request | Response | Device |
|---------|----------|--------|
| 0x780 | 0x790 | PM (Slot 0) |
| 0x781 | 0x791 | JSM (Slot 1) |
| 0x782 | 0x792 | Slot 2 |
| 0x783 | 0x793 | Slot 3 |
| 0x78F | 0x793 | R-Net Programmer |

### Frame Data Structure

```
Byte 0: Command
  0x20 = Open page / Set pointer
  0x40 = Request data
  0x41 = ACK (pointer exists)
  0x21 = Response with data
  0xC1 = Error (address not found)
  0x83 = ICS read address
  0x8F = ICS operation complete

Byte 1: Register
  0x80 = Page 0 (main config)
  0x81 = Pointer register
  0x8F = Data register
  0x8C = Text data (display strings)
  0x40 = Mode 0 info
  0x50 = Mode status

Bytes 2-3: Usually 0x0000

Bytes 4-7: Parameter ID or Value (little-endian)
```

### Example: Reading a Parameter

```
JSM: 781#2081000006000100   ; Set pointer to param 06, sub 01
PM:  790#4181000000000000   ; ACK - pointer exists
JSM: 781#408F000000000000   ; Request data at pointer
PM:  790#218F000084B20000   ; Return value 0xB284
```

---

## Joystick Control

### Position Frame

```
Frame ID: 02000X00 (extended)
          X = device slot (usually 1 for JSM)

Data: 2 bytes
  Byte 0: X-axis position (signed int8, -100 to +100)
  Byte 1: Y-axis position (signed int8, -100 to +100)

Timing: Every 10ms (100Hz)
```

### Position Values

| Value | Meaning |
|-------|---------|
| 0x00 | Center (0) |
| 0x64 | Full positive (+100) |
| 0x9C | Full negative (-100) |

### Examples

```
02000100#0000   Joystick centered
02000100#0064   Full forward
02000100#009C   Full reverse
02000100#6400   Full right
02000100#9C00   Full left
02000100#4832   Forward + right diagonal
```

---

## Common Frame Reference

### Periodic Frames

| Frame | Period | Description |
|-------|--------|-------------|
| `00E#SSSSSSSS00000000` | 50ms | Serial heartbeat |
| `02000X00#XxYy` | 10ms | Joystick position |
| `03C30F0F#8787878787878787` | 100ms | JSM heartbeat |
| `0C140X00#Xx` | 1000ms | PM heartbeat |
| `1C0C0X00#Xx` | 1000ms | Battery level (0-100%) |
| `14300X00#LlHh` | 200ms | Motor current |
| `1C300X04#LlLlLlLlRrRrRrRr` | 1000ms | Distance counter |

### Event Frames

| Frame | Description |
|-------|-------------|
| `0A040X00#Pp` | Set speed (Pp = 0x00-0x64) |
| `0C040X00#` | Horn start |
| `0C040X01#` | Horn stop |
| `061#40400000` | Suspend current mode |
| `061#004M0000` | Select mode M |
| `181C0D00#LlNnLlNnLlNnLlNn` | Play tones |

### Power/Sleep Frames

| Frame | Description |
|-------|-------------|
| `000#R` | Sleep all devices |
| `000#` | Sleep acknowledgment |
| `00C#` | Test network connection |
| `1C240X00#` | Power down device |
| `1C240X01#` | Device ready |

### Lighting Frames

| Frame | Description |
|-------|-------------|
| `0C000401#` | Left turn signal |
| `0C000402#` | Right turn signal |
| `0C000403#` | Hazard lights |
| `0C000404#` | Flood lights |
| `0C000400#XxYy` | Lamp status bitmap |

Lamp bitmap values:
- `0x01` = Left
- `0x04` = Right
- `0x10` = Hazard
- `0x80` = Flood

---

## Control Override Methods

### Method 1: JSMerror

Trigger a network error on the JSM, causing it to stop sending joystick frames. Then inject your own.

```python
# Send frame that causes JSM network error
cansend("0C000100#")

# JSM stops sending 02000100# frames
# Now inject your own joystick frames
while True:
    cansend("02000100#" + position_data)
    sleep(0.01)
```

**Pros:** Reliable takeover
**Cons:** JSM must be present; JSM retains speed control

### Method 2: FollowJSM

Wait for legitimate joystick frame, immediately send spoofed frame. If within 1ms, PM accepts it.

```python
while True:
    frame = canwait("02000100")  # Wait for JSM frame
    cansend("02000100#" + my_position)  # Immediately send ours
```

**Pros:** JSM can still function; seamless handoff
**Cons:** Timing-sensitive; occasional control drops

### Method 3: EmulateJSM

Replay the complete startup handshake to impersonate a JSM.

**Pros:** No JSM required
**Cons:** Only works with serials the PM has seen before

---

## Security Analysis

### Vulnerabilities

| Vulnerability | Severity | Description |
|--------------|----------|-------------|
| No encryption | Critical | All traffic is plaintext |
| Weak authentication | Critical | XOR-based, challenge ignored |
| Timing attacks | High | FollowJSM exploit |
| Error injection | High | JSMerror exploit |
| No message authentication | High | Any device can send any frame |

### Attack Vectors

1. **Passive eavesdropping** - Extract XOR tables, learn serial numbers
2. **Frame injection** - Send malicious control frames
3. **Device impersonation** - Spoof any device with known serial
4. **Denial of service** - Flood bus with high-priority frames

### Mitigations

For researchers working on wheelchair accessibility:
- Always have physical emergency stop
- Test in controlled environment first
- Implement software safety limits
- Monitor for unexpected behavior

---

## Tools & Setup

### Hardware Options

**Raspberry Pi + PiCAN2 (~$115)**
```bash
# /boot/config.txt
dtparam=spi=on
dtoverlay=mcp2515-can0-overlay,oscillator=16000000,interrupt=25

# Bring up interface
sudo ip link set can0 up type can bitrate 125000
```

**Arduino + SparkFun CAN Shield (~$75)**
- Flash SLCAN firmware
- Connect as `/dev/ttyUSB0`

### Software Tools

```bash
# Monitor bus
candump can0 -L

# Send frame
cansend can0 02000100#0064

# Generate random frames (fuzzing)
cangen can0 -e -g 10 -v

# Wait for specific frame
candump -n 1 can0,7b3:7ff

# Analyze with Wireshark
wireshark -i can0
```

### Python Library

```python
from can2RNET import *

# Open CAN socket
sock = opencansocket(0)

# Send joystick frame
cansend(sock, "02000100#0064")

# Wait for frame
frame = canwait(sock, "02000100")
print(dissect_frame(frame))
```

---

## References

- DEFCON24 Presentation (2016) - Stephen Chavez & Specter
- `RNET_FRAME_DICTIONARY.md` - Complete frame reference
- `wireshark/` - Packet captures for analysis
- `can2RNET/` - Python library source

---

## License & Disclaimer

This documentation is provided for educational and accessibility research purposes. The authors are not responsible for any misuse. Always prioritize safety when working with mobility equipment.

**Remember:** Wheelchairs are critical medical devices. Test thoroughly and always have a physical emergency stop available.
