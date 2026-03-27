# cJSM Display Protocol Analysis

**Color Joystick Module (cJSM) display communication over R-Net CAN bus**

## Overview

The Color JSM (cJSM) uses the standard R-Net parameter exchange protocol to receive display text and configuration. Unlike a traditional bitmap display, the cJSM receives **text strings** and **display parameters** rather than raw pixel data.

## Authentication

The cJSM uses slot 8+ (0x1F8X range) for serial number authentication:

```
Slot 8 auth frames: 0x1F80XXXX - 0x1F8FXXXX
```

When authentication fails, the cJSM enters a "cry for help" pattern:
```
1F800010#, 1F800011#, 1F800012#, 1F800013#  ; Repeated attempts
1F810000#, 1FA00000#  ; Retry/error state
```

## Display Text Protocol

Text is transferred via the parameter exchange protocol using register 0x8C:

### Frame Format
```
Request:  0x78X#208CXXXX...  (X = slot)
Response: 0x79X#208CXXXX...

Data format:
  Byte 0: 0x20 (data type = text)
  Byte 1: 0x8C (register = text display)
  Bytes 2-3: 0x0000
  Bytes 4-7: ASCII text (4 characters)
```

### Example Text Transfer
Profile names are sent in 4-character chunks:

| Frame Data | Decoded |
|------------|---------|
| `208c000044726976` | "Driv" |
| `208c000065202020` | "e   " |
| `208c000053656174` | "Seat" |
| `208c0000696e6720` | "ing " |
| `208c00004c333374` | "L33t" |
| `208c000042542020` | "BT  " |
| `208c00004d6f7573` | "Mous" |
| `208c00006f6e7472` | "ontr" |
| `208c00006f6c2020` | "ol  " |
| `208c00004f757470` | "Outp" |
| `208c00007574204d` | "ut M" |
| `208c00006f646520` | "ode " |
| `208c000050726f67` | "Prog" |
| `208c000072616d6d` | "ramm" |
| `208c0000696e6720` | "ing " |

Profile prefixes (mode indicators):
- `64646450` = "dddP" (Profile)
- `64646441` = "dddA" (Attendant)
- `64646447` = "dddG" (Godly)
- `6464644e` = "dddN" (Noob)

## Mode Configuration Frames (0x1ECXXXXX)

Extended frames in the 0x1EC range appear to transfer mode/profile configuration:

### Frame ID Structure
```
0x1EC [Mode] [SubAddr] [Type]
      │       │         │
      │       │         └── Data type (0x00=init, 0x40=config, 0x60=param, etc.)
      │       └────────────  Sub-address within mode
      └────────────────────  Mode index (0-5)
```

### Data Types
| Type Suffix | Description |
|-------------|-------------|
| `0x00` | Initialization (usually zeros) |
| `0x40` | Configuration header (`0103000000000000`) |
| `0x60` | Mode parameters |
| `0x61` | Extended mode data |
| `0x62` | Mode serial/XOR data |
| `0x80` | Status (usually zeros) |
| `0xC0`, `0xF0` | Flags (`0100000000000000`) |

### Mode Parameter Format (0x...61)
```
Bytes 0-1: Slot/index prefix
Bytes 2-3: Data type (0x80 = button, 0x40 = action)
Bytes 4-5: Address/parameter ID
Bytes 6-7: Value
```

Example mode entries:
```
0001028000400200  ; Slot 0, button 0x0280, action 0x0002
0003038000400500  ; Slot 0, button 0x0380, action 0x0005
0007048000400400  ; Slot 0, button 0x0480, action 0x0004
```

## Device Enumeration

Device enumeration frames (0x1FB0000X) contain full 8-byte serial numbers:

```
1FB00002#8f80198b00000000  ; Device at slot 2
1FB00004#50c01c8f00000000  ; Device at slot 4 (JSM serial)
1FB00005#1697000003500201  ; Device at slot 5
```

## No Bitmap Graphics

**Important:** The cJSM does NOT receive raw bitmap/pixel data over CAN. Instead:

1. **Text is sent as ASCII strings** via register 0x8C
2. **Icons/graphics are built into the cJSM firmware**
3. **Mode parameters configure which built-in graphics to display**
4. **Colors may be specified via parameters, not pixel data**

The 8-byte CAN frame limitation makes transferring bitmap images impractical - even a small 32x32 monochrome icon would require 128+ frames.

## Frame Summary

| Frame Range | Purpose |
|-------------|---------|
| `0x78X#208C...` | Text display request |
| `0x79X#208C...` | Text display response |
| `0x1EC0XXXX` - `0x1EC5XXXX` | Mode configuration |
| `0x1F80XXXX` - `0x1F8FXXXX` | cJSM slot 8 authentication |
| `0x1FB0000X` | Device enumeration |

## Decoding Text from Captures

To extract display text from a pcap:

```bash
tshark -r capture.pcapng -T fields -e data 2>/dev/null | \
  grep "^208c" | cut -c9-16 | xxd -r -p
```

Or use the Python utility:

```python
# Extract 0x8C register data
data = bytes.fromhex("44726976")  # From frame 208c000044726976
text = data.decode('ascii')  # "Driv"
```

## References

- Main protocol documentation: `RNET_PROTOCOL_GUIDE.md`
- Frame dictionary: `RNET_FRAME_DICTIONARY.md`
- Analysis source: `wireshark/aug19th_hotplug_cjsm.pcapng`
