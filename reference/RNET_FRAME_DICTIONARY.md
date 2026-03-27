# R-Net CAN Frame Dictionary

Comprehensive reference of all known R-Net CAN frames, compiled from pcap analysis, protocol research, and reverse engineering by Stephen Chavez & Specter (DEFCON24, 2016).

**Protocol:** CAN 2.0B @ 125Kbps
**Frame Format:** `<can_id>#{R|data}` (cansend/candump format)
**Notation:**
- `X` = variable nibble (0-F)
- `Xx` = variable byte
- `#R` = Remote Transmission Request (RTR)
- STD = Standard frame (11-bit ID)
- XTD = Extended frame (29-bit ID)
- JSMtx = JSM transmits, PMtx = PM transmits, etc.

---

## 1. POWER/SLEEP FRAMES

| Frame | Type | Description |
|-------|------|-------------|
| `000#R` | RTR | PM sleep all devices (power off) |
| `000#` | STD | JSM sleeping acknowledgment |
| `002#R` | RTR | PM sleep all devices (alternate) |
| `002#` | STD | Seen during JSM init |
| `004#` | STD | JSM sleep commencing |
| `004#R` | RTR | Related to sleep/wake sequence |
| `00C#` | STD | JSM test CAN connection (checks for ACK before wake). If sent while JSM is on, turns it off |
| `0006C01F#` | XTD | CAN bus sleep/wake reset. Sent to prevent CAN bus from entering sleep mode. (Source: DongleInterface.dll `CAN_ID_SLEEP_RESET`) |

---

## 2. SERIAL NUMBER / IDENTIFICATION

| Frame | Type | Description |
|-------|------|-------------|
| `00E#RrSsTtUuVvWwXxYy` | STD | JSM serial number heartbeat. **Periodic: 50ms**. Unique to each JSM. PM must see this to begin profile handshaking. Known: `08901c8a` |
| `1FMSKkUu#` | XTD | Serial number exchange. M=module# (0-7), S=serial position (0-7), Kk=key, Uu=serial data |
| `1FRSTtUu#R` | RTR | Serial number challenge from PM |
| `1F00XXXX#` through `1F70XXXX#` | XTD | Serial number exchange sequence (8 subsequences) |
| `1f8000Xx#` | XTD | Serial number related |
| `1f9000Xx#` | XTD | Serial number related |
| `1f9100Xx#` | XTD | Serial number related |
| `1fb0000Z#RrSsTtUuVvWwXxYy` | XTD | Set serial number for device Z |

**Serial Number Frame ID Structure (29-bit Extended):**
```
0x1F [SEQ][SLOT] [KEY][VALUE]
     │    │      │    │
     │    │      │    └── Serial byte (response) or Challenge (RTR)
     │    │      └─────── Key = serial[seq] XOR xor_table[seq]
     │    └────────────── Device slot on network (0-F)
     └─────────────────── Sequence number (0-7, for 8-byte serial)
```

**Key Derivation Algorithm:**
```
key[seq] = serial[seq] XOR xor_table[seq]
```
The `xor_table` is per-network (stored in PM or negotiated at startup).

**Known XOR Table A (Standalone JSM, serial 08901c8a):**
```
xor_table = [0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45]
serial    = [0x08, 0x90, 0x1C, 0x8A, 0x00, 0x00, 0x00, 0x00]
keys      = [0x08, 0xB1, 0x1E, 0x46, 0xDD, 0x12, 0x7B, 0x45]
```

**Known XOR Table B (M300 Network, serial 50c01c8f):**
```
xor_table = [0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E]
serial    = [0x50, 0xC0, 0x1C, 0x8F, 0x00, 0x00, 0x00, 0x00]
keys      = [0xD3, 0x92, 0xB1, 0x94, 0xED, 0x06, 0x2C, 0x4E]
```

