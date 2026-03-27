# R-Net Programmer Protocol

Complete documentation of the R-Net R-Net Programmer protocol used for reading and writing wheelchair configuration data.

## Overview

The R-Net Programmer is a commercial device made by PG Drives Technology for configuring R-Net wheelchair electronics. This document describes the CAN bus protocol used by the programmer to communicate with the Power Module (PM) and other R-Net devices.

> **Official Name:** The programmer protocol is officially called **POP (Parameter Object Protocol)**, running on the **REBUS** transport layer. These names were identified through reverse engineering of DongleInterface.dll v3.0.0.0 (PG Drives Technology), which implements the PC-side programmer interface.

**Protocol Characteristics:**
- CAN 2.0B @ 125 Kbps
- Standard frames (11-bit IDs) for basic POP operations
- Extended frames (29-bit IDs) for segmented POP transfers
- Request/Response pattern
- No encryption or authentication

## Frame IDs

| Frame ID | Direction | Description |
|----------|-----------|-------------|
| `0x78F` | Programmer → PM | Programmer request frames |
| `0x793` | PM → Programmer | PM response frames |
| `0x7A0` | Programmer → Bus | Programmer presence announcement |
| `0x792` | Device → Programmer | Device responses (slot 2) |

**Note:** Frame ID `0x793` is shared between R-Net Programmer responses and Slot 3 parameter responses. Context determines interpretation.

## Command Bytes

The first byte of frame data indicates the command type:

### Request Commands (0x78F)

| Byte | Command | Description |
|------|---------|-------------|
| `0x42` | PRESENCE_REQUEST | Heartbeat/presence polling |
| `0x83` | SET_ADDRESS | Set memory address pointer |
| `0x03` | START_READ | Begin read operation |
| `0x43` | START_WRITE | Begin write operation |
| `0x20` | OPEN_PAGE | Open parameter page |
| `0x40` | REQUEST_DATA | Request data at pointer |

### Response Commands (0x793)

| Byte | Command | Description |
|------|---------|-------------|
| `0x2F` | PRESENCE_ACK | Heartbeat acknowledgment |
| `0x4F` | READ_RESPONSE | Read data response |
| `0x0F` | WRITE_RESPONSE | Write acknowledgment |
| `0x8F` | COMPLETE | Operation complete |
| `0x41` | ACK | General acknowledgment |
| `0x21` | DATA_RESPONSE | Data with value |
| `0xC1` | ERROR | Error response |

---

## Programmer Handshake

The handshake establishes programmer presence on the bus and must be maintained throughout the session.

### Step 1: Announce Presence

Send an empty frame to announce the programmer:

```
TX: 7A0#
```

No response expected. This frame alerts devices that a programmer is connecting.

### Step 2: Establish Heartbeat

Send heartbeat request and wait for acknowledgment:

```
TX: 78F#422000FF00000000
RX: 793#2F2000FF00000000
```

**Frame Breakdown (Request):**
```
78F#42 20 00 FF 00 00 00 00
     │  │  │  │
     │  │  │  └── Device ID (0xFF = broadcast)
     │  │  └───── Reserved (0x00)
     │  └──────── Register (0x20)
     └─────────── Command: Presence Request (0x42)
```

**Frame Breakdown (Response):**
```
793#2F 20 00 FF 00 00 00 00
     │  │  │  │
     │  │  │  └── Device ID echo
     │  │  └───── Reserved
     │  └──────── Register echo
     └─────────── Command: Presence ACK (0x2F)
```

### Step 3: Maintain Connection

The heartbeat must be sent periodically to maintain the connection:

```
Interval: ~200ms
TX: 78F#422000FF00000000
RX: 793#2F2000FF00000000
```

If heartbeats stop, the PM will exit programmer mode after a timeout.

### Complete Handshake Sequence

```
Time     Frame
──────────────────────────────────────────────────
  0ms    TX: 7A0#                         ; Announce presence
100ms    TX: 78F#422000FF00000000         ; Heartbeat 1
110ms    RX: 793#2F2000FF00000000         ; ACK
300ms    TX: 78F#422000FF00000000         ; Heartbeat 2
310ms    RX: 793#2F2000FF00000000         ; ACK
  ...    (continue every 200ms)
```

---

## Read Protocol

Reading data from device memory.

### Frame Format

**Set Address Request:**
```
78F#83 00 01 FF XX XX 00 00
     │  │  │  │  └──┴── Address (16-bit, little-endian)
     │  │  │  └──────── Device ID (0xFF = broadcast)
     │  │  └─────────── Sub-command (0x01)
     │  └────────────── Reserved (0x00)
     └───────────────── Command: Set Address (0x83)
```

