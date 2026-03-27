# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an R-Net CAN bus research and accessibility project for power wheelchairs. It enables alternative control methods (USB joystick, Xbox controller, network-based control) for wheelchairs using R-Net electronics. The project was presented at DEFCON24 (August 2016).

**Authors:** Stephen Chavez & Specter

## Key Components

### can2RNET (Primary Library)
The `can2RNET/` directory contains the main Python library for R-Net CAN communication:
- `can2RNET.py` - Core library providing SocketCAN interface functions (`build_frame`, `dissect_frame`, `cansend`, `canwait`, `opencansocket`)
- `JoyLocal.py` - USB joystick to R-Net translation (main user-facing script)
- `JoyLocal_usingJSMexploit.py` - Alternative using JSM error exploit method
- `reference/RNET_FRAME_DICTIONARY.md` - Comprehensive CAN frame reference (590+ entries)

### R-Net Connector Pinout (Female/Device side)
```
  1   2
  3   4

1) CAN Lo
2) CAN Hi
3) +24VDC
4) GND
```

### Hardware Configurations

**Raspberry Pi 3 + PiCAN2 (~$115):**
- Pi3 + PiCAN2 w/ SMPS from skpang
- Uses MCP2551 + MCP2515, interrupt driven
- WiFi + 1A power = self-contained unit

```bash
# Add to /boot/config.txt
dtparam=spi=on
dtoverlay=mcp2515-can0-overlay,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay

# Bring up CAN interface
sudo ip link set can0 up type can bitrate 125000
```

**Arduino UNO + SparkFun CANshield (~$75):**
- `can2RNET/slcan_sketchbook/slcan/slcan.ino` - SLCAN firmware (if present)
- Uses MCP2515 CAN controller, default 125kbps bitrate
- Install as SLCAN to use with SocketCAN (note: can hang occasionally)

**PlatformIO (new/):**
- SparkFun Redboard target with CAN bus library
- Build: `platformio run` in `new/` directory

## CAN Frame Format

Messages use "cansend" format from can-utils:
```
<can_id>#{R|data}          # CAN 2.0 frames
<can_id>##<flags>{data}    # CAN FD frames

# Examples:
5A1#11.2233.44556677.88   # Standard frame with data
123#DEADBEEF              # Standard frame
1F334455#1122334455667788 # Extended frame (8 hex chars)
123#R                     # Remote transmission request
```

## Common Operations

```bash
# Monitor CAN bus
candump can0 -L

# Send CAN frame (play tune)
cansend can0 181C0D00#0840085008440840

# Horn beep
cansend can0 0C040100#; sleep .2; cansend can0 0c040101#

# Set max power to 50%
cansend can0 0A040100#32

# Random battery levels (for testing UI)
cangen can0 -I 1C0C0100 -L 1 -e -g 100

# Change from mode 0 to mode 1
cansend can0 061#40400000; sleep .1; cansend can0 061#00410000

# Fuzz bus with random extended frames
cangen can0 -e -g 10 -v -v

# Wait for specific CAN ID
candump -n 1 can0,7b3:7ff

# Run joystick control (FollowJSM method)
python3 can2RNET/JoyLocal.py

# Run joystick control (JSMerror method)
python3 can2RNET/JoyLocal_usingJSMexploit.py
```

## R-Net Protocol Notes

R-Net uses CAN 2.0B at 125Kbps. Frame ID represents priority (lowest wins).

### Key Frame Types

**Periodic frames:**
- `02000X00#XxYy` - Joystick position (every 10ms), X=device, XxYy=position as int8
- `00E#XXXXXXXX00000000` - JSM serial number heartbeat (every 50ms)
- `03C30F0F#8787878787878787` - JSM device heartbeat (every 100ms)
- `14300X00#LlHh` - Drive motor current, little-endian 16-bit (every 200ms)
- `1C0C0X00#Xx` - Battery level 0x00-0x64 (every 1000ms)

**Event frames:**
- `0C040X00#` / `0C040X01#` - Horn start/stop
- `0A040100#Pp` - Set max speed (0x00-0x64 = 0-100%)
- `181C0D00#LlNnLlNnLlNnLlNn` - Play tones (Ll=length, Nn=note)
- `061#40400000` then `061#00410000` - Change mode 0→1

