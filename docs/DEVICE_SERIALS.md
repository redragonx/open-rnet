# R-Net Device Registry

**Manufacturer:** Penny & Giles (now Curtiss-Wright Controls)
**Protocol:** R-Net CAN 2.0B @ 125Kbps
**Wheelchair Models:** Permobil M300, M400, Quickie, Sunrise Medical

---

## Device List

| Serial | Type | Name | Network | Slot | Function |
|--------|------|------|---------|------|----------|
| `08901c8a` | JSM | Standalone JSM | Table A | 1 | Joystick control |
| `50c01c8f` | cJSM | M300 Color JSM | Table B | 3 | Joystick + LCD display |
| `8f80198b` | BTM | SuperBlueTooth | Table B | 1 | Bluetooth pairing |
| `0c01148b` | PM | Power Module | Table B | 0 | Motor/power control |
| `1697000003500201` | IOM | I/O Module v2.1 | Table B | 4 | Lights, accessories |
| `e48c1c8c` | ? | Unknown | Table B | 2 | Unknown |
| `2f000e48` | ? | Unknown | Table A | 0 | Powerup sequence |

---

## Joystick Modules (JSM)

### 08901c8a - Standalone JSM
| Field | Value |
|-------|-------|
| Serial | `08901c8a` |
| Type | Standard JSM (Joystick Module) |
| Network | Standalone (single device) |
| XOR Table | A - `[0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45]` |
| Slot | 1 |
| Heartbeat | `00E#08901c8a00000000` (50ms) |
| Device Heartbeat | `03C30F0F#8787878787878787` (100ms) |
| Captures | JSMpoweronreal, bluetooth_ASNEWDEVICE, ledJSM_afterconnect, poweronJSMsh |

**Byte Breakdown:**
```
Byte 0: 0x08 (Unit ID Low)
Byte 1: 0x90 (Unit ID High)
Byte 2: 0x1c (Product: JSM)
Byte 3: 0x8a (Variant: Standalone)
```

### 50c01c8f - M300 JSM
| Field | Value |
|-------|-------|
| Serial | `50c01c8f` |
| Type | M300 Color JSM (cJSM) |
| Wheelchair | Permobil M300 |
| Network | Multi-device (with BTM, IOM, PM) |
| XOR Table | B - `[0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E]` |
| Slot | 3 (in M300 network) |
| Heartbeat | `00E#50c01c8f00000000` (50ms) |
| Profiles | Drive, Seating, L33tBT, Mouse Control 1/2, Output Mode, IR Control, Programming |
| Custom Modes | Noob Mode, Godly Mode, Profile 3-7, Attendant |
| Captures | Most M300 captures (full_action_dump, ics_*, programmer_*, etc.) |

**Byte Breakdown:**
```
Byte 0: 0x50 (Unit ID Low)
Byte 1: 0xc0 (Unit ID High)
Byte 2: 0x1c (Product: JSM)
Byte 3: 0x8f (Variant: M300)
```

---

## Bluetooth Module (BTM)

### 8f80198b - BTM
| Field | Value |
|-------|-------|
| Serial | `8f80198b` |
| Type | Bluetooth Module |
| Name | SuperBlueTooth |
| Network | M300 multi-device |
| XOR Table | B (same as M300 network) |
| Slot | 1 |
| Function | Bluetooth pairing, external device control |
| Status Frames | `0x0A400002#`, `0x0A400102#`, `0x0A400300#`, `0x0A400301#` |
| Captures | bluetooth_sept20, cJSM+lJSM+dualcan, full_action_dump, power_bluetooth |

**Byte Breakdown:**
```
Byte 0: 0x8f (Unit ID Low)
Byte 1: 0x80 (Unit ID High)
Byte 2: 0x19 (Product: BTM)
Byte 3: 0x8b (Variant: Standard)
```

---

## Power Module (PM)

### 0c01148b - PM/Controller
| Field | Value |
|-------|-------|
| Serial | `0c01148b` |
| Type | Power Module / Main Controller |
| Network | M300 multi-device |
| XOR Table | B |
| Slot | 0 (master) |
| Function | Motor control, power management, device coordination |
| Parameter Frames | `0x780#` (request) / `0x790#` (response) |
| Captures | ics_write_config, programmer_dump, programmer_write |

**Byte Breakdown:**
```
Byte 0: 0x0c (Unit ID Low)
Byte 1: 0x01 (Unit ID High)
Byte 2: 0x14 (Product: PM)
Byte 3: 0x8b (Variant: Standard)
```