**Start Read Request:**
```
78F#03 00 01 FF 17 00 00 00
     │  │  │  │  │
     │  │  │  │  └── Read size/mode (0x17)
     │  │  │  └───── Device ID
     │  │  └──────── Sub-command
     │  └─────────── Reserved
     └────────────── Command: Start Read (0x03)
```

**Read Response:**
```
793#4F 00 01 FF DD DD DD DD
     │  │  │  │  └──┴──┴──┴── Data (4 bytes)
     │  │  │  └────────────── Device ID
     │  │  └─────────────────  Sub-command
     │  └────────────────────  Reserved
     └───────────────────────  Command: Read Response (0x4F)
```

**Operation Complete:**
```
793#8F 00 01 FF 00 00 00 00
     │
     └── Command: Complete (0x8F)
```

### Read Sequence

To read 4 bytes from address `0x0100`:

```
1. TX: 78F#830001FF00010000    ; Set address to 0x0100 (little-endian: 00 01)
2. TX: 78F#030001FF17000000    ; Start read
3. RX: 793#4F0001FFDDDDDDDD    ; Response with data
4. RX: 793#8F0001FF00000000    ; Complete
```

### Reading Multiple Bytes

For reads larger than 4 bytes, repeat the sequence with incremented addresses:

```
; Read 8 bytes from 0x0100

; Bytes 0-3
TX: 78F#830001FF00010000      ; Address 0x0100
TX: 78F#030001FF17000000      ; Start read
RX: 793#4F0001FF[byte0-3]     ; Data
RX: 793#8F0001FF00000000      ; Complete

; Bytes 4-7
TX: 78F#830001FF04010000      ; Address 0x0104
TX: 78F#030001FF17000000      ; Start read
RX: 793#4F0001FF[byte4-7]     ; Data
RX: 793#8F0001FF00000000      ; Complete
```

---

## Write Protocol

Writing data to device memory.

### Frame Format

**Set Address Request:** (same as read)
```
78F#83 00 01 FF XX XX 00 00
```

**Write Command:**
```
78F#43 00 01 FF DD DD DD DD
     │  │  │  │  └──┴──┴──┴── Data to write (4 bytes)
     │  │  │  └────────────── Device ID
     │  │  └─────────────────  Sub-command
     │  └────────────────────  Reserved
     └───────────────────────  Command: Start Write (0x43)
```

**Write Response:**
```
793#0F 00 01 FF SS 00 00 00
     │           │
     │           └── Status byte
     └────────────── Command: Write Response (0x0F)
```

### Write Sequence

To write `DEADBEEF` to address `0x0200`:

```
1. TX: 78F#830001FF00020000    ; Set address to 0x0200
2. TX: 78F#430001FFDEADBEEF    ; Write data
3. RX: 793#0F0001FF41000000    ; Write ACK (0x41 = success)
4. RX: 793#8F0001FF00000000    ; Complete
```

---

## Error Handling

### Error Response

When an operation fails, the PM responds with error code `0xC1`:

```
793#C1 81 00 00 28 00 00 00
     │  │        │
     │  │        └── Error code
     │  └─────────── Register that failed
     └────────────── Command: Error (0xC1)
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| `0x28` | Address not found |
| `0x00` | General error |

### Timeout Handling

- Read timeout: 500ms
- Write timeout: 500ms
- Heartbeat timeout: 200ms
- Session timeout: ~2000ms without heartbeat

---

## Observed Traffic Patterns

### From Captured Programmer Session

Traffic captured from an actual R-Net Programmer session shows this pattern:

```
; Initial handshake
7A0#                              ; Programmer announce
78F#422000FF00000000              ; Heartbeat
793#2F2000FF00000000              ; ACK

; Periodic status frames
0300:00400#1510                   ; Status: connected
0300:00400#1515                   ; Status: active