**Startup/config frames:**
- `00C#` - JSM test if connected to R-Net (checks for ACK)
- `7B3#` / `7B3#R` - Serial number exchange request
- `7B1#` / `7B0#` - Drop to config mode 1/0
- `1F[seq][slot][key][val]#` - Serial number challenge/response (see algorithm below)
- `1fb0000X#` - Device enumeration (full 8-byte serial for slot X)

See `RNET_FRAME_DICTIONARY.md` for comprehensive frame reference (compiled from all research).

## Control Override Methods

Three confirmed methods to take control from the JSM:

### 1. JSMerror (`JoyLocal_usingJSMexploit.py`)
Trigger JSM network error - JoyXY frames stop, then inject your own.
- (-) JSM must be present and turned on
- (-) Drive control disabled on JSM, but JSM can still control speed

### 2. FollowJSM (`JoyLocal.py`)
Wait for JoyXY frame, immediately send spoofed frame. If done within 1ms, PM accepts it.
- (-) Occasionally drops control for a few seconds due to late frame
- (+) JSM can still provide drive control if allowed in code

### 3. EmulateJSM (experimental)
Disconnect JSM, replay wakeup handshake to spoof a JSM.
- (+) No JSM required
- (-) Only works with JSM serial numbers the PM has seen before

### JSM/PM Startup Handshake
```
JSM                                    PM
 |--[00C#] check network connection--->|
 |--[00E#XXXX...] s/n heartbeat 50ms-->|
 |                                     |--[7B3#R] request s/n confirm
 |                                     |--[1FXXXXXX#R] s/n challenge
 |--[7B3#R] respond to challenge------>|
 |--[03C30F0F#87...] heartbeat 100ms-->|
 |                                     |--[7B0#] parameter exchange mode
 |                                     |--[04X#0...] open parameter page
 |--[78X#2X81...] request param------->|
 |                                     |--[79X#...] param response
 |--[04X#8000...] close param page---->|
 |<-[05X#XX...] mode map---------------|
 |--[06X#XX...] request profile------->|
 |--[02000X00#XxYy] joystick 10ms----->| (user mode)
```

### Serial Number Challenge/Response Algorithm

The serial number exchange uses XOR-based key derivation:

**Frame ID Structure (29-bit Extended):**
```
0x1F [SEQ][SLOT] [KEY][VALUE]
     │    │      │    │
     │    │      │    └── Serial byte (response) or challenge (RTR)
     │    │      └─────── Key = serial[seq] XOR xor_table[seq]
     │    └────────────── Device slot on network (0-F)
     └─────────────────── Sequence number (0-7)
```

**Key Derivation Formula:**
```
key[seq] = serial[seq] XOR xor_table[seq]
```

**Verified XOR Tables:**

*Table A (Standalone JSM, serial 08901c8a):*
```
xor_table = [0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45]
serial    = [0x08, 0x90, 0x1C, 0x8A, 0x00, 0x00, 0x00, 0x00]
keys      = [0x08, 0xB1, 0x1E, 0x46, 0xDD, 0x12, 0x7B, 0x45]
```

*Table B (M300 Network, serial 50c01c8f):*
```
xor_table = [0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E]
serial    = [0x50, 0xC0, 0x1C, 0x8F, 0x00, 0x00, 0x00, 0x00]
keys      = [0xD3, 0x92, 0xB1, 0x94, 0xED, 0x06, 0x2C, 0x4E]
```

*Table C (BTM Network - different module type):*
```
keys      = [0x47, 0xA1, 0x62, 0xAD, 0x2E, 0x05, 0xB3, 0xEC]
```