---

## I/O Module (IOM)

### 1697000003500201 - IOM
| Field | Value |
|-------|-------|
| Serial | `1697000003500201` (8-byte) |
| Type | I/O Expansion Module |
| Product ID | 0x1697 |
| Model | 3.80 |
| Version | 2.1 |
| Network | M300 multi-device |
| Slot | 4 |
| Function | Additional I/O, lights, accessories |
| Captures | aug19th_hotplug, cJSM+lJSM, full_action_dump, ics_*, programmer_* |

**Byte Breakdown:**
```
Bytes 0-1: 0x1697 (Product ID)
Bytes 2-3: 0x0000 (Reserved)
Bytes 4-5: 0x0350 (Model: 3.80)
Bytes 6-7: 0x0201 (Version: 2.1)
```

---

## Unknown Modules

### e48c1c8c - Unknown
| Field | Value |
|-------|-------|
| Serial | `e48c1c8c` |
| Type | Unknown (JSM family based on byte 2) |
| Network | M300 multi-device |
| Slot | 2 |
| Captures | aug19th_hotplug, cJSM+lJSM+dualcan, full_action_dump |

**Byte Breakdown:**
```
Byte 0: 0xe4 (Unit ID Low)
Byte 1: 0x8c (Unit ID High)
Byte 2: 0x1c (Product: JSM family?)
Byte 3: 0x8c (Variant: Unknown)
```

### 2f000e48 - Unknown
| Field | Value |
|-------|-------|
| Serial | `2f000e48` |
| Type | Unknown (different device class) |
| Network | Standalone JSM network |
| Slot | 0 |
| Notes | Appears during powerup sequences |
| Captures | JSMpoweronreal, poweronJSMsh |

**Byte Breakdown:**
```
Byte 0: 0x2f (Unit ID Low)
Byte 1: 0x00 (Unit ID High)
Byte 2: 0x0e (Product: Unknown)
Byte 3: 0x48 (Variant: Different class)
```

---

## Network Configurations

### Standalone Network (Table A)
```
Slot 0: 2f000e48 (Unknown)
Slot 1: 08901c8a (Standalone JSM)
```

### M300 Network (Table B)
```
Slot 0: 0c01148b (PM - Power Module)
Slot 1: 8f80198b (BTM - Bluetooth)
Slot 2: e48c1c8c (Unknown)
Slot 3: 50c01c8f (JSM - Joystick)
Slot 4: 1697000003500201 (IOM - I/O Module)
```

---

## Serial Number Format

### 4-Byte Devices (JSM, BTM, PM)
```
[B0][B1][B2][B3]
  │   │   │   └── Device Variant (0x8a-0x8f, 0x48)
  │   │   └────── Product Family (0x1c=JSM, 0x19=BTM, 0x14=PM, 0x0e=?)
  │   └────────── Unit ID High Byte
  └────────────── Unit ID Low Byte
```

### 8-Byte Devices (IOM)
```
[Product ID][Reserved][Model][Version]
   2 bytes    2 bytes  2 bytes 2 bytes
```

---

## Product Family Codes (Byte 2)

| Code | Product Family |
|------|----------------|
| 0x1c | JSM (Joystick Module) |
| 0x19 | BTM (Bluetooth Module) |
| 0x14 | PM (Power Module) |
| 0x0e | Unknown |

## Device Variant Codes (Byte 3)

| Code | Variant |
|------|---------|
| 0x8a | Standalone JSM |
| 0x8b | BTM / PM (shared) |
| 0x8c | Unknown module |
| 0x8f | M300 JSM |
| 0x48 | Different device class |

---

## Device Capabilities

### cJSM (Color Joystick Module)
- Color LCD display
- Profile switching
- Mode indicators (dddP, dddA, dddG, dddN, dddI, dddO, dddS)
- Text display via register 0x8C
- Slot 8+ authentication (0x1F8X range)

### lJSM (LED Joystick Module)
- LED display (simpler than cJSM)
- Indoor/Outdoor/Speed mode indicators
- Environmental profile support

### BTM (Bluetooth Module)
- External device pairing
- Smartphone/tablet control
- Alternative input methods

### IOM (I/O Module)
- Lighting control
- Accessory ports
- Expansion I/O

---

## R-Net Programmer Data

| Field | Value |
|-------|-------|
| Wheelchair Models | M300, M400 |
| Config Type | G basic |
| Price/Code | USD1299 |
| Capture Dates | 2016-01-27, 2017-07-13 |
| Config Source | src_b_32 |