; Continuous heartbeat during operation
78F#422000FF00000000              ; Heartbeat (every 200ms)
793#2F2000FF00000000              ; ACK
```

### Multi-Device Query

The programmer can query multiple devices:

```
78F#422000FF00000000              ; Broadcast query (FF)
792#2F2000FF00000000              ; Slot 2 response
793#2F2000FF00000000              ; Slot 3 response
```

---

## Memory Map

Based on analysis of `.R-net` configuration files:

| Address Range | Content |
|---------------|---------|
| `0x0000-0x001F` | Header / File type |
| `0x0020-0x015F` | Device configuration blocks |
| `0x0160-0x020F` | Profile names (20 chars each) |
| `0x0210-0x0FFF` | Profile configurations |
| `0x1000+` | Mode maps and parameter tables |

### Known Profile Offsets

```
0x0160: "Drive" (20 bytes)
0x0174: "Seating" (20 bytes)
0x0188: "L33tBT" (20 bytes)
0x019C: "Mouse Control 1" (20 bytes)
...
```

---

## Implementation Notes

### Timing Requirements

- Minimum inter-frame gap: 1ms
- Heartbeat interval: 150-250ms (200ms recommended)
- Response timeout: 500ms
- Maximum burst rate: ~10 frames/100ms

### Device ID Filtering

- `0xFF` = Broadcast (all devices respond)
- `0x00` = PM (Power Module)
- `0x01` = JSM (Joystick Module)
- `0x02`-`0x0E` = Other devices
- `0x0F` = Reserved for programmer

### Session Lifecycle

```
1. Open CAN socket
2. Send 7A0# (announce)
3. Start heartbeat thread (200ms interval)
4. Perform read/write operations
5. Stop heartbeat
6. Close socket
```

---

## Security Considerations

The R-Net Programmer protocol has **no security**:

1. **No authentication** - Any device can send programmer frames
2. **No encryption** - All data transmitted in plaintext
3. **No integrity checking** - No CRC beyond CAN layer
4. **Broadcast addressing** - 0xFF queries all devices

This allows:
- Configuration extraction (dump all memory)
- Configuration modification (write arbitrary values)
- Profile manipulation (change speed limits, etc.)
- Potential safety bypass (if safety params are writable)

---

## POP Transfer Codes

The POP (Parameter Object Protocol) defines the following transfer codes (TC) for data exchange between programmer and device:

### Upload (Device to Programmer)

| Code | Name | Value | Description |
|------|------|-------|-------------|
| TC_UL_REQ | Upload Request | 0x03 | Programmer requests data from device |
| TC_UL_RES | Upload Response | 0x01 | Device sends requested data |
| TC_ULS_REQ | Upload Segmented Request | 0x09 | Segmented upload request (for large transfers) |
| TC_ULS_RES | Upload Segmented Response | 0x0A | Segmented upload response |

### Download (Programmer to Device)

| Code | Name | Value | Description |
|------|------|-------|-------------|
| TC_DL_REQ | Download Request | 0x05 | Programmer sends data to device |
| TC_DL_RES | Download Response | 0x07 | Device acknowledges download |
| TC_DLS_REQ | Download Segmented Request | 0x04 | Segmented download request (for large transfers) |
| TC_DLS_RES | Download Segmented Response | 0x08 | Segmented download response |

### Control

| Code | Name | Value | Description |
|------|------|-------|-------------|
| TC_ABORT | Transfer Abort | - | Abort current transfer |
| TC_END | Transfer End | - | End of transfer sequence |
| TC_ILLEGAL | Illegal Transfer | - | Invalid/unsupported transfer code |

---

## ODI Classes (Object Dictionary Interface)

The ODI (Object Dictionary Interface) classifies device memory regions into typed objects. The programmer uses ODI classes to address different memory types:

| Class Code | Name | Description |
|------------|------|-------------|
| 0x0100 | EEPROM | Non-volatile configuration storage |
| 0x0110 | PORT | I/O port registers |
| 0x0120 | RAM | Volatile runtime data |
| 0x0130 | ROM | Read-only firmware data |
| 0x0140 | ADC | Analog-to-digital converter values |
| 0x0200 | SLOT | Device slot configuration |
| 0xFFFFFF | SENTINEL | End-of-list / uninitialized marker |

ODI classes allow the programmer to access different memory types on the target device through a unified interface, rather than raw memory addresses.

---

## POP Segmented Protocol (Extended CAN IDs)

For transfers larger than a single CAN frame, POP uses a segmented protocol with extended (29-bit) CAN IDs:

### Extended Frame ID Construction

**Request (Programmer to Device):**
```
ID = 0x1E400000 | (node << 15) | (tc << 18)

Where:
  node = target device node number (0-F)
  tc   = transfer code (see POP Transfer Codes)
```

**Response (Device to Programmer):**
```
ID = 0x1E000000 | (node << 15) | (tc << 18)

Where:
  node = responding device node number
  tc   = response transfer code