**Protocol Flow:**
```
1. JSM announces: 00E#08901c8a00000000 (serial heartbeat)
2. PM sends 8 RTR challenges with computed keys
3. JSM responds with serial bytes using same keys
4. Challenge values in RTR are IGNORED by device

RTR: 0x1f00 08 2f  →  Response: 0x1f01 08 08  (key=08, serial[0]=08)
RTR: 0x1f10 b1 00  →  Response: 0x1f11 b1 90  (key=B1, serial[1]=90)
RTR: 0x1f20 1e 0e  →  Response: 0x1f21 1e 1c  (key=1E, serial[2]=1C)
RTR: 0x1f30 46 48  →  Response: 0x1f31 46 8a  (key=46, serial[3]=8A)
```

**Multi-device Networks:**
- All devices on same network use the SAME xor_table
- Different networks/PMs have different xor_tables
- Device enumeration via `0x1fb0000X#` frames contains full 8-byte serials

**Security Note:** No cryptographic security - XOR obfuscation only. If attacker knows xor_table, can impersonate any serial.

### Parameter Exchange Protocol (78X/79X)

Device configuration is exchanged via standard frames 0x780-0x784 (request) and 0x790-0x794 (response):

**Frame ID Assignment:**
- `0x780` / `0x790` = Device slot 0 (PM)
- `0x781` / `0x791` = Device slot 1 (JSM)
- `0x782` / `0x792` = Device slot 2
- `0x78F` / `0x793` = R-Net Programmer

**Frame Data Structure (8 bytes):**
```
Byte 0: Command (0x20=open, 0x40=request, 0x41=ack, 0x21=data, 0xC1=error)
Byte 1: Register (0x80=page0, 0x81=pointer, 0x8F=data, 0x8C=text)
Bytes 2-3: 0x0000
Bytes 4-7: Parameter ID or Value (little-endian)
```

**Example Exchange:**
```
781#2081000006000100  ; JSM: check if pointer 06 sub 01 exists
790#4181000000000000  ; PM: yes, pointer exists
781#408F000000000000  ; JSM: request pointer value
790#218F000084b20000  ; PM: return value 0xb284
```

### R-Net Programmer Protocol

The R-Net Programmer is a commercial device for configuring R-Net electronics. This protocol enables reading/writing wheelchair configuration memory.

**Frame IDs:**
| ID | Direction | Purpose |
|----|-----------|---------|
| `0x7A0` | Programmer → Bus | Presence announcement |
| `0x78F` | Programmer → PM | Request frames |
| `0x793` | PM → Programmer | Response frames |

**Command Bytes (Request - 0x78F):**
| Byte | Command | Description |
|------|---------|-------------|
| `0x42` | PRESENCE_REQ | Heartbeat/polling request |
| `0x83` | SET_ADDRESS | Set memory address pointer |
| `0x03` | START_READ | Begin read operation |
| `0x43` | START_WRITE | Begin write operation |

**Command Bytes (Response - 0x793):**
| Byte | Command | Description |
|------|---------|-------------|
| `0x2F` | PRESENCE_ACK | Heartbeat acknowledgment |
| `0x4F` | READ_RESPONSE | Read data response |
| `0x0F` | WRITE_RESPONSE | Write acknowledgment |
| `0x8F` | COMPLETE | Operation complete |
| `0xC1` | ERROR | Error response |

#### Programmer Handshake

To enter programmer mode, send presence announcement then establish heartbeat:

```
; Step 1: Announce presence
TX: 7A0#                          ; Empty frame announces programmer

; Step 2: Heartbeat (repeat every 200ms)
TX: 78F#422000FF00000000          ; Heartbeat request
RX: 793#2F2000FF00000000          ; Heartbeat ACK
```

**Heartbeat Frame Breakdown:**
```
78F#42 20 00 FF 00 00 00 00
     │  │  │  │
     │  │  │  └── Device ID (0xFF = broadcast)
     │  │  └───── Reserved
     │  └──────── Register (0x20)
     └─────────── Command: Presence Request (0x42)
```

#### Read Protocol

To read 4 bytes from address `0x0100`:

```
1. TX: 78F#830001FF00010000    ; Set address (0x0100 little-endian)
2. TX: 78F#030001FF17000000    ; Start read
3. RX: 793#4F0001FF[4 bytes]   ; Data response
4. RX: 793#8F0001FF00000000    ; Complete
```