**Known XOR Table C (BTM Network):**
```
xor_table = [Unknown - different from JSM tables]
keys      = [0x47, 0xA1, 0x62, 0xAD, 0x2E, 0x05, 0xB3, 0xEC]
```

**Example challenge/response (serial 08901c8a):**
```
RTR: 0x1f00 08 2f  →  Response: 0x1f01 08 08  (seq0, key=08, serial[0]=08)
RTR: 0x1f10 b1 00  →  Response: 0x1f11 b1 90  (seq1, key=B1, serial[1]=90)
RTR: 0x1f20 1e 0e  →  Response: 0x1f21 1e 1c  (seq2, key=1E, serial[2]=1C)
RTR: 0x1f30 46 48  →  Response: 0x1f31 46 8a  (seq3, key=46, serial[3]=8A)
RTR: 0x1f40 dd 00  →  Response: 0x1f41 dd 00  (seq4-7: padding zeros)
RTR: 0x1f50 12 00  →  Response: 0x1f51 12 00
RTR: 0x1f60 7b 00  →  Response: 0x1f61 7b 00
RTR: 0x1f70 45 00  →  Response: 0x1f71 45 00
```

**Multi-device networks:** All devices use same xor_table (derived from PM config).
Different networks have different xor_tables. Challenge values in RTR are ignored by devices.

**Device enumeration frames (0x1fb0000X):**
```
0x1fb00000#SSSSSSSSSSSSSSSS  - Slot 0 device serial (8 bytes)
0x1fb00001#SSSSSSSSSSSSSSSS  - Slot 1 device serial
...
```

---

## 3. CONFIGURATION MODE FRAMES

| Frame | Type | Description |
|-------|------|-------------|
| `7B3#` | STD | JSM request serial# exchange |
| `7B3#R` | RTR | PM commencing serial# exchange |
| `7B1#` | STD | PM drop to config mode 1 |
| `7B1#R` | RTR | PM request drop to config mode 1 |
| `7B0#` | STD | Drop to config mode 0, ends capability mapping, starts "run" mode |
| `7B0#R` | RTR | PM request drop to config mode 0 |
| `7E0#` | STD | Unknown purpose. Present in DongleInterface.dll binary data. May be related to diagnostics or reserved. (Source: DongleInterface.dll) |

---

## 4. MODE MAP / PARAMETER EXCHANGE

| Frame | Type | Description |
|-------|------|-------------|
| `040#00000000` | STD | Open parameter page for mode 0 |
| `04M#00000000` | STD | JSMrx select modemap M for parameter exchange (causes JSM error if not at modemap level) |
| `04M#80000000` | STD | JSMtx end parameter exchange for mode M |
| `041#00000000` | STD | Open parameter page for mode 1 |
| `041#80000000` | STD | Close parameter page for mode 1 |

### Parameter Request/Response (78X/79X) - POP Quick (Parameter Object Protocol)

> **Note:** The 0x780-0x78F / 0x790-0x79F parameter request/response frames are officially called **POP Quick** (Parameter Object Protocol) frames in R-Net documentation and the R-Net Programmer DongleInterface.dll. These are single-frame parameter exchanges, as opposed to the **POP Segmented** transfers (0x1E000000/0x1E400000 extended frames) used for multi-frame data.

**Frame ID Assignment:**
- `0x780` / `0x790` = Device slot 0 (PM) request/response
- `0x781` / `0x791` = Device slot 1 (JSM) request/response
- `0x782` / `0x792` = Device slot 2 request/response
- `0x783` / `0x793` = Device slot 3 request/response
- `0x784` / `0x794` = Device slot 4 request/response
- `0x78F` / `0x793` = R-Net Programmer request/response

