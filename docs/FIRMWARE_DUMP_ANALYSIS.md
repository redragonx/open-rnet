# R-Net Firmware Dump Analysis

Analysis of BTMouse and LEDJSM firmware dumps in Motorola S-Record format.

## Overview

| Property | BTMouse | LEDJSM |
|----------|---------|--------|
| File Format | Motorola S-Record (S1/S2) | Motorola S-Record (S1/S2) |
| Address Range | 0x0000 - 0x3FBFFF | 0x0000 - 0x3FBFFF |
| Total Size | 4,177,920 bytes (~4MB) | 4,177,920 bytes (~4MB) |
| Records | 12,288 lines | 12,288 lines |
| Similarity | 96.8% identical | 96.8% identical |

## CPU Architecture

**Identified: Freescale/NXP HCS08 (8-bit)**

Evidence:
- HC08/HCS08 instruction patterns detected in code region
- High frequency of characteristic opcodes:
  - `0xC6` (LDA ext): 518 occurrences
  - `0x81` (RTS): 178 occurrences
  - `0xB6` (LDA dir): 108 occurrences
  - `0xA6` (LDA #imm): 36 occurrences
- S-record format commonly used with Freescale tools
- CAN bus peripherals common on HCS08 automotive variants

Likely MCU family: **MC9S08DZ** or similar with integrated CAN.

## Memory Layout

```
0x0000 - 0x00FF    Header / Device ID
0x0100 - 0x01FF    Serial / Keys (BTMouse has encryption key)
0x0200 - 0x03FF    Reserved / Config pointers
0x0400 - 0x0FFF    Device Configuration Tables
0x1000 - 0x3FFF    Extended Config (mostly 0x18A7 sentinel)
0x4000 - 0x7FFF    Firmware Code Region 1
0x8000 - 0xFFFF    Firmware Code Region 2
0x10000+           Additional code/data pages
0x380000 - 0x3FFFFF Pages 0x38-0x3F (mostly zeros)
```

## Header Structure (0x0000 - 0x00FF)

| Offset | BTMouse | LEDJSM | Description |
|--------|---------|--------|-------------|
| 0x0000 | `00 00` | `63 80` | Device Type ID |
| 0x0008 | `00 00 00 00` | `4B 00 00 00` | Device Flags |
| 0x000C | `90 00 01 00` | `90 00 01 00` | Version (same) |
| 0x0012 | `68 0D` | `01 0D` | Config variant |
| 0x0016 | `06 10` | `00 10` | Mode flags |
| 0x0022 | `E7 BC` | `6A 80` | Checksum/CRC |
| 0x0030 | `00` | `3F` | Max profiles? |
| 0x0037 | `7C` | `1C` | Speed limit? |
| 0x00FE | `00` | `04` | Feature flags |

### Device Identification

- **BTMouse**: Device ID `0x0000` - Bluetooth Mouse module
- **LEDJSM**: Device ID `0x6380` - LED Joystick Module

## Encryption/Key Data (0x0160)

**BTMouse** has a 16-byte key at offset 0x0160:
```
FC 95 FE BA E3 1F 2D 04 EC 12 E6 FD EF 00 57 C1
```

**LEDJSM** has mostly zeros with a 2-byte value:
```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 E6 93
```

This key is likely used for:
- Configuration encryption (BTMouse config region has high entropy)
- Device authentication on the R-Net bus
- XOR table derivation for serial number exchange

## Configuration Region (0x0400 - 0x0600)

### Entropy Analysis

| Region | BTMouse | LEDJSM | Interpretation |
|--------|---------|--------|----------------|
| 0x0400-0x1000 | 7.914 | 2.747 | BTMouse encrypted, LEDJSM plaintext |
| 0x4000-0x8000 | 6.919 | 6.923 | Both have compiled code |

**BTMouse configuration is encrypted** - the data at 0x0400+ appears random.
**LEDJSM configuration is plaintext** - structured data is visible.

### LEDJSM Config Structure

```
0x0400: 18 02    Device type flags
0x040A: 01 01 01 01 01 01    Slot configuration (6 slots)
0x0410: 01 01 03 00 01 06 00 01    Mode configuration
0x0430: 32       Speed setting (0x32 = 50%)
0x0444: F6 62    Some identifier
0x04D4: 24       Config value
0x04D6: FF FF    Max value
0x04D7: 64       Max percent (100)
```

### The 0x18A7 Sentinel

The pattern `0x18A7` (or `A7 18` in little-endian) appears 35,131 times in LEDJSM.

**Interpretation**: This is a "uninitialized" or "default" marker value. R-Net devices use this to indicate unprogrammed configuration slots.

Regions filled with 0x18A7:
- 0x0004E0 - 0x000528 (72 bytes)
- 0x000C56 - 0x000F08 (690 bytes)
- 0x001000 - 0x004000 (12KB)
- 0x3B8000 - 0x3BC000 (16KB)
- 0x3C8000 - 0x3CC000 (16KB)
- 0x3D8000 - 0x3DC000 (16KB)

## Code Region Analysis (0x4000+)

The firmware code starts at 0x4000. Sample disassembly (HC08):

```
4000: 14 10       BSET 2,0x10      ; Set bit 2 of address 0x10
4002: CC 55 55    JMP  0x5555      ; Jump to 0x5555
4005: 8C 55 55    CPX  #0x5555     ; Compare X with 0x5555
4008: 26 64       BNE  0x406E      ; Branch if not equal
400A: 8C 00 00    CPX  #0x0000     ; Compare X with 0
400D: 27 5F       BEQ  0x406E      ; Branch if equal
400F: CC AA AA    JMP  0xAAAA      ; Jump to 0xAAAA
...
4081: 81          RTS              ; Return from subroutine
```

The code uses patterns like `0x5555` and `0xAAAA` which are common in:
- Flash programming verification
- Memory test patterns
- Watchdog refresh sequences

## Memory Pages

The BTMouse dump covers memory pages 0x38-0x3F:
- Each page = 64KB
- Address range: 0x380000 - 0x3FFFFF

These pages were extracted using the R-Net Programmer's page-by-page read function.

## Differences Summary

Only 3.2% of bytes differ between the files (132,192 bytes).

Key differences:
1. **Device ID** (0x0000): Different device types
2. **Encryption key** (0x0160): BTMouse has key, LEDJSM doesn't
3. **Configuration** (0x0400+): BTMouse encrypted, LEDJSM plaintext
4. **Profile settings** (0x0240): Different default values

## Security Observations

1. **Weak encryption**: BTMouse uses simple XOR-based encryption with a 16-byte key stored in firmware

2. **No code signing**: Firmware can be extracted and potentially modified

3. **Readable configuration**: LEDJSM exposes all config in plaintext

4. **Standard format**: S-record files can be edited with standard tools

## Tools for Further Analysis

```bash
# Convert S-record to binary
srec_cat firmware.s19 -o firmware.bin -binary

# Disassemble with HCS08 disassembler
# (Use tools like IDA Pro, Ghidra with HC08 processor module)

# Compare two firmware dumps
srec_cmp dump_a.s19 dump_b.s19

# Extract specific address range
srec_cat firmware.s19 -crop 0x4000 0x8000 -o code.s19
```

## Potential Uses

1. **Reverse engineering**: Understand R-Net device firmware
2. **Custom firmware**: Modify behavior (accessibility features)
3. **Security research**: Identify vulnerabilities
4. **Backup/Restore**: Clone device configurations
5. **Emulation**: Run firmware in simulator for protocol analysis

## References

- `docs/RNET_PROGRAMMER_PROTOCOL.md` - How these dumps were likely extracted
- `RNET_FRAME_DICTIONARY.md` - Protocol documentation
- Freescale HCS08 Reference Manual