**Set Address Frame:**
```
78F#83 00 01 FF XX XX 00 00
     │  │  │  │  └──┴── Address (16-bit, little-endian)
     │  │  │  └──────── Device ID (0xFF = broadcast)
     │  │  └─────────── Sub-command (0x01)
     │  └────────────── Reserved
     └───────────────── Command: Set Address (0x83)
```

**Read Response Frame:**
```
793#4F 00 01 FF DD DD DD DD
     │  │  │  │  └──┴──┴──┴── Data (4 bytes)
     │  │  │  └────────────── Device ID
     │  │  └─────────────────  Sub-command
     │  └────────────────────  Reserved
     └───────────────────────  Command: Read Response (0x4F)
```

#### Write Protocol

To write `DEADBEEF` to address `0x0200`:

```
1. TX: 78F#830001FF00020000    ; Set address (0x0200)
2. TX: 78F#430001FFDEADBEEF    ; Write data
3. RX: 793#0F0001FF41000000    ; Write ACK
4. RX: 793#8F0001FF00000000    ; Complete
```

#### Timing Requirements

- Heartbeat interval: 200ms (maintain connection)
- Inter-frame gap: minimum 1ms
- Response timeout: 500ms
- Session timeout: ~2s without heartbeat

#### Programmer Tool

Use `rnet_programmer.py` to interact with programmer mode:

```bash
# Test programmer handshake
python3 rnet_programmer.py handshake -v

# Enable programmer mode (maintains heartbeat)
python3 rnet_programmer.py enable

# Read 256 bytes from address 0x0000
python3 rnet_programmer.py read 0x0000 0x100 -o data.bin

# Write data to address
python3 rnet_programmer.py write 0x0100 --data DEADBEEF

# Dump memory range to file
python3 rnet_programmer.py dump 0x0000 0x1000 -o config.bin

# Monitor programmer frames
python3 rnet_programmer.py monitor --filter 78F,793,7A0

# Read from RAM instead of EEPROM (ODI class from DongleInterface.dll)
python3 rnet_programmer.py --odi-class ram read 0x0000 0x100

# Target specific device (0x00=PM, 0x01=JSM, 0xFF=broadcast)
python3 rnet_programmer.py --target 0x00 read 0x0000 0x100
```

See `docs/RNET_PROGRAMMER_PROTOCOL.md` for complete protocol documentation.
See `docs/POP_PROTOCOL.md` for full POP specification (from DongleInterface.dll RE).

### Firmware Architecture

R-Net devices use **Freescale/NXP HCS08 8-bit microcontrollers** (likely MC9S08DZ family with integrated CAN).

**Evidence from firmware dumps:**
- HC08/HCS08 instruction patterns (LDA, RTS, BNE, BEQ)
- Motorola S-Record format (used by Freescale toolchain)
- CAN bus peripherals common on HCS08 automotive variants

**Memory Layout (from dump analysis):**
```
0x0000 - 0x00FF    Header / Device ID
0x0100 - 0x01FF    Serial / Keys (encryption key at 0x0160)
0x0200 - 0x03FF    Reserved / Config pointers
0x0400 - 0x0FFF    Device Configuration Tables
0x1000 - 0x3FFF    Extended Config (0x18A7 sentinel = uninitialized)
0x4000 - 0x7FFF    Firmware Code Region 1
0x8000 - 0xFFFF    Firmware Code Region 2
0x10000+           Additional code/data pages
```

**Device Identification:**
| Device | Device ID | Config Encryption |
|--------|-----------|-------------------|
| BTMouse | `0x0000` | Encrypted (XOR key at 0x0160) |
| LEDJSM | `0x6380` | Plaintext |

**BTMouse Encryption Key (0x0160):**
```
FC 95 FE BA E3 1F 2D 04 EC 12 E6 FD EF 00 57 C1
```

**Sentinel Value:** `0x18A7` marks uninitialized/default configuration slots. Appears 35,000+ times in firmware dumps.

**Security Observations:**
- Weak XOR-based encryption (key stored in firmware)
- No code signing (firmware can be modified)
- Standard S-record format (editable with common tools)

See `docs/FIRMWARE_DUMP_ANALYSIS.md` for complete analysis.