**Frame Data Structure (8 bytes):**
```
Byte 0: Command type
  0x20 = Open page / Set pointer address
  0x40 = Request data at pointer
  0x41 = ACK (pointer exists)
  0x21 = Response with data
  0xC1 = Error (address not found)
  0x83 = ICS read address
  0x03 = ICS read start
  0x43 = ICS write start
  0x4F = ICS read response
  0x0F = ICS write response
  0x8F = ICS operation complete

Byte 1: Register/Page
  0x80 = Page 0 (main config)
  0x81 = Pointer register
  0x8F = Data register
  0x8C = Text data (cJSM display)
  0x8A = Unknown register
  0x8B = Unknown register
  0x40 = Mode 0 info
  0x50 = Mode status

Bytes 2-3: Usually 0x0000

Bytes 4-7: Parameter ID or Value (little-endian)
```

**Standard Parameter Exchange:**
| Frame | Type | Description |
|-------|------|-------------|
| `781#2080000011000000` | STD | JSM programming header for capability exchange |
| `78M#2P810000Xx00Vv00` | STD | JSMtx check if pointer Xx sub Vv exists |
| `78M#4P8F000000000000` | STD | JSMtx request "pointer" from PM |
| `790#4180000000000000` | STD | PMtx yes, pointer exists |
| `79M#4P81000000000000` | STD | PMtx yes, pointer exists |
| `790#218F0000XxYy0000` | STD | PMtx pointer value returned |
| `79M#2P8F0000XxYy0000` | STD | PMtx XxYy = "pointer" value |
| `79M#CP81000000000000` | STD | PMtx no, pointer does not exist |
| `79M#C181000028000000` | STD | PMtx Error: address not found |
| `79M#2P8C0000asciitxt` | STD | PMtx text chunk for color JSM display (only with programmer) |

### R-Net Programmer Protocol (78F/793)

The R-Net Programmer uses a separate protocol over 0x78F/0x793 for reading/writing device configuration:

| Frame | Description |
|-------|-------------|
| `78F#830001ff00000000` | Read address 0x00000000 |
| `78F#830001ffXXXX0000` | Read address XXXX (little-endian) |
| `78F#030001ff17000000` | Start read operation |
| `793#4f0001ff000000c8` | Read response (c8 = status) |
| `78F#430001ff410000c8` | Write command |
| `793#0f0001ff41000000` | Write response |
| `793#8f0001ff00000000` | Operation complete |

**ICS Protocol Flow (Read):**
```
1. 78F#830001ff00000000  ; Set read address 0x0000
2. 78F#030001ff17000000  ; Start read (17 = read cmd)
3. 793#4f0001ff000000c8  ; Response with data
4. 793#8f0001ff00000000  ; Read complete
```

### POP Segmented Transfers (0x1E000000/0x1E400000)

POP Segmented frames are used for multi-frame parameter transfers between devices and the programmer, as opposed to the single-frame **POP Quick** exchanges (0x78X/0x79X above).

| Frame ID | Type | Description |
|----------|------|-------------|
| `0x1E000000` | XTD | POP (Parameter Object Protocol) segmented response base ID. Node and transfer code encoded in ID bits: `0x1E000000 | (node << 15) | (tc << 18)`. Used for multi-frame parameter transfers from device to programmer. (Source: DongleInterface.dll `POP_SEG_RES_ID`) |
| `0x1E400000` | XTD | POP (Parameter Object Protocol) segmented request base ID. Node and transfer code encoded in ID bits: `0x1E400000 | (node << 15) | (tc << 18)`. Used for multi-frame parameter transfers from programmer to device. (Source: DongleInterface.dll `POP_SEG_REQ_ID`) |

### Configuration Transfer Protocol (0x1E3X-0x1E8X)

Extended frames used for bulk configuration/firmware transfer:

| Frame ID | Description |
|----------|-------------|
| `0x1E3C0001` | Transfer header (segment 1) |
| `0x1E3C0002` | Transfer header (segment 2) |
| `0x1E3D0003` | Transfer header (segment 3, includes CRC) |
| `0x1E4D0003` | Data block end |
| `0x1E4E0001` | Data block (segment 1) |
| `0x1E4F0002` | Data block (segment 2, includes CRC) |
| `0x1E3F0002` | Acknowledgment |
| `0x1E80000F` | Transfer complete/status |

