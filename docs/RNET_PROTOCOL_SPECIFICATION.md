# R-Net Protocol Specification

**Version:** 1.0
**Date:** January 2026
**Authors:** Stephen Chavez, Specter
**Source:** Firmware reverse engineering, CAN bus captures, DEFCON24 research

### Official Internal Terminology

Reverse engineering of the R-Net Programmer software (DongleInterface.dll v3.0.0.0, PG Drives Technology) reveals the following official internal names for protocol layers:

| Official Name | Full Name | Maps To |
|---------------|-----------|---------|
| **REBUS** | (R-Net transport/protocol layer) | The overall R-Net protocol and bus system |
| **POP** | Parameter Object Protocol | The 0x78X/0x79X parameter exchange and programmer protocol (Section 8, 9) |
| **ODI** | Object Dictionary Interface | Memory classification system for device configuration (EEPROM, RAM, ROM, etc.) |

These names appear in the DLL's class hierarchy and string tables, confirming they are the manufacturer's internal designations.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Physical Layer](#2-physical-layer)
3. [Data Link Layer](#3-data-link-layer)
4. [Frame Structure](#4-frame-structure)
5. [Device Identification](#5-device-identification)
6. [Startup & Authentication](#6-startup--authentication)
7. [Joystick Control Protocol](#7-joystick-control-protocol)
8. [Parameter Exchange Protocol](#8-parameter-exchange-protocol)
9. [R-Net Programmer Protocol](#9-ics-programmer-protocol)
10. [Configuration Data Format](#10-configuration-data-format)
11. [Mode & Profile System](#11-mode--profile-system)
12. [Audio Protocol](#12-audio-protocol)
13. [Display Protocol (cJSM)](#13-display-protocol-cjsm)
14. [Bluetooth Module Protocol](#14-bluetooth-module-protocol)
15. [Error Handling](#15-error-handling)
16. [Security Analysis](#16-security-analysis)
17. [Timing Requirements](#17-timing-requirements)
18. [Appendix A: Frame Dictionary](#appendix-a-frame-dictionary)
19. [Appendix B: XOR Tables](#appendix-b-xor-tables)
20. [Appendix C: Memory Map](#appendix-c-memory-map)

---

## 1. Overview

R-Net is a proprietary CAN-based protocol developed by PG Drives Technology (now part of Curtiss-Wright) for power wheelchair control systems. It provides communication between:

- **PM** (Power Module) - Main controller, motor driver
- **JSM** (Joystick Module) - User input device
- **cJSM** (Color JSM) - JSM with color display
- **LEDJSM** (LED JSM) - JSM with LED indicators
- **BTM** (Bluetooth Module) - Wireless connectivity
- **R-Net Programmer** - Configuration tool

### Protocol Stack

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4 - Application (POP / ODI)                       │
│   Joystick, Speed, Parameters, Profiles, Audio          │
│   POP = Parameter Object Protocol (0x78X/0x79X)         │
│   ODI = Object Dictionary Interface (memory classes)    │
├─────────────────────────────────────────────────────────┤
│ Layer 3 - Session (REBUS)                               │
│   Authentication, Device Enumeration, Slot Assignment   │
│   REBUS = R-Net transport/protocol layer                │
├─────────────────────────────────────────────────────────┤
│ Layer 2 - Addressing                                    │
│   Standard Frames (11-bit), Extended Frames (29-bit)    │
├─────────────────────────────────────────────────────────┤
│ Layer 1 - Physical                                      │
│   CAN 2.0B @ 125 Kbps                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Physical Layer

### 2.1 CAN Bus Specification

| Parameter | Value |
|-----------|-------|
| Standard | CAN 2.0B |
| Bit Rate | 125,000 bps |
| Termination | 120Ω at each end |
| Max Bus Length | ~40m (typical wheelchair) |
| Max Nodes | 16 (practical limit) |

### 2.2 Connector Pinout

**R-Net Connector (Female/Device Side):**
```
  ┌───┬───┐
  │ 1 │ 2 │
  ├───┼───┤
  │ 3 │ 4 │
  └───┴───┘

Pin 1: CAN Lo (CAN_L)
Pin 2: CAN Hi (CAN_H)
Pin 3: +24VDC Power
Pin 4: GND (Ground)
```

### 2.3 Electrical Characteristics

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| CAN_H (dominant) | 2.75 | 3.5 | 4.5 | V |
| CAN_L (dominant) | 0.5 | 1.5 | 2.25 | V |
| CAN_H (recessive) | 2.0 | 2.5 | 3.0 | V |
| CAN_L (recessive) | 2.0 | 2.5 | 3.0 | V |
| Differential (dominant) | 1.5 | 2.0 | 3.0 | V |
| Differential (recessive) | -0.5 | 0 | 0.05 | V |

### 2.4 MCU Implementation

R-Net devices use **Freescale/NXP HCS08** microcontrollers:

| Parameter | Value |
|-----------|-------|
| MCU Family | MC9S08DZ (likely) |
| Architecture | 8-bit HCS08 |
| CAN Controller | Integrated MSCAN |
| Flash | 60KB+ |
| Clock | 8 MHz bus clock |

**CAN Controller Registers (MSCAN @ 0x0140):**

| Register | Offset | Description |
|----------|--------|-------------|
| CANCTL0 | 0x00 | Control Register 0 |
| CANCTL1 | 0x01 | Control Register 1 |
| CANBTR0 | 0x02 | Bus Timing Register 0 |
| CANBTR1 | 0x03 | Bus Timing Register 1 |
| CANRFLG | 0x04 | Receiver Flag Register |
| CANTFLG | 0x06 | Transmitter Flag Register |

**Baud Rate Configuration (125Kbps):**
```
BRP = 4 (Prescaler)
TSEG1 = 12
TSEG2 = 3
SJW = 1
Sample Point = 80%
```

---

## 3. Data Link Layer

### 3.1 Frame Types

R-Net uses both standard (11-bit) and extended (29-bit) CAN frames:

| Type | ID Bits | Usage |
|------|---------|-------|
| Standard | 11 | Control, status, real-time data |
| Extended | 29 | Configuration, authentication, bulk transfer |

### 3.2 Priority Scheme

Lower CAN ID = Higher priority (CAN arbitration)

| Priority | ID Range | Usage |
|----------|----------|-------|
| Highest | 0x000-0x0FF | Network control, joystick |
| High | 0x100-0x1FF | Status, motor data |
| Medium | 0x200-0x5FF | Configuration |
| Low | 0x600-0x7FF | Parameters, programmer |

### 3.3 Frame ID Allocation

**Standard Frames (11-bit):**

| ID Range | Description |
|----------|-------------|
| 0x00C-0x00F | Network test/query |
| 0x02000X00 | Joystick position (X=slot) |
| 0x03C30F0F | Device heartbeat |
| 0x04X | Parameter page control |
| 0x05X-0x06X | Mode/profile exchange |
| 0x0A040X00 | Speed limit control |
| 0x0C040X00 | Horn control |
| 0x0C140X00 | Lights control |
| 0x14300X00 | Motor current |
| 0x181C0D00 | Audio tones |
| 0x1C0C0X00 | Battery status |
| 0x78X | Parameter request |
| 0x79X | Parameter response |
| 0x7A0 | Programmer announce |
| 0x7B0-0x7B3 | Config mode control |

**Extended Frames (29-bit):**

| ID Pattern | Description |
|------------|-------------|
| 0x0006C01F | Sleep reset (prevents CAN bus sleep) |
| 0x00E00000 | Serial number heartbeat |
| 0x1FssXXkk | Serial challenge/response |
| 0x1ECmmXtt | Mode configuration |
| 0x1E3X0001 | Transfer header |
| 0x1E4E0001 | Transfer data |
| 0x1FB0000X | Device enumeration |

---

## 4. Frame Structure

### 4.1 Standard Frame Format

```
┌──────────┬──────────┬─────────────────────────────────┐
│ ID (11b) │ DLC (4b) │ Data (0-8 bytes)                │
└──────────┴──────────┴─────────────────────────────────┘
```

### 4.2 Extended Frame Format

```
┌──────────┬───┬──────────┬─────────────────────────────┐
│ ID (29b) │IDE│ DLC (4b) │ Data (0-8 bytes)            │
└──────────┴───┴──────────┴─────────────────────────────┘
```

### 4.3 Common Frame Structures

**Joystick Frame (0x02000X00):**
```
Byte 0: X position (int8, -100 to +100)
Byte 1: Y position (int8, -100 to +100)
```

**Parameter Frame (0x78X/0x79X):**
```
Byte 0: Command
Byte 1: Register
Byte 2-3: Reserved (0x0000)
Byte 4-7: Value (little-endian)
```

**Serial Heartbeat (0x00E):**
```
Byte 0-3: Serial number (32-bit)
Byte 4-7: Reserved (0x00000000)
```

---

## 5. Device Identification

### 5.1 Device Types

**Known device IDs (from firmware dumps):**

| Device ID | Name | Description |
|-----------|------|-------------|
| 0x0000 | BTMouse | Bluetooth Mouse Module |
| 0x6380 | LEDJSM | LED Joystick Module |
| 0x00XX | PM | Power Module |
| 0x01XX | JSM | Standard Joystick Module |

**Additional device types (from R-Net Programmer software / DongleInterface.dll):**

| Abbreviation | Full Name | Description |
|--------------|-----------|-------------|
| ISM | Intelligent Seating Module | 6-channel actuator control + lighting |
| ISM-8 / CxSM | Extended Seating Module | 8-channel extended seating control |
| IOM | Input/Output Module | General-purpose I/O expansion |
| Omni | Omni Input Module | Sip-and-puff, IR, and scanning input device |
| ASM | Advanced Stability Module | Accelerometer-based stability control |
| Tilt Module | Tilt Module | Seat tilt position sensing/control |
| Gyro Module | Gyro Module | PID-based gyroscopic stabilization |
| Encoder Module | Encoder Module | Motor feedback/position encoder |
| DTT | Dealer Test Tool | Handheld programmer/diagnostic tool |

### 5.2 Slot Assignment

Each device is assigned a slot (0-F) on the network:

| Slot | Device | Request ID | Response ID |
|------|--------|------------|-------------|
| 0 | PM (Power Module) | 0x780 | 0x790 |
| 1 | JSM (Joystick) | 0x781 | 0x791 |
| 2 | Device 2 | 0x782 | 0x792 |
| 3 | Device 3 | 0x783 | 0x793 |
| ... | ... | ... | ... |
| F | R-Net Programmer | 0x78F | 0x793 |

### 5.3 Serial Number Format

8-byte serial number, first 4 bytes are unique:

```
Example: 08 90 1C 8A 00 00 00 00
         └──┬───┘ └──────┬─────┘
           Unique      Padding
```

---

## 6. Startup & Authentication

### 6.1 Power-On Sequence

```
Time    Device  Frame                    Description
────────────────────────────────────────────────────────────
0ms     JSM     00C#                     Test network connection
10ms    PM      (any response)           Network present
50ms    JSM     00E#SSSSSSSS00000000     Serial heartbeat start
        JSM     (repeat every 50ms)      Continuous heartbeat
100ms   PM      7B3#R                    Request serial confirm
        PM      1F00kkcc#R               Challenge sequence 0
150ms   JSM     7B3#R                    Respond to request
        JSM     1F01kk00#ss              Serial byte 0 response
        (repeat for sequences 1-7)
400ms   JSM     03C30F0F#8787878787...   Device heartbeat start
        JSM     (repeat every 100ms)
500ms   PM      7B0#                     Enter parameter mode
        PM      04X#0...                 Open parameter page
        JSM     78X#2X81...              Request parameters
        PM      79X#...                  Parameter response
        JSM     04X#8000...              Close parameter page
600ms   PM      05X#XX...                Mode map
        JSM     06X#XX...                Request profile
800ms   JSM     02000X00#XxYy            Joystick active (10ms)
```

### 6.2 Authentication Protocol

R-Net uses XOR-based key derivation for device authentication.

**Frame ID Structure (29-bit Extended):**
```
0x1F [SEQ] [SLOT] [KEY] [VALUE]
     │     │      │     │
     │     │      │     └── Serial byte (response) or challenge
     │     │      └──────── Derived key
     │     └─────────────── Device slot (0-F)
     └───────────────────── Sequence (0-7)
```

**Key Derivation:**
```python
def derive_key(serial: bytes, xor_table: bytes, seq: int) -> int:
    """
    key[seq] = serial[seq] XOR xor_table[seq]
    """
    return serial[seq] ^ xor_table[seq]
```

**Challenge/Response Exchange:**
```
Sequence  PM Challenge (RTR)    JSM Response
────────────────────────────────────────────────
0         1F00 08 2F #R         1F01 08 08    (key=08, serial[0]=08)
1         1F10 B1 00 #R         1F11 B1 90    (key=B1, serial[1]=90)
2         1F20 1E 0E #R         1F21 1E 1C    (key=1E, serial[2]=1C)
3         1F30 46 48 #R         1F31 46 8A    (key=46, serial[3]=8A)
4         1F40 DD 00 #R         1F41 DD 00    (key=DD, serial[4]=00)
5         1F50 12 00 #R         1F51 12 00    (key=12, serial[5]=00)
6         1F60 7B 00 #R         1F61 7B 00    (key=7B, serial[6]=00)
7         1F70 45 00 #R         1F71 45 00    (key=45, serial[7]=00)
```

### 6.3 XOR Tables

Different networks/PMs use different XOR tables:

**Table A (Standalone JSM):**
```
Index:     0    1    2    3    4    5    6    7
Table:    00   21   02   CC   DD   12   7B   45
Serial:   08   90   1C   8A   00   00   00   00
Keys:     08   B1   1E   46   DD   12   7B   45
```

**Table B (M300 Network):**
```
Index:     0    1    2    3    4    5    6    7
Table:    83   52   AD   1B   ED   06   2C   4E
Serial:   50   C0   1C   8F   00   00   00   00
Keys:     D3   92   B1   94   ED   06   2C   4E
```

**Table C (BTM Module):**
```
Index:     0    1    2    3    4    5    6    7
Keys:     47   A1   62   AD   2E   05   B3   EC
```

**Firmware Location:** XOR tables found at address 0x0706 in LEDJSM firmware.

---

## 7. Joystick Control Protocol

### 7.1 Joystick Position Frame

**Frame ID:** 0x02000X00 (X = device slot)

**Data Format:**
```
Byte 0: X position (int8, signed)
Byte 1: Y position (int8, signed)

Values:
  -100 (0x9C) = Full left/reverse
     0 (0x00) = Center
  +100 (0x64) = Full right/forward
```

**Transmission Rate:** Every 10ms (100 Hz)

**Examples:**
```
02000100#0064    Full forward
02000100#6400    Full right
02000100#009C    Full reverse
02000100#9C00    Full left
02000100#0000    Centered (stopped)
02000100#3232    Diagonal (50%, 50%)
```

### 7.2 Speed Limit Frame

**Frame ID:** 0x0A040X00

**Data Format:**
```
Byte 0: Speed percentage (0x00-0x64 = 0-100%)
```

**Examples:**
```
0A040100#32      Set speed to 50%
0A040100#64      Set speed to 100%
0A040100#00      Set speed to 0% (stopped)
```

### 7.3 Control Override Methods

Three methods to override JSM control:

**1. JSMerror Method:**
- Trigger network error on JSM
- JSM stops sending joystick frames
- Inject replacement frames

**2. FollowJSM Method:**
- Monitor for JSM joystick frame
- Send spoofed frame within 1ms
- PM accepts spoofed frame

**3. EmulateJSM Method:**
- Disconnect physical JSM
- Replay complete startup handshake
- Requires known serial number

---

## 8. Parameter Exchange Protocol (POP)

> **Official name:** POP (Parameter Object Protocol), as identified in DongleInterface.dll v3.0.0.0.
> The parameter exchange uses the REBUS transport layer for frame routing.

### 8.1 Frame IDs

| Direction | ID Pattern | Description |
|-----------|------------|-------------|
| Request | 0x78X | Parameter request (X=slot) |
| Response | 0x79X | Parameter response (X=slot) |

### 8.2 Command Bytes

**Request Commands (Byte 0):**

| Command | Value | Description |
|---------|-------|-------------|
| OPEN | 0x20 | Open parameter page |
| REQUEST | 0x40 | Request value at pointer |
| HEARTBEAT | 0x42 | Presence/polling request |
| SET_ADDR | 0x83 | Set memory address |
| READ | 0x03 | Start read operation |
| WRITE | 0x43 | Start write operation |

**Response Commands (Byte 0):**

| Command | Value | Description |
|---------|-------|-------------|
| DATA | 0x21 | Data value response |
| HB_ACK | 0x2F | Heartbeat acknowledgment |
| ACK | 0x41 | General acknowledgment |
| READ_RSP | 0x4F | Read data response |
| WRITE_RSP | 0x0F | Write acknowledgment |
| COMPLETE | 0x8F | Operation complete |
| ERROR | 0xC1 | Error response |

### 8.3 Register Types

| Register | Value | Description |
|----------|-------|-------------|
| PAGE0 | 0x80 | Page control |
| POINTER | 0x81 | Address pointer |
| TEXT | 0x8C | Text/string data |
| DATA | 0x8F | Parameter value |

### 8.4 Frame Data Structure

```
Byte 0: Command
Byte 1: Register
Byte 2: Reserved (0x00)
Byte 3: Reserved (0x00)
Byte 4-7: Value (little-endian 32-bit)
```

### 8.5 Parameter Exchange Example

```
; Check if parameter 0x0601 exists
TX: 781#20 81 00 00 06 00 01 00   ; OPEN, pointer, param 0x0601
RX: 790#41 81 00 00 00 00 00 00   ; ACK, pointer exists

; Request parameter value
TX: 781#40 8F 00 00 00 00 00 00   ; REQUEST, data register
RX: 790#21 8F 00 00 84 B2 00 00   ; DATA, value = 0x0000B284

; Close page
TX: 781#80 00 00 00 00 00 00 00   ; Close page
```

---

## 9. R-Net Programmer Protocol

### 9.1 Overview

The R-Net Programmer is a commercial device for configuring R-Net electronics. It uses dedicated frame IDs and operates in a master/slave relationship with the PM.

### 9.2 Frame IDs

| ID | Direction | Description |
|----|-----------|-------------|
| 0x7A0 | Programmer → Bus | Presence announcement |
| 0x78F | Programmer → PM | Request frames |
| 0x793 | PM → Programmer | Response frames |

### 9.3 Programmer Handshake

```
; Step 1: Announce presence
TX: 7A0#                          ; Empty frame

; Step 2: Establish heartbeat (repeat every 200ms)
TX: 78F#42 20 00 FF 00 00 00 00   ; Heartbeat request
         │  │  │  │
         │  │  │  └── Device ID (FF = broadcast)
         │  │  └───── Reserved
         │  └──────── Register 0x20
         └─────────── Command: HEARTBEAT

RX: 793#2F 20 00 FF 00 00 00 00   ; Heartbeat ACK
```

### 9.4 Memory Read Protocol

```
; Set address to 0x0100
TX: 78F#83 00 01 FF 00 01 00 00
         │  │  │  │  └──┴──┴──┴── Address (little-endian)
         │  │  │  └────────────── Device ID
         │  │  └─────────────────  Sub-command
         │  └────────────────────  Reserved
         └───────────────────────  Command: SET_ADDR

; Start read
TX: 78F#03 00 01 FF 17 00 00 00   ; READ command

; Receive data (4 bytes)
RX: 793#4F 00 01 FF DD DD DD DD   ; READ_RSP with data
RX: 793#8F 00 01 FF 00 00 00 00   ; COMPLETE
```

### 9.5 Memory Write Protocol

```
; Set address to 0x0200
TX: 78F#83 00 01 FF 00 02 00 00   ; SET_ADDR

; Write data
TX: 78F#43 00 01 FF DE AD BE EF   ; WRITE with data

; Acknowledgment
RX: 793#0F 00 01 FF 41 00 00 00   ; WRITE_RSP, status=OK
RX: 793#8F 00 01 FF 00 00 00 00   ; COMPLETE
```

### 9.6 Error Responses

```
RX: 793#C1 81 00 00 28 00 00 00
         │  │        │
         │  │        └── Error code (0x28 = address not found)
         │  └─────────── Register that failed
         └────────────── Command: ERROR
```

| Error Code | Meaning |
|------------|---------|
| 0x00 | General error |
| 0x28 | Address not found |
| 0x41 | Success (in write response) |

---

## 10. Configuration Data Format

### 10.1 Memory Map

```
Address Range     Size      Description
──────────────────────────────────────────────────────────
0x0000 - 0x00FF   256B      Device Header
0x0100 - 0x015F   96B       Reserved
0x0160 - 0x016F   16B       Encryption/Auth Key
0x0170 - 0x01FF   144B      Reserved
0x0200 - 0x03FF   512B      Reserved
0x0400 - 0x04DF   224B      Active Configuration
0x04E0 - 0x0FFF   2848B     Profile/Extended Config
0x1000 - 0x3FFF   12KB      Extended Config (sentinel)
0x4000 - 0xFF7F   48KB      Firmware Code
0xFF80 - 0xFFFF   128B      Interrupt Vectors
```

### 10.2 Header Structure (0x0000-0x00FF)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x0000 | 2 | Device ID | Device type identifier |
| 0x0002 | 6 | Reserved | Zeros |
| 0x0008 | 4 | Flags | Device flags |
| 0x000C | 4 | Version | Firmware version |
| 0x0012 | 2 | Variant | Configuration variant |
| 0x0016 | 2 | Mode Flags | Operating mode |
| 0x0022 | 2 | Checksum | CRC/checksum |
| 0x0030 | 1 | Max Profiles | Maximum profile count |
| 0x0037 | 1 | Speed Limit | Default speed limit |
| 0x00FE | 1 | Features | Feature flags |

### 10.3 Configuration Region (0x0400+)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x0400 | 2 | Config Type | 0x1802 for LEDJSM |
| 0x040A | 6 | Slot Config | Slot enable flags |
| 0x0410 | 8 | Mode Config | Mode configuration |
| 0x0430 | 1 | Speed | Speed percentage (0-100) |
| 0x0438 | 8 | Control | Control byte array |
| 0x0444 | 2 | Device ID | Device identifier |

### 10.4 Sentinel Value

**Pattern:** 0x18A7

**Meaning:** Uninitialized/default configuration slot

**Usage:**
- Marks empty profile slots
- Indicates unused parameters
- Fills reserved memory regions

### 10.5 Key Storage (0x0160)

**BTMouse (encrypted config):**
```
FC 95 FE BA E3 1F 2D 04 EC 12 E6 FD EF 00 57 C1
```

**LEDJSM (no encryption):**
```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 E6 93
```

---

## 11. Mode & Profile System

### 11.0 Profile Numbering

R-Net supports an 8-profile system per mode:

| Profile | Number | Notes |
|---------|--------|-------|
| Profile 1 | 1 | Default/primary drive profile |
| Profile 2 | 2 | |
| Profile 3 | 3 | |
| Profile 4 | 4 | |
| Profile 5 | 5 | |
| Profile 6 | 6 | |
| Profile 7 | 7 | |
| Attendant | 8 | Attendant control profile (Profile 8) |

The Attendant profile (Profile 8) is a special profile intended for caregiver/attendant control. It has separate speed and motor current limits from the user profiles 1-7.

### 11.1 Mode Configuration Frames

**Frame ID Pattern:** 0x1ECmmXtt

```
0x1EC [Mode] [SubAddr] [Type]
      │      │         │
      │      │         └── Type: 00/40/60/61/62/80/C0/F0
      │      └──────────── Sub-address: 08/10/18/F0/etc
      └─────────────────── Mode index: 0-5
```

### 11.2 Type Suffixes

| Type | Description | Data |
|------|-------------|------|
| 0x00 | Initialization | Usually zeros |
| 0x40 | Config header | 0103000000000000 |
| 0x60 | Mode parameters | Device serials |
| 0x61 | Extended data | Additional params |
| 0x62 | XOR key data | Authentication |
| 0x80 | Status | Current state |
| 0xC0 | Flags | 0100000000000000 |
| 0xF0 | End flags | Termination |

### 11.3 Mode Change Protocol

```
; Change from Mode 0 to Mode 1
TX: 061#40 40 00 00    ; Suspend mode 0 (byte 1 = 0x40 + mode)
(wait 100ms)
TX: 061#00 41 00 00    ; Select mode 1 (byte 1 = 0x40 + mode)

; Mode byte encoding: 0x40=mode0, 0x41=mode1, ..., 0x48=mode8
```

### 11.3.1 OBP Mode (Mode 8)

**Mode 8 is reserved for OBP (On-Board Programming)** — the wheelchair's built-in configuration mode. OBP allows dealer-level parameter adjustment (speed, acceleration, deceleration, torque, tremor damping) directly from the JSM display.

**Activation — Hardware Dongle (original method, always works):**
1. Insert R-Net programming dongle (D50609 dealer / D50610 OEM) into bus
2. Power on → dongle detected, network reconfigures
3. Press Mode button to cycle to Mode 8

**Activation — Button Combo (requires "OBP Keycode Entry" = Yes):**
1. Hold Horn + On/Off button → wait for short bleep
2. Release Horn, keep On/Off → wait for two more bleeps
3. Release On/Off → long bleep confirms OBP active

**Note:** Per Permobil documentation (2012), OBP was originally designed to require a dongle. The button combo is an alternative gated by "OBP Keycode Entry", an OEM-level boolean in PM EEPROM that manufacturers may disable.

**Verification:** Press Mode button twice on JSM. If OBP is available, display shows "Speeds" (or "Speeds with ESP" if ESP personality loaded).

**CAN bus behavior in OBP mode:**
- Joystick position frames (`0x02000X00`) **stop** (driving disabled)
- JSM sends parameter requests on `0x781` (slot 1)
- PM responds on `0x790` (slot 0)
- Normal heartbeats (`0x00E`, `0x03C30F0F`) continue
- **5-minute inactivity timeout** exits OBP automatically

**OBP Keycode Entry:** An OEM-level boolean parameter in PM EEPROM (system config region, typically 0x0400-0x0600). When set to "No" (0x00), the button combo is disabled. Can be re-enabled via POP protocol. See `docs/OBP_ENABLE_GUIDE.md`.

**Access levels:**

| Level | Entry Method | Can Adjust |
|-------|-------------|------------|
| User OBP | Button combo | Speed, accel, decel, deadband, sleep timer |
| Dealer | D50609 dongle | Above + torque, power, tremor, throw, profiles |
| OEM | D50610 dongle | All parameters including motor voltage, compensation |

**Mode change to OBP:**
```
TX: 061#40 40 00 00    ; Suspend current mode (mode 0)
TX: 061#00 48 00 00    ; Select mode 8 (OBP)
```

**Controller Personality:** The OBP menu content is defined by a "Controller Personality" binary blob stored in the PM. Set via `Controller → Set Controller Personality` in the PC Programmer. Two known personalities: "Permobil ESP" (shows ESP speed params) and "PGDT Generic" (shows normal PM speed params). Transferred via segmented POP protocol. Source: "Reprogramming OBP menu v2.pdf" (Permobil, 2010).

**Source:** R-Net OBP Manual SK78571/4, R-Net Technical Manual SK77981/12, ICS Trouble Shooter manual v2 (Permobil, 2012)

### 11.4 Profile Selection

```
; Request profile via parameter exchange
TX: 781#20 81 00 00 [profile_id]
RX: 790#41 81 00 00 00 00 00 00
```

---

## 12. Audio Protocol

### 12.1 Tone Generation

**Frame ID:** 0x181C0D00

**Data Format (4 notes):**
```
Byte 0-1: Note 1 (length, pitch)
Byte 2-3: Note 2 (length, pitch)
Byte 4-5: Note 3 (length, pitch)
Byte 6-7: Note 4 (length, pitch)

Length: Duration in ~10ms units
Pitch: Frequency value (0x00-0xFF)
```

**Examples:**
```
181C0D00#0840085008440840    Play melody
181C0D00#1050105010501050    Alarm tone
```

---

## 13. Display Protocol (cJSM)

### 13.1 Text Transfer

Text is sent via parameter exchange using register 0x8C:

```
Request:  0x78X#20 8C XX XX ...
Response: 0x79X#20 8C XX XX [4 bytes ASCII]
```

**Data Format:**
```
Byte 0: 0x20 (command = data)
Byte 1: 0x8C (register = text)
Byte 2-3: 0x0000
Byte 4-7: ASCII text (4 characters)
```

### 13.2 Text Examples

```
208c000044726976 → "Driv"
208c000065202020 → "e   "
208c000053656174 → "Seat"
208c0000696e6720 → "ing "
```

### 13.3 Profile Prefixes

| Prefix | ASCII | Meaning |
|--------|-------|---------|
| 64646450 | dddP | Profile |
| 64646441 | dddA | Attendant |
| 64646447 | dddG | Godly |
| 6464644E | dddN | Noob |

### 13.4 cJSM Authentication

cJSM uses slot 8+ range (0x1F8X) for authentication:

```
; Authentication failure pattern
0x1F800010#, 0x1F800011#, 0x1F800012#, 0x1F800013#
0x1F810000#, 0x1FA00000#  ; Retry/error state
```

---

## 14. Bluetooth Module Protocol

### 14.1 BTM Identification

| Property | Value |
|----------|-------|
| Device ID | 0x0000 |
| Config | Encrypted (high entropy) |
| Key Location | 0x0160 |

### 14.2 BTM Status Frames

```
0x0A400002#    BTM Status 1
0x0A400102#    BTM Status 2
0x0A400300#    BTM Control 1
0x0A400301#    BTM Control 2
```

### 14.3 BTM Configuration

BTMouse config at 0x0400-0x1000 stores:
- Bluetooth pairing keys (128-bit)
- Paired device addresses
- Connection parameters

**Note:** BTMouse config is NOT encrypted with the 0x0160 key. The high entropy is from stored Bluetooth link keys (inherently random).

---

## 15. Error Handling

### 15.1 CAN Error Frames

R-Net devices handle standard CAN error frames:
- Bit errors
- Stuff errors
- CRC errors
- Form errors
- ACK errors

### 15.2 Protocol Errors

| Error | Response | Recovery |
|-------|----------|----------|
| Invalid command | 0xC1 ERROR | Retry |
| Address not found | 0xC1 + 0x28 | Check address |
| Timeout | No response | Retry with backoff |
| Authentication fail | No ACK | Re-authenticate |

### 15.3 Timeout Values

| Operation | Timeout |
|-----------|---------|
| Read response | 500ms |
| Write response | 500ms |
| Heartbeat | 200ms |
| Session | 2000ms |

---

## 16. Security Analysis

### 16.1 Vulnerabilities

| Vulnerability | Severity | Description |
|---------------|----------|-------------|
| No encryption | High | All frames plaintext |
| Weak authentication | High | XOR-based, predictable |
| No integrity check | Medium | Beyond CAN CRC |
| Broadcast addressing | Medium | 0xFF queries all |
| No code signing | Medium | Firmware modifiable |

### 16.2 Attack Vectors

**1. Passive Sniffing:**
- Capture all bus traffic
- Extract serial numbers
- Derive XOR tables

**2. Active Injection:**
- Spoof joystick frames
- Override speed limits
- Modify profiles

**3. Configuration Extraction:**
- Use programmer protocol
- Dump all memory
- Extract firmware

**4. Replay Attacks:**
- Capture authentication
- Replay startup sequence
- Impersonate devices

### 16.3 Mitigations (Recommendations)

| Mitigation | Implementation |
|------------|----------------|
| Bus isolation | Physical access control |
| Monitoring | Detect anomalous frames |
| Rate limiting | Prevent flooding |
| Secure boot | Code signing (requires HW change) |

---

## 17. Timing Requirements

### 17.1 Periodic Frame Intervals

| Frame Type | Interval | Tolerance |
|------------|----------|-----------|
| Joystick (02000X00) | 10ms | ±2ms |
| Serial heartbeat (00E) | 50ms | ±10ms |
| Device heartbeat (03C) | 100ms | ±20ms |
| Programmer heartbeat | 200ms | ±50ms |
| Battery status (1C0C) | 1000ms | ±100ms |

### 17.2 Protocol Timing

| Parameter | Value |
|-----------|-------|
| Inter-frame gap (min) | 1ms |
| Response timeout | 500ms |
| Session timeout | 2000ms |
| Authentication timeout | 1000ms |
| Startup sequence | ~800ms |

### 17.3 Timing Diagram

```
     0ms        50ms       100ms      200ms      500ms      800ms
      │          │          │          │          │          │
JSM   ├──00C#────┼──00E#────┼──00E#────┼──00E#────┼──00E#────┤
      │          │  (50ms)  │          │          │          │
PM    │          ├──7B3#R───┼──────────┼──────────┼──────────┤
      │          │          │          │          │          │
AUTH  │          │    ├─1F0X#─1F1X#─1F2X#─...─1F7X#─┤        │
      │          │          │          │          │          │
JSM   │          │          ├──03C#────┼──03C#────┼──03C#────┤
      │          │          │  (100ms) │          │          │
PARAM │          │          │          ├──78X#────┼──79X#────┤
      │          │          │          │          │          │
JOY   │          │          │          │          │  ├─02000X00#─
      │          │          │          │          │    (10ms)
```

---

## Appendix A: Frame Dictionary

### A.1 Standard Frames

| ID | Direction | DLC | Description |
|----|-----------|-----|-------------|
| 0x00C | JSM→PM | 0 | Network test |
| 0x00E | JSM→Bus | 8 | Serial heartbeat |
| 0x02000100 | JSM→PM | 2 | Joystick slot 1 |
| 0x03C30F0F | JSM→Bus | 8 | Device heartbeat |
| 0x040 | PM→Dev | 8 | Parameter page |
| 0x050 | PM→JSM | 8 | Mode map |
| 0x060 | JSM→PM | 8 | Mode request |
| 0x061 | Any | 4 | Mode change |
| 0x0A040100 | Any | 1 | Speed limit |
| 0x0C040100 | JSM→PM | 0-1 | Horn control |
| 0x0C140100 | Any | 1 | Lights |
| 0x14300100 | PM→Bus | 4 | Motor current |
| 0x181C0D00 | Any | 8 | Audio tones |
| 0x1C0C0100 | PM→Bus | 1 | Battery level |
| 0x780-0x78F | Req | 8 | Parameter request |
| 0x790-0x793 | Rsp | 8 | Parameter response |
| 0x7A0 | Prog | 0 | Programmer announce |
| 0x7B0-0x7B3 | PM | 0-8 | Config mode |

### A.2 Extended Frames

| ID Pattern | Description |
|------------|-------------|
| 0x0006C01F | Sleep reset (prevents CAN bus sleep mode) |
| 0x00E00000 | Serial heartbeat |
| 0x1F0X0000-0x1F7X0000 | Auth challenge/response |
| 0x1FB0000X | Device enumeration |
| 0x1EC00000-0x1EC5FFFF | Mode configuration |
| 0x1E3C0001-0x1E3F0003 | Transfer header |
| 0x1E4E0001-0x1E4E0002 | Transfer data |
| 0x1E800000-0x1E80000F | Transfer control |

---

## Appendix B: XOR Tables

### B.1 Known Tables

```python
XOR_TABLES = {
    # Table A - Standalone JSM (serial: 08901c8a)
    'standalone_jsm': [0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45],

    # Table B - M300 Network (serial: 50c01c8f)
    'm300_network': [0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E],

    # Table C - BTM Module
    'btm_module': [0x47, 0xA1, 0x62, 0xAD, 0x2E, 0x05, 0xB3, 0xEC],

    # Firmware table (0x0706)
    'firmware': [0x65, 0x55, 0xB8, 0xEC, 0xDD, 0x12, 0x7B, 0x45],
}
```

### B.2 Key Derivation Code

```python
def derive_keys(serial: bytes, xor_table: bytes) -> list[int]:
    """Derive authentication keys from serial and XOR table."""
    return [s ^ t for s, t in zip(serial[:8], xor_table)]

def build_auth_response(serial: bytes, xor_table: bytes, slot: int) -> list[tuple]:
    """Build complete authentication response sequence."""
    keys = derive_keys(serial, xor_table)
    frames = []
    for seq in range(8):
        frame_id = 0x1F000000 | (seq << 20) | (slot << 16) | (keys[seq] << 8) | serial[seq]
        frames.append((frame_id, serial[seq]))
    return frames
```

---

## Appendix C: Memory Map

### C.1 Full Address Space

```
00000000 ┌─────────────────────────────────────┐
         │ Device Header (256 bytes)           │
000000FF ├─────────────────────────────────────┤
         │ Reserved (96 bytes)                 │
0000015F ├─────────────────────────────────────┤
         │ Encryption Key (16 bytes)           │
0000016F ├─────────────────────────────────────┤
         │ Reserved (144 bytes)                │
000001FF ├─────────────────────────────────────┤
         │ Reserved (512 bytes)                │
000003FF ├─────────────────────────────────────┤
         │ Active Configuration (224 bytes)    │
000004DF ├─────────────────────────────────────┤
         │ Profile Config (2848 bytes)         │
         │ (includes XOR table at 0x0706)      │
00000FFF ├─────────────────────────────────────┤
         │ Extended Config (12KB)              │
         │ (filled with 0x18A7 sentinel)       │
00003FFF ├─────────────────────────────────────┤
         │ Firmware Code (~48KB)               │
         │ - Boot code at 0x4000               │
         │ - CAN handlers at 0x4200+           │
         │ - Data tables at 0x5500+            │
0000FF7F ├─────────────────────────────────────┤
         │ Interrupt Vectors (128 bytes)       │
         │ - Reset vector: 0x4000              │
         │ - CAN TX ISR: 0x429A                │
0000FFFF └─────────────────────────────────────┘
```

### C.2 Interrupt Vector Table

| Vector | Address | Handler | Function |
|--------|---------|---------|----------|
| 0xFFD2 | CAN TX | 0x429A | Transmit complete |
| 0xFFD4 | CAN RX | 0x448F | Receive handler |
| 0xFFC4 | Timer | 0x449C | Timer overflow |
| 0xFFB2 | SCI RX | 0x435A | Serial receive |
| 0xFFFE | Reset | 0x4000 | System reset |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01 | Initial release from firmware RE |
| 1.1 | 2026-03 | Added official POP/REBUS/ODI terminology from R-Net Programmer RE; added device types from DongleInterface.dll; added 8-profile system; added sleep reset frame |

---

*This specification was reconstructed through reverse engineering of R-Net firmware dumps and CAN bus traffic analysis. It is intended for accessibility research to enable alternative wheelchair control methods.*

*Authors: Stephen Chavez & Specter*
*DEFCON24 Presentation: August 2016*