### R-Net Programmer Configuration Files (.R-net)

Configuration exports from R-Net Programmer software contain wheelchair settings in binary format.

**File Structure:**
| Offset | Content |
|--------|---------|
| 0x0000-0x00FF | Header (magic `03000000`, checksums) |
| 0x0160-0x0250 | Mode profiles (Drive, Seating, Bluetooth) |
| 0x0250-0x0600 | Speed profiles (`dddd` + 16-byte name + config) |
| 0x0B00-0x0BC0 | Motor current limits (per-profile %) |
| 0x0C00-0x1000 | Seating/actuator functions |

**Motor Current Limits (key offsets):**
```
0x0B23: Profile 1 current limit (0-100%)
0x0B30: Profile 2 current limit
0x0B3D: Profile 3 current limit
...
0x0BB2: Profile 12 current limit
```

**Stock vs Modified:**
| Config Type | Motor Limit | Notes |
|-------------|-------------|-------|
| Stock OEM | 55% | Factory default |
| 90-amp mod | 100% | All profiles maxed |
| 120-amp mod | 100% | + ESP disabled |

**Known Speed Profile Names (27 unique):**
- V6: SLOWEST, SLOW, MEDIUM, FAST, V6AT FAST
- Standard: Indoor, Normal, High Torque, Profile 3-7
- Custom: idiot mode, DANGEROUS, DIABLO!!!, **SOCCER**, PWR-Tremor

**10 Unique Chair Serials:**
CS14050871 (V6), CR14121385 (V6), CS13093419 (C500), CR15070953 (C500),
CS13124566 (M300), CR17122192 (M300), CR14060137 (Alltrack),
CS13061526 (Pulse 6), CR16125104 (M3), CS21054090 (F3)

See `docs/RNET_CONFIG_FILE_FORMAT.md` for complete format specification.
See `parsed_configs/` for extracted settings from all 25 config files.

### Configuration Transfer Protocol (0x1E3X-0x1E8X)

Bulk config/firmware transfer uses extended frames:
- `0x1E3C0001-3` - Transfer header (3 segments with CRC)
- `0x1E4E0001-2` - Data blocks with CRC
- `0x1E3F0002` - Acknowledgment
- `0x1E80000F` - Transfer complete

### Bluetooth Module (BTM) Differences

BTM devices use different serial keys and status frames:
- Serial exchange uses different XOR table than JSM
- Status frames: `0x0A400002#`, `0x0A400102#`, `0x0A400300#`, `0x0A400301#`

### Color JSM (cJSM) Display Protocol

The cJSM has a color display but does **NOT** receive raw bitmap/pixel data over CAN. Instead:
- Text is sent as ASCII via register 0x8C
- Icons/graphics are built into the cJSM firmware
- Mode configuration frames define display behavior

**Authentication:**
cJSM uses slot 8+ range (0x1F8X) instead of 0-7. When authentication fails, sends repeated "cry for help" pattern:
```
0x1F800010#, 0x1F800011#, 0x1F800012#, 0x1F800013#  ; Trying slot 8
0x1F810000#, 0x1FA00000#  ; Retrying/error state
```

**Display Text Transfer:**
Text is sent via parameter exchange using register 0x8C in 4-byte chunks:
```
Request:  0x78X#208CXXXX...  (X = slot)
Response: 0x79X#208CXXXX...

Data format:
  Byte 0: 0x20 (command = data)
  Byte 1: 0x8C (register = text display)
  Bytes 2-3: 0x0000
  Bytes 4-7: ASCII text (4 characters)
```

Example text chunks from captures:
```
208c000044726976 → "Driv"
208c000065202020 → "e   "
208c000053656174 → "Seat"
208c0000696e6720 → "ing "
208c00004c333374 → "L33t"
208c000042542020 → "BT  "
208c00004d6f7573 → "Mous"
208c00006f6e7472 → "ontr"
208c00006f6c2020 → "ol  "
```

Profile prefixes (mode indicators):
- `64646450` = "dddP" (Profile)
- `64646441` = "dddA" (Attendant)
- `64646447` = "dddG" (Godly)
- `6464644e` = "dddN" (Noob)