**Transfer Frame Data Structure:**
```
0x1E3C0001#[SEQ][CMD][ADDR_HI][ADDR_LO][SIZE_HI][SIZE_LO][00][00]
0x1E3C0002#[ADDR_LO2][SIZE][FLAGS][00][00][00][00][00]
0x1E3D0003#[00][00][00][00][00][CRC_HI][CRC_LO]
0x1E4E0001#[SEQ][DATA...][CRC_HI][CRC_LO]
```

---

## 5. PROFILE / MODE SELECTION

| Frame | Type | Description |
|-------|------|-------------|
| `050#Ss0M00XX` | STD | Profile attribute response (same format as 060#) |
| `050#c000ff00` | STD | Profile info after init |
| `050#d000ff02` | STD | Profile info after init |
| `050#f000ff01` | STD | Profile info after init |
| `051#004M0000` | STD | JSMtx select profile M |
| `060#Ss0M00XX` | STD | Return attribute Ss of mode M as data XX |
| `060#11000002` | STD | Mode attribute |
| `060#20000000` | STD | Mode attribute |
| `060#30000001` | STD | Mode attribute |
| `060#80000080` | STD | Mode attribute |
| `060#90000000` | STD | DriveProfile joystick event stop |
| `060#90010040` | STD | LiftProfile joystick event start |
| `060#90010000` | STD | LiftProfile joystick event stop |
| `061#404M0000` | STD | JSMtx suspend mode M (M = 0x40+mode: 0x40=mode0, 0x41=mode1, ..., 0x48=mode8) |
| `061#004M0000` | STD | JSMtx select mode M (last mode must be suspended first) |
| `061#00400000` | STD | Select mode 0 (drive) |
| `061#00480000` | STD | Select mode 8 (**OBP — On-Board Programming**). Mode 8 is reserved for OBP. Activated by Horn+On/Off button combo or via mode change frames. Requires "OBP Keycode Entry"=Yes (OEM param). See `docs/OBP_ENABLE_GUIDE.md` |
| `42D#` | STD | Slot change notification. Sent when a device's slot assignment changes on the network. (Source: DongleInterface.dll `SLOT_CHANGED_STD_ID`) |
| `431#` | STD | Mode change notification. Broadcast when the active operating mode changes. (Source: DongleInterface.dll `MODE_CHANGE_ID`) |
| `436#` | STD | Profile/speed change notification. Broadcast when the active speed profile changes. (Source: DongleInterface.dll `PROFILE_CHANGE_ID`) |

---

## 6. JOYSTICK POSITION (DRIVE CONTROL)

| Frame | Type | Description |
|-------|------|-------------|
| `02000X00#XxYy` | XTD | **Joystick position. Periodic: 10ms**. X=device (typically 1). Xx=X-axis, Yy=Y-axis. Values: -100 to +100 as signed int8. `0000`=center, `0064`=full forward, `009C`=full reverse |

**Examples:**
- `02000100#0000` - Joystick centered
- `02000100#0064` - Full forward
- `02000100#64FE` - Forward + slight right
- `02000100#009C` - Full reverse

---

## 7. SPEED CONTROL

| Frame | Type | Description |
|-------|------|-------------|
| `0A040X00#Pp` | XTD | Motor speed max setting. Pp = 0x00-0x64 (0-100%), typically in 0x19 (25%) increments |
| `0A400D0M#XY` | XTD | Unknown. X={1,2,3,0xB} Y={0,1,2,3} |

**Examples:**
- `0A040100#00` - Speed 0%
- `0A040100#19` - Speed 25%
- `0A040100#32` - Speed 50%
- `0A040100#4B` - Speed 75%
- `0A040100#64` - Speed 100%

---

## 8. MOTOR / DRIVE STATUS

| Frame | Type | Description |
|-------|------|-------------|
| `06X#90010000` | STD | PMtx chair angle motor has stopped |
| `06X#90010040` | STD | PMtx chair angle motor is running |
| `0C000005#` | XTD | PMtx global motor has stopped (0 MPH) |
| `0C000006#` | XTD | PMtx global motor is decelerating |
| `14300X00#LlHh` | XTD | **PMtx drive motor current. Periodic: 200ms**. Little-endian 16-bit. 0x02e8 = ~6A |

---

## 9. HORN

| Frame | Type | Description |
|-------|------|-------------|
| `0C040X00#` | XTD | Horn start. X=origin device (100-F00 range) |
| `0C040X01#` | XTD | Horn stop. Horn can get stuck; sounds until stop frame sent |

**Example:**
```bash
cansend can0 0C040100#; sleep .2; cansend can0 0c040101#
```

---

## 10. LIGHTING / INDICATORS

| Frame | Type | Description |
|-------|------|-------------|
| `0C000401#` | XTD | Start left turn signal lamp (D=device, typically 4) |
| `0C000402#` | XTD | Start right turn signal lamp |
| `0C000403#` | XTD | Start hazard lamps |
| `0C000404#` | XTD | Start flood lamps. **Periodic: ~1000ms** |
| `0C000E00#XxYy` | XTD | Lamp indicator bitmap. Xx=mask, Yy=bitmap. 01=left, 04=right, 10=hazard, 80=flood |
| `0C000400#XxYy` | XTD | Lamp control status |

**Lamp bitmap examples:**
- `0C000400#0000` - All lights off
- `0C000400#0101` - Left lamp on
- `0C000400#0404` - Right lamp on
- `0C000400#1510` - Hazard (left+right) on
- `0C000400#8080` - Flood lights on
- `0C000400#9590` - Flood + hazard on
- `0C000400#d5d5` - Lamp test (all on)

---

## 11. TONES / AUDIO

| Frame | Type | Description |
|-------|------|-------------|
| `181C0D00#LlNnLlNnLlNnLlNn` | XTD | Play four musical tones. Ll=length (00-7F), Nn=note (00-9C, 12 notes per octave). Note >0x0b plays as 0x0b. Ll=00 Nn=00 for silence |

**Example tune:**
```bash
cansend can0 181C0D00#2050205120522053  # Play 4 ascending notes
```

---

## 12. BATTERY / POWER STATUS

| Frame | Type | Description |
|-------|------|-------------|
| `1C0C0X00#Xx` | XTD | **Battery level percentage. Periodic: 1000ms**. Xx = 0x00-0x64 (0-100%) |

---

## 13. DISTANCE / ODOMETER

| Frame | Type | Description |
|-------|------|-------------|
| `1C300X04#LlLlLlLlRrRrRrRr` | XTD | **Distance counter. Periodic: 1000ms**. Two 32-bit little-endian fields (left/right motors or dual battery banks) |

---

## 14. TIME OF DAY

| Frame | Type | Description |
|-------|------|-------------|
| `1C2C0X00#RrSsTtUuVvWw` | XTD | Time of day, little-endian format |

---

## 15. HEARTBEATS

| Frame | Type | Description |
|-------|------|-------------|
| `00E#XXXXXXXX00000000` | STD | **JSM serial number heartbeat. Periodic: 50ms** |
| `03C30F0F#8787878787878787` | XTD | **JSM device heartbeat. Periodic: 100ms** |
| `0C140X00#Xx` | XTD | **PM heartbeat. Periodic: 1000ms**. Alternates between values (0xC0, 0x01) |
| `0C140400#82` | XTD | Lamp controller heartbeat(?). **Periodic: 1000ms** |

---

## 16. MODULE STATUS / CONTROL

| Frame | Type | Description |
|-------|------|-------------|
| `0C180000#0101` | XTD | PMtx enable motor output (after change to drive mode) |
| `0C180000#020X` | XTD | PMtx enable motor output (after change to chair angle mode) |
| `0C180001#200101` | XTD | After profile change to tilt (1 of 3) |
| `0C180001#000101` | XTD | After profile change to tilt (2 of 3) |
| `0C180001#010101` | XTD | After profile change to tilt (3 of 3) |
| `0C180102#0003` | XTD | Seen during startup |
| `0C180200#0X0Y` | XTD | Unknown. x,y={0,1}. **Periodic** |
| `0C180400#0X0Y` | XTD | Unknown. X={2}, Y={1,2} alternating. **Periodic: ~125ms** |
| `0C280000#Xx` | XTD | PMtx "PM connected" - sent once after serial number exchange |

---

## 17. UI / DEVICE STATUS

| Frame | Type | Description |
|-------|------|-------------|
| `0C000205#` | XTD | JSMtx UI interaction for module 2 |
| `0C000301#` | XTD | JSMtx UI interaction for module 3 |
| `0C000303#` | XTD | JSMtx UI interaction for module 3 |
| `1C200X00#RrSsTtUuVv` | XTD | JSMrx. `0x0481000003` triggers JSM error display (but JoyXY continues) |
| `1C240X00#` | XTD | PMrx - power down JSM |
| `1C240X01#` | XTD | JSMtx - device is ready, UI is active |

---

## 18. ERROR TRIGGER FRAMES

| Frame | Type | Description |
|-------|------|-------------|
| `0C000X00#` | XTD | JSMrx - causes JSM network error (stops joystick frames) |
| `0C140000#01` | XTD | Induces error state: speed limited to ~10%, power level change has no effect (disconnected ECU error) |

---

## 19. STARTUP SEQUENCE (Real JSM)

```
1.  00C#                          ; JSM check network connection
2.  00E#08901c8a00000000          ; JSM serial heartbeat (50ms)
3.  7B3#                          ; JSM request s/n exchange
4.  7B3#R                         ; PM s/n exchange RTR
5.  1F00XXXX#R ... 1F70XXXX#R     ; PM s/n challenge (8 frames)
6.  1F01XXXX# ... 1F71XXXX#       ; JSM s/n response (8 frames)
7.  00E#... (continues)           ; JSM heartbeat continues
8.  7B1#                          ; PM drop to config mode 1
9.  7B0#R                         ; PM request config mode 0
10. 7B0#                          ; JSM config mode 0
11. 1C0C0000#XX                   ; PM battery level
12. 050#...                       ; Profile info (3 frames)
13. 0C280000#00                   ; PM connected
14. 0C140000#C0                   ; PM heartbeat
15. 0C140000#01                   ; PM heartbeat
16. 040#00000000                  ; Open parameter page
17. 781#... / 790#...             ; Parameter exchange
18. 1C240101#                     ; JSM UI active
19. 03C30F0F#87...                ; JSM heartbeat (100ms)
20. 041#80000000                  ; Close parameter page
21. 050#...                       ; Mode map
22. 061#00400000                  ; Select drive mode
23. 0C180102#0003                 ; Mode change
24. 060#...                       ; Mode attributes
25. 0C180000#0101                 ; Enable motor output
26. 0A040100#00                   ; Speed setting
27. 14300000#0000                 ; Motor current
28. 1C300004#...                  ; Distance counter
29. 02000100#0000                 ; Joystick frames begin (10ms)
```

---

## 20. BLUETOOTH MODULE (BTM) FRAMES

BTM devices use the same serial number protocol but with different XOR keys:

**BTM Serial Exchange (from pcap):**
```
Serial: Unknown BTM device
Keys observed: [0x47, 0xA1, 0x62, 0xAD, 0x2E, 0x05, 0xB3, 0xEC]

0x1F00472F#  - seq0, key=0x47
0x1F10A100#  - seq1, key=0xA1
0x1F20620E#  - seq2, key=0x62
0x1F30AD48#  - seq3, key=0xAD
0x1F402E00#  - seq4, key=0x2E
0x1F500500#  - seq5, key=0x05
0x1F60B300#  - seq6, key=0xB3
0x1F70EC00#  - seq7, key=0xEC
```

| Frame | Type | Description |
|-------|------|-------------|
| `0A400002#Xx` | XTD | BTM status (Xx=20,30,31) |
| `0A400102#Xx` | XTD | BTM status (Xx=12,13,30,31) |
| `0A400300#Xx` | XTD | BTM control (Xx=30,b0) |
| `0A400301#Xx` | XTD | BTM control (Xx=10-13,20,30,31) |

---

## 21. COLOR JSM (cJSM) AUTHENTICATION

cJSM devices use a different slot range (0x8X instead of 0x0X) for serial exchange:

**cJSM "Cry for Help" Pattern:**
When a cJSM cannot authenticate, it repeatedly sends these frames:
```
0x1F800010#  - Attempting slot 8, seq 0
0x1F800011#  - Attempting slot 8, seq 1
0x1F800012#  - Attempting slot 8, seq 2
0x1F800013#  - Attempting slot 8, seq 3
0x1F800020#  - Retrying with different parameters
0x1F810000#  - Slot 8+1 attempt
0x1FA00000#  - Unknown (possibly error state)
```

PM responses with different keys indicate XOR table mismatch:
```
0x1F900000#  - Response but key doesn't match
0x1F910000#  -
0x1F928F1C#  - Response with computed key 8F, value 1C
0x1F93C050#  - Response with computed key C0, value 50
```

---

## 22. UNKNOWN / PARTIALLY DECODED

| Frame | Type | Description |
|-------|------|-------------|
| `0A400D0M#XY` | XTD | X={1,2,3,0xB} Y={0,1,2,3} |
| `0C040D0X#` | XTD | Periodic: ~500ms (CONFLICT with horn?) |
| `0C180001#x00y0z` | XTD | x={2,0} y=1 z=1 - chair adjust mode? |
| `0C180100#XxYy` | XTD | Xx=04 Yy={2,1} ~50ms apart in clusters |
| `0C180101#020201` | XTD | Unknown |
| `0C180101#030201` | XTD | Unknown |
| `0C180201#210001` | XTD | Unknown |
| `0C180401#` | XTD | Unknown |
| `140C0X01#` | XTD | Unknown (motor related?) |
| `0C000301#` | XTD | Module 3 interaction |
| `0C000302#` | XTD | Module 3 interaction |
| `0C000303#` | XTD | Module 3 interaction |
| `0C000304#` | XTD | Module 3 interaction |

---

## 23. R-NET CONFIG FILE FORMAT (.R-net)

R-net configuration files are binary files used by the R-Net Programmer to store/restore device settings.

**File Structure:**
```
Offset 0x000: Header (32 bytes)
  - Bytes 0-3:   File type identifier
  - Bytes 4-7:   Version/flags
  - Bytes 8-15:  Timestamp or checksum
  - Bytes 16-31: Device identifier

Offset 0x020: Device configuration blocks
  - Each block: [length:2][type:2][data:n]

Offset 0x160+: Profile names (20 chars each, null-padded)
  - "Drive", "Seating", "L33tBT", "Mouse Control 1", etc.

Offset 0x210+: Profile configurations
  - Profile name (20 chars)
  - Profile settings (variable)
  - Pattern: "dddd" prefix + name + 0xf9 marker

Offset variable: Mode maps and parameter tables
  - Speed settings, turn rates, acceleration curves
  - Display text strings
  - Bluetooth pairing info
```

**Known Profile Block Types:**
```
Type 0x0003: Main config
Type 0x0007: Speed/motor settings
Type 0x0008: Display settings
Type 0x000a: Profile mappings
Type 0x0014: Mode maps
Type 0x0001: Device serial info
```

---

## Notes

1. **Frame IDs:** 3 hex chars = standard frame (11-bit), 8 hex chars = extended frame (29-bit)
2. **Device numbering:** Device 1 is typically the JSM, device 0 is typically the PM
3. **Timing is critical:** Joystick frames must arrive every 10ms or control is lost
4. **FollowJSM exploit:** Send spoofed frame within 1ms of legitimate frame
5. **JSMerror exploit:** Many frames can trigger JSM network error, allowing frame injection
6. **Serial numbers:** Can be anything, even all zeros, for EmulateJSM exploit
7. **XOR tables:** Each PM/network has a unique XOR table for serial authentication
8. **Parameter protocol (POP Quick):** 0x78X/0x79X where X = device slot number. Officially called POP Quick (Parameter Object Protocol) frames
9. **R-Net Programmer:** Uses 0x78F/0x793 with extended addressing
10. **BTM/cJSM:** Use different XOR keys; cJSM uses slot 8+ range
11. **Config transfer:** Extended frames 0x1E3X-0x1E8X for bulk data
12. **POP Segmented:** 0x1E000000 (response) and 0x1E400000 (request) base IDs for multi-frame parameter transfers. Node and transfer code encoded in ID bits
13. **DongleInterface.dll IDs:** 0x42D (slot change), 0x431 (mode change), 0x436 (profile change) are notification frames discovered via R-Net Programmer DLL reverse engineering

---

## Error Code Reporting

Error codes are transmitted on the R-Net CAN bus as part of device status communication. The PM aggregates errors from all connected modules.

### Error Code Frame Format

Error codes are 16-bit values transmitted as part of device status frames. They can be observed through:

- **On-screen display** — System faults show abbreviated text on JSM/OMNI/cJSM
- **R-Net PC Programmer** — Full error log with timestamps accessible via programmer protocol
- **On-Board Programming (OBP)** — System fault log access
- **CAN bus captures** — Error conditions visible in traffic analysis

### Error Code Ranges

| Range | Module | Manufacturer |
|-------|--------|-------------|
| 0x0001-0x0015 | Kernel (shared) | Permobil/HMC |
| 0x0001-0x8E01 | PGDT PM errors | PGDT |
| 0x1101-0x110A | Compact Joystick (CJ) | HMC International |
| 0x1201-0x120A | ESP | Permobil Design AB |
| 0x1401-0x140A | Compact Joystick Advanced (CJA) | HMC International |
| 0x1501-0x150A | MagicDrive/MagicDriveTouch | Permobil Design AB |
| 0x1601-0x160A | Co-pilot | Permobil Design AB |
| 0x1680-0x1689 | Co-pilot2 | Permobil Design AB |
| 0x1701-0x170A | Easy Rider (ER) | HMC International |
| 0x1801-0x180A | Remote Button Interface (RBI) | HMC International |
| 0x1901-0x1915 | Mini-Joystick (MJ) | HMC International |
| 0x2011-0x217D | ICS seating errors | Permobil |
| 0xFFFF | Generic module error | Any |

See `docs/RNET_ERROR_CODES.md` for the complete error code reference with descriptions and remedies.

---

## Protocol Summary

**Layer 1: Physical**
- CAN 2.0B @ 125Kbps
- Standard R-Net connector pinout

**Layer 2: Addressing**
- Standard frames (11-bit): Control, mode, profile
- Extended frames (29-bit): Data, serial, config

**Layer 3: Session**
- Serial number challenge/response authentication
- XOR-based key derivation (no crypto)
- Device slot assignment (0-F)

**Layer 4: Application**
- Joystick: 02000X00# every 10ms
- Speed: 0A040X00# on change
- Parameters: 78X#/79X# request/response
- Heartbeats: 00E#, 03C30F0F#, 0C140X00#

**Security Weaknesses:**
- No encryption
- Challenge values ignored
- Timing-based spoofing possible
- Error injection enables control takeover
