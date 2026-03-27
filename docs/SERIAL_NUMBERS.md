# R-Net Serial Numbers

**All device serial numbers extracted from R-Net CAN bus captures**

## Unique Device Serial Numbers

| Serial Number | Device Type | Notes |
|---------------|-------------|-------|
| `08901c8a` | Standalone JSM | Used in JSMpoweronreal, bluetooth captures |
| `50c01c8f` | M300 JSM | Primary wheelchair JSM, most captures |
| `8f80198b` | BTM (Bluetooth Module) | Bluetooth module |
| `e48c1c8c` | Unknown Module | Appears in multi-device networks |
| `0c01148b` | Unknown Module | PM or other controller |
| `1697000003500201` | IOM/Other | 8-byte serial, IO module? |
| `2f000e48` | Unknown | Appears in powerup sequences |

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

## Serials by Slot (from Auth Frames)

### Multi-device M300 Network
| Slot | Serial | Device |
|------|--------|--------|
| 0 | `0c01148b` | PM/Controller |
| 1 | `8f80198b` | BTM |
| 2 | `e48c1c8c` | Unknown |
| 3 | `50c01c8f` | M300 JSM |
| 4 | `1697000003500201` | IOM |

### Standalone JSM Network
| Slot | Serial | Device |
|------|--------|--------|
| 0 | `2f000e48` | Unknown |
| 1 | `08901c8a` | Standalone JSM |

## XOR Table Associations

| Serial | XOR Table | Key Values |
|--------|-----------|------------|
| `08901c8a` | Table A (Standalone) | `[0x00,0x21,0x02,0xCC,0xDD,0x12,0x7B,0x45]` |
| `50c01c8f` | Table B (M300) | `[0x83,0x52,0xAD,0x1B,0xED,0x06,0x2C,0x4E]` |
| `8f80198b` | Table B (M300) | Same as M300 network |

## Derived Authentication Keys

### Serial 08901c8a (Standalone JSM)
```
Seq | Serial Byte | XOR Table | Key
----|-------------|-----------|-----
0   | 0x08        | 0x00      | 0x08
1   | 0x90        | 0x21      | 0xB1
2   | 0x1C        | 0x02      | 0x1E
3   | 0x8A        | 0xCC      | 0x46
4   | 0x00        | 0xDD      | 0xDD
5   | 0x00        | 0x12      | 0x12
6   | 0x00        | 0x7B      | 0x7B
7   | 0x00        | 0x45      | 0x45
```

### Serial 50c01c8f (M300 JSM)
```
Seq | Serial Byte | XOR Table | Key
----|-------------|-----------|-----
0   | 0x50        | 0x83      | 0xD3
1   | 0xC0        | 0x52      | 0x92
2   | 0x1C        | 0xAD      | 0xB1
3   | 0x8F        | 0x1B      | 0x94
4   | 0x00        | 0xED      | 0xED
5   | 0x00        | 0x06      | 0x06
6   | 0x00        | 0x2C      | 0x2C
7   | 0x00        | 0x4E      | 0x4E
```

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

## Source Captures

| Capture File | Serials Found |
|--------------|---------------|
| JSMpoweronreal.pcapng | `08901c8a` |
| bluetooth_ASNEWDEVICE_onOLDCHAIR_Sept20.pcapng | `08901c8a`, `8f80198b` |
| cJSM+lJSM+dualcan.pcapng | `50c01c8f`, `8f80198b`, `e48c1c8c`, + |
| full_action_dumpJuly2_2016.pcapng | `50c01c8f`, `8f80198b`, `e48c1c8c`, + |
| ics_write_config.pcapng | `50c01c8f`, `e48c1c8c`, `1697...` |
| programmer_dump_file_july2017.pcapng | `50c01c8f`, `e48c1c8c`, `1697...` |

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