**Mode Configuration Frames (0x1ECXXXXX):**

Extended frames in the 0x1EC range transfer mode/profile configuration:
```
Frame ID: 0x1EC [Mode] [SubAddr] [Type]
                │       │         │
                │       │         └── 0x00=init, 0x40=config, 0x60=param, 0x61=extended
                │       └──────────── Sub-address within mode (0x08, 0x10, 0x18, etc.)
                └──────────────────── Mode index (0-5)
```

Type suffixes:
- `0x00` - Initialization (usually zeros)
- `0x40` - Configuration header (`0103000000000000`)
- `0x60` - Mode parameters (device serials at SubAddr 0xF0)
- `0x61` - Extended mode data
- `0x62` - XOR key data
- `0x80` - Status
- `0xC0`, `0xF0` - Flags (`0100000000000000`)

Device serials found in Mode X, SubAddr 0xF0, Type 0x60:
```
Mode 0: 08901C8A00000000  (JSM)
Mode 1: 0C01148B00000000
Mode 2: 8F80198B00000000
Mode 3: E48C1C8C00000000
Mode 4: 50C01C8F00000000  (M300 JSM)
Mode 5: 1697000003500201
```

**No Bitmap Graphics:**
The 8-byte CAN frame limit makes bitmap transfer impractical. A 32x32 monochrome icon would require 128+ frames. The cJSM stores all graphics in firmware and only receives text/parameters to configure the display.

### Other Discoveries
- **Bit-banging doesn't work:** Attempting to kill frames via bit-banging instantly causes CAN error and frame resend (no timeout)
- **Drive-by-wire over IP:** TCP-based remote control with Pi3 on R-Net + separate joystick machine (`x360_over_IP*.py`)

## R-Net Protocol Stack Summary

```
Layer 4 - Application
├── Joystick:    02000X00# every 10ms
├── Speed:       0A040X00# on change
├── Parameters:  78X#/79X# request/response
└── Heartbeats:  00E#, 03C30F0F#, 0C140X00#

Layer 3 - Session
├── Serial number challenge/response authentication
├── XOR-based key derivation (no crypto)
└── Device slot assignment (0-F)

Layer 2 - Addressing
├── Standard frames (11-bit): Control, mode, profile
└── Extended frames (29-bit): Data, serial, config

Layer 1 - Physical
└── CAN 2.0B @ 125Kbps
```

**Security Weaknesses:**
- No encryption on any frames
- Challenge values in RTR ignored by devices
- Timing-based spoofing possible (FollowJSM)
- Error injection enables control takeover (JSMerror)
- XOR tables can be extracted from captures

## Utility Scripts

### rnet_utils.py

Protocol analysis utility with the following commands:

```bash
# Decode serial number with XOR table
python3 rnet_utils.py decode-serial 08901c8a00000000 --xor 002102ccdd127b45

# Decode R-Net frames
python3 rnet_utils.py decode-frame 02000100#0064 00E#08901C8A00000000

# Analyze capture file statistics
python3 rnet_utils.py analyze wireshark/july12_light.log

# Extract authentication info and XOR tables from capture
python3 rnet_utils.py extract-auth capture.log

# Generate auth frames for serial spoofing
python3 rnet_utils.py generate-auth 08901c8a00000000 --table standalone_jsm

# Calculate joystick frame for given position
python3 rnet_utils.py joystick 0 100      # full forward
python3 rnet_utils.py joystick 50 50 -c   # diagonal with continuous send

# Extract cJSM display text from capture
python3 rnet_utils.py extract-display capture.log -v

# List known XOR tables
python3 rnet_utils.py list-tables
```

Known XOR tables built-in: `standalone_jsm`, `m300`, `btm`

### rnet_obp_mode.py

OBP (On-Board Programming) mode tool — uses the JSM parameter exchange
protocol (0x781/0x790), NOT the POP dongle protocol. OBP is activated by
the wheelchair user via Horn + On/Off button combo (series of bleeps).