---

## Authentication

Each device authenticates using XOR-derived keys:

```
Key[seq] = Serial[seq] XOR Table[seq]
```

**XOR Table A (Standalone):**
```
[0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45]
```

**XOR Table B (M300 Network):**
```
[0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E]
```

All devices on the same network share the same XOR table.

---

## Derived Authentication Keys

### Keys for 08901c8a (Standalone JSM)
| Seq | Serial Byte | XOR Table | Key |
|-----|-------------|-----------|-----|
| 0 | 0x08 | 0x00 | 0x08 |
| 1 | 0x90 | 0x21 | 0xB1 |
| 2 | 0x1C | 0x02 | 0x1E |
| 3 | 0x8A | 0xCC | 0x46 |
| 4 | 0x00 | 0xDD | 0xDD |
| 5 | 0x00 | 0x12 | 0x12 |
| 6 | 0x00 | 0x7B | 0x7B |
| 7 | 0x00 | 0x45 | 0x45 |

### Keys for 50c01c8f (M300 JSM)
| Seq | Serial Byte | XOR Table | Key |
|-----|-------------|-----------|-----|
| 0 | 0x50 | 0x83 | 0xD3 |
| 1 | 0xC0 | 0x52 | 0x92 |
| 2 | 0x1C | 0xAD | 0xB1 |
| 3 | 0x8F | 0x1B | 0x94 |
| 4 | 0x00 | 0xED | 0xED |
| 5 | 0x00 | 0x06 | 0x06 |
| 6 | 0x00 | 0x2C | 0x2C |
| 7 | 0x00 | 0x4E | 0x4E |

---

## Serial Number Sources

### 1. JSM Serial Heartbeat (Frame ID: 0x00E)
Broadcast every 50ms with 8-byte serial (4 bytes serial + 4 bytes padding):
```
00E#08901c8a00000000  → Serial: 08901c8a
00E#50c01c8f00000000  → Serial: 50c01c8f
```

### 2. Device Enumeration (Frame ID: 0x1FB0000X)
Full 8-byte serial per slot:
```
1FB00002#8f80198b00000000  → Slot 2: BTM
1FB00004#50c01c8f00000000  → Slot 4: M300 JSM
1FB00005#1697000003500201  → Slot 5: IOM
```

### 3. Authentication Frames (0x1FXXXXXX)
Serial bytes transmitted via challenge/response:
```
Frame ID Format: 0x1F [SEQ][SLOT] [KEY][VALUE]
  SEQ = sequence 0-7
  SLOT = device slot on network
  KEY = serial[seq] XOR xor_table[seq]
  VALUE = serial byte (in responses)
```

---

## cJSM Slot 8+ Authentication

The Color JSM uses slot 8 and above (0x1F8X range):
```
1F800010  → Slot 8, Seq 0, trying to authenticate
1F800011  → Slot 8, Seq 1
1F800012  → Slot 8, Seq 2
1F800013  → Slot 8, Seq 3
1F810000  → Error/retry state
1FA00000  → Authentication failed
```

When cJSM can't authenticate, it enters a "cry for help" pattern repeating these frames.

---

## Source Captures

| Serial | Captures Found In |
|--------|-------------------|
| `08901c8a` | JSMpoweronreal, bluetooth_ASNEWDEVICE, ledJSM_afterconnect, poweronJSMsh |
| `50c01c8f` | Most M300 captures (full_action_dump, July12_lights2, ics_*, programmer_*, etc.) |
| `8f80198b` | bluetooth_sept20, cJSM+lJSM+dualcan, full_action_dump, power_bluetooth |
| `e48c1c8c` | aug19th_hotplug, cJSM+lJSM+dualcan, full_action_dump, ics_*, programmer_* |
| `0c01148b` | ics_write_config, programmer_dump, programmer_write |
| `1697000003500201` | aug19th_hotplug, cJSM+lJSM, full_action_dump, ics_*, programmer_* |

---

## Extraction Commands

```bash
# Extract JSM heartbeat serials
tshark -r capture.pcapng -T fields -e can.id -e data | \
  awk '$1 == 14 {print $2}'

# Extract device enumeration
tshark -r capture.pcapng -T fields -e can.id -e data | \
  awk '$1 >= 532676608 && $1 <= 532676623 {print}'

# Use rnet_utils.py
python3 rnet_utils.py extract-auth capture.log
python3 rnet_utils.py decode-serial 08901c8a
```