```

### Example

Segmented upload from node 1:
```
Request:  0x1E400000 | (1 << 15) | (0x09 << 18) = 0x1E648000
Response: 0x1E000000 | (1 << 15) | (0x0A << 18) = 0x1E288000
```

---

## USB Dongle Interface

The R-Net Programmer connects to a PC via a USB dongle that bridges USB to CAN.

### Hardware Details

| Property | Value |
|----------|-------|
| Part Number | D50610 |
| Interface Chip | FTDI (USB-to-serial) |
| Device Description | "RNet Dongle" |

### Framing Protocol

The USB dongle uses a byte-stuffed framing protocol:

| Byte | Name | Value | Description |
|------|------|-------|-------------|
| STX | Start of Text | 0x02 | Frame start delimiter |
| ETX | End of Text | 0x03 | Frame end delimiter |
| DLE | Data Link Escape | 0x10 | Escape character for byte-stuffing |

**Maximum frame size:** 32 bytes

When data bytes match STX, ETX, or DLE, they are prefixed with DLE (byte-stuffing) to avoid framing ambiguity.

### Raw Message Formats

**V1 Format (21 bytes):**
Legacy message format for older programmer hardware.

**V2 Format (24 bytes):**
Extended message format with additional fields for newer hardware.

### Access Levels

The dongle's EEPROM stores access level credentials:

| Level | Privileges | Description |
|-------|------------|-------------|
| OEM | Full access | Factory-level read/write to all memory regions |
| Dealer | Restricted | Limited to user-configurable parameters |

**Enforcement:** Access levels are enforced by credentials stored in the dongle's EEPROM. OEM access grants strictly more privileges than Dealer access. The dongle presents its access level during the REBUS connection handshake.

---

## Connection State Machine

The programmer connection follows a defined state progression:

```
CXTN_NONE ──> CXTN_INIT ──> CXTN_DONGLE ──> CXTN_CAN ──> CXTN_RNET ──> CXTN_UPLOAD
                                                                     └──> CXTN_DOWNLOAD
```

| State | Description |
|-------|-------------|
| CXTN_NONE | No connection, initial state |
| CXTN_INIT | Connection initialization started |
| CXTN_DONGLE | USB dongle detected and configured |
| CXTN_CAN | CAN bus interface active (dongle talking to bus) |
| CXTN_RNET | REBUS protocol established (heartbeat active, devices enumerated) |
| CXTN_UPLOAD | Upload session active (reading data from device) |
| CXTN_DOWNLOAD | Download session active (writing data to device) |

The state machine progresses linearly from NONE through RNET. From RNET, the connection branches into either UPLOAD or DOWNLOAD mode depending on the operation. Failure at any stage returns to CXTN_NONE.

---

## Timing Constants

Constants extracted from DongleInterface.dll:

| Constant | Value | Description |
|----------|-------|-------------|
| QCK_TIMEOUT | 1000ms | Quick operation timeout |
| SEG_TIMEOUT | 100ms | Segmented transfer inter-frame timeout |
| DONGLE_TIMEOUT | 500ms | USB dongle response timeout |
| CANMSG_TIMEOUT | 10000ms | Maximum wait for any CAN message |
| USB_READ_TIMEOUT | 250ms | USB read operation timeout |
| READ_RETRY_COUNT | 3 | Number of read retries before failure |
| LATENCY_TIMER | 1ms | FTDI latency timer setting |

**Note:** These values supplement the timing requirements in the existing [Timing Requirements](#timing-requirements) section. The `SEG_TIMEOUT` of 100ms is notably shorter than the standard heartbeat interval, reflecting the tighter timing needs of segmented bulk transfers.

---

## Tool Usage

The `rnet_programmer.py` tool implements this protocol:

```bash
# Test handshake
./rnet_programmer.py handshake -v

# Enable programmer mode
./rnet_programmer.py enable

# Read 256 bytes from address 0x0000
./rnet_programmer.py read 0x0000 0x100

# Write data to address
./rnet_programmer.py write 0x0100 --data DEADBEEF

# Dump memory range
./rnet_programmer.py dump 0x0000 0x1000 -o config.bin

# Monitor programmer frames
./rnet_programmer.py monitor --filter 78F,793,7A0
```

---

## References

- DEFCON24 Wheelchair Hacking presentation (Stephen Chavez & Specter)
- `wireshark/programmer_dump_file_july2017.pcapng` - Captured programmer read session
- `wireshark/programmer_write_file_july2017.pcapng` - Captured programmer write session
- `wireshark/ics_write_config.pcapng` - ICS configuration transfer
- `new/src/test.cpp` - Captured programmer bus queries (lines 492-591)
- `RNET_FRAME_DICTIONARY.md` - Complete frame reference
- DongleInterface.dll v3.0.0.0 (PG Drives Technology) - Source of POP/REBUS/ODI terminology, transfer codes, ODI classes, timing constants, USB dongle protocol, connection state machine, and access levels