```bash
# Interactive OBP shell
python3 rnet_obp_mode.py

# Enable OBP if disabled (safe mode: backup + guided workflow)
python3 rnet_obp_mode.py --enable

# Enable OBP with known EEPROM address (safe: backs up first)
python3 rnet_obp_mode.py --enable-obp-addr 0x0450

# Enable without backup/prompts (advanced)
python3 rnet_obp_mode.py --enable --advanced

# Monitor parameter exchange traffic during OBP
python3 rnet_obp_mode.py --monitor

# Scan all known OBP parameters
python3 rnet_obp_mode.py --scan

# Read Forward Speed parameter (ptr=0x06, sub=0x01)
python3 rnet_obp_mode.py --read 0x06 0x01

# Write Forward Speed = 80
python3 rnet_obp_mode.py --write 0x06 0x01 80
```

Interactive commands: `read`, `write`, `scan`, `monitor`, `check`, `enable`, `enable-at`, `read-pop`, `write-pop`, `slot`, `target`, `status`, `help`, `quit`

See `docs/OBP_ENABLE_GUIDE.md` for the complete guide to enabling and using OBP mode.

### rnet_pop_shell.py

POP (Parameter Object Protocol) shell — emulates the R-Net Programmer
dongle (D50610) over SocketCAN. Uses 0x78F/0x793 for raw memory read/write.
This is the dongle protocol, not OBP mode. Formerly `rnet_obd_program.py`.

```bash
# Enable programming mode (interactive shell)
python3 rnet_pop_shell.py

# Use specific CAN interface
python3 rnet_pop_shell.py can0

# Read 256 bytes from address 0x0000
python3 rnet_pop_shell.py --read 0x0000 0x100

# Dump config region to file
python3 rnet_pop_shell.py --dump config.bin

# Write speed setting (50%) to address 0x0430
python3 rnet_pop_shell.py --write 0x0430 32

# Read from RAM or ROM (ODI class from DongleInterface.dll)
python3 rnet_pop_shell.py --odi-class ram --read 0x0000 0x100

# Target specific device
python3 rnet_pop_shell.py --target 0x00 --read 0x0000 0x100

# Verbose mode (show all CAN frames)
python3 rnet_pop_shell.py -v
```

Interactive commands: `read`, `write`, `dump`, `odi`, `target`, `status`, `help`, `quit`

### rnet_programmer.py

R-Net Programmer mode tool for reading/writing device configuration.
Uses POP (Parameter Object Protocol) from DongleInterface.dll v3.0.0.0.
Supports ODI class selection (EEPROM/RAM/ROM/SLOT) and device targeting.

```bash
# Test programmer handshake
python3 rnet_programmer.py handshake -v

# Enable programmer mode and maintain connection
python3 rnet_programmer.py enable

# Read memory from device
python3 rnet_programmer.py read 0x0000 0x100 -o dump.bin

# Write data to memory
python3 rnet_programmer.py write 0x0100 --data DEADBEEF

# Dump entire memory range
python3 rnet_programmer.py dump 0x0000 0x2000 -o config.bin

# Monitor CAN bus (optionally filter to programmer frames)
python3 rnet_programmer.py monitor --filter 78F,793,7A0

# Read from different ODI memory classes
python3 rnet_programmer.py --odi-class ram read 0x0000 0x100
python3 rnet_programmer.py --odi-class rom read 0x0000 0x100

# Target specific device on the bus
python3 rnet_programmer.py --target 0x01 read 0x0000 0x100  # JSM
```

### rnet_config_parser.py

Parser for R-Net Programmer .R-net configuration files:

```bash
# Parse single config file
python3 rnet_config_parser.py config.R-net

# Output as JSON
python3 rnet_config_parser.py config.R-net --json

# Compare stock vs modified configs
python3 rnet_config_parser.py stock.R-net mod.R-net --diff

# Focus on motor settings (with visual bars)
python3 rnet_config_parser.py config.R-net --motor

# Include raw hex sections
python3 rnet_config_parser.py config.R-net --raw
```

Extracts: speed profiles, motor current limits, seating functions, mode profiles.
See `docs/RNET_CONFIG_FILE_FORMAT.md` for file format specification.

## Analysis Tools

Located in `tools/` directory:

```bash
# Analyze LEDJSM plaintext config
python3 tools/analyze_ledjsm_config.py

# Attempt BTMouse decryption
python3 tools/decrypt_btmouse.py

# Block-by-block encryption analysis
python3 tools/analyze_encryption.py

# Deep BTMouse analysis
python3 tools/btmouse_deep_analysis.py

# Try AES decryption (requires pycryptodome)
python3 tools/try_aes_decrypt.py

# Extract config from pcap
python3 tools/extract_config_data.py wireshark/file.pcapng output.bin
```

See `tools/README.md` for complete tool documentation.

## Data Files

- `wireshark/` - 27+ PCAP captures of R-Net traffic for protocol analysis
  - `*_startup*.pcapng` - Power-on handshake sequences
  - `*_powerup*.pcapng` - M300 multi-device startup
  - `*_bluetooth*.pcapng` - BTM pairing/communication
  - `*_hotplug*.pcapng` - Device hot-plug behavior
  - `*cJSM*.pcapng` - Color JSM display protocol and authentication
  - `ics_*.pcapng` - R-Net Programmer read/write operations
  - `*.R-net` - Binary config files from R-Net Programmer
- `docs/` - Protocol documentation (see `docs/README.md` for index)
  - `RNET_PROTOCOL_SPECIFICATION.md` - **Full protocol specification**
  - `RNET_PROTOCOL_GUIDE.md` - Protocol overview
  - `RNET_PROGRAMMER_PROTOCOL.md` - Programmer protocol
  - `CJSM_DISPLAY_PROTOCOL.md` - Color JSM display protocol
  - `FIRMWARE_DUMP_ANALYSIS.md` - Firmware dump analysis
  - `FIRMWARE_REVERSE_ENGINEERING.md` - HCS08 code analysis
  - `LEDJSM_CONFIG_ANALYSIS.txt` - Config structure analysis
  - `RNET_CONFIG_FILE_FORMAT.md` - R-Net Programmer .R-net file format
  - `RNET_ERROR_CODES.md` - Error code definitions and handling
  - `ESP_PROTOCOL.md` - Electronic Stability Program protocol
  - `OBP_ENABLE_GUIDE.md` - How to enable and use OBP mode (safe + advanced)
  - `ICS_SEATING_SYSTEM.md` - ICS seating system documentation
  - `SAFETY_RESTRICTIONS.md` - Safety restrictions and lockout behavior
  - `GETTING_STARTED.md` - Setup guide
  - `QUICK_REFERENCE.md` - Cheat sheet
- `tools/` - Analysis and utility scripts (see `tools/README.md`)
- `chair_data/` - Chair-specific data and logs
- `R-Net Configs/` - R-Net Programmer configuration exports (25 .R-net files)
  - `V6/` - Frontier V6 configs (stock, 90amp, 120amp, no-ESP mods)
  - `C500 - Black/` - Permobil C500 configs
  - `M300 2018/` - M300 configs including **SOCCER** profile
  - `amylior alltrack/` - Alltrack with DANGEROUS, PWR-Tremor profiles
  - `quickie pulse 6/` - Pulse 6 with DIABLO!!! profile
  - `2021 F3/`, `orange 2018 m3/` - Additional chair models
  - See `docs/RNET_CONFIG_FILE_FORMAT.md` for format analysis
- `parsed_configs/` - Extracted settings from all .R-net files
  - `ALL_CONFIGS_EXTRACTED.json` - Complete extraction (522 KB)
  - `CLEAN_SETTINGS_SUMMARY.json` - Filtered/cleaned settings
  - `motor_settings_comparison.csv` - Motor limits per config
  - `speed_profiles_comparison.csv` - All speed profile settings
  - Individual `.txt` and `.json` files per config

- `can2RNET/ppts/DEFCON24_chairhacking.pdf` - Personal story presentation
- `can2RNET/ppts/canPPT.pdf` - Technical presentation (R-Net protocol, exploits)
- `RNET_FRAME_DICTIONARY.md` - Comprehensive frame reference (590+ lines)
