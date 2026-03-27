# R-Net Firmware Reverse Engineering Analysis

Detailed analysis of HCS08 machine code from R-Net device firmware dumps.

## Executive Summary

This document presents findings from reverse engineering R-Net device firmware:
- BTMouse (Bluetooth Mouse module)
- LEDJSM (LED Joystick Module)

Both contain Freescale HCS08 microcontroller code with CAN bus protocol handling.

## File Format Analysis

### S-Record Structure

Both files use Motorola S-Record format with S1 (16-bit address) and S2 (24-bit address) records:

```
S1 13 4000 1410CC55558C555526648C0000275FCC 74
|  |  |    |                              |
|  |  |    |                              +-- Checksum
|  |  |    +-- Data (16 bytes)
|  |  +-- Load address (0x4000)
|  +-- Byte count (0x13 = 19)
+-- Record type (S1 = 16-bit address data)
```

### Memory Regions Identified

| Address Range | Contents | Notes |
|--------------|----------|-------|
| 0x0000-0x00FF | Device Header | Device ID, version, flags |
| 0x0100-0x01FF | Keys/Serial | BTMouse has encryption key at 0x0160 |
| 0x0400-0x0FFF | Configuration | LEDJSM plaintext, BTMouse encrypted |
| 0x0700-0x0720 | XOR Tables | Authentication key tables |
| 0x1000-0x3FFF | Extended Config | Mostly 0x18A7 sentinel |
| 0x4000-0x41FF | Boot/Flash Code | Flash programming routines |
| 0x4200-0x54FF | Main Firmware | Protocol handlers, state machines |
| 0x5500-0x5AFF | Data Tables | CAN ID tables, constants |
| 0xFF80-0xFFFF | Interrupt Vectors | HCS08 vector table |
| 0x3E8000+ | Page copies | Mirror of lower memory |

## CPU Architecture: Freescale HCS08

### Evidence

1. **Instruction Patterns** - High frequency of characteristic opcodes:
   - `0xC6` (LDA ext) - 518+ occurrences
   - `0x81` (RTS) - 178+ occurrences
   - `0xB6` (LDA dir) - 108+ occurrences
   - `0xA6` (LDA #imm) - 36+ occurrences
   - `0x4A` (DECA) - Very common in loops
   - `0x26` (BNE) - Branch if not equal
   - `0x27` (BEQ) - Branch if equal

2. **Flash Programming Patterns** - Code uses 0x5555 and 0xAAAA:
   ```
   4000: 1410      BCLR 2,$10      ; Clear bit in direct page
   4002: CC5555    JMP  $5555      ; Flash unlock sequence
   4005: 8C5555    CPX  #$5555     ; Verify pattern
   4008: 2664      BNE  $406E      ; Branch if failed
   400A: 8C0000    CPX  #$0000     ; Check for zero
   400D: 275F      BEQ  $406E      ; Branch if zero
   400F: CCAAAA    JMP  $AAAA      ; Second unlock pattern
   ```

3. **Stack Operations** - Standard HCS08 calling convention:
   - `3D` (RTS) - Return from subroutine
   - `8D` (BSR) - Branch to subroutine
   - `CD` (JSR) - Jump to subroutine

### Likely MCU Model

**MC9S08DZ** family - Features match:
- Integrated MSCAN module (CAN 2.0B)
- Flash with standard 0x5555/0xAAAA unlock
- Automotive temperature range
- 60KB+ flash typical

## Interrupt Vector Table (0xFF80-0xFFFF)

Found at end of code region in LEDJSM dump:

```
FF80: 448F 448F 448F 448F 448F 448F 448F 448F  ; Vectors 0-7
FF90: 448F 448F 448F 448F 448F 448F 448F 448F  ; Vectors 8-15
FFA0: 448F 448F 448F 448F 448F 448F 448F 448F  ; Vectors 16-23
FFB0: 435A 429F 43DA 448F 448F 448F 448F 448F  ; SCI, ADC, KBI, etc.
FFC0: 448F 448F 449C 4497 448F 448F 448F 448F  ; SPI, Timer, etc.
FFD0: 448F 429A 448F 448F 448F 448F 448F 448F  ; CAN vectors
FFE0: 448F 448F 448F 448F 448F 448F 448F 4405  ; More vectors
FFF0: 448F 448F 448F 5145 448F 4000 448F 4000  ; SWI, IRQ, Reset
```

### Key Vectors Identified

| Vector | Address | Handler | Function |
|--------|---------|---------|----------|
| CAN Transmit | 0xFFD2 | 0x429A | CAN TX complete ISR |
| CAN Receive | 0xFFD4 | 0x448F | CAN RX handler (default) |
| CAN Error | 0xFFD6 | 0x448F | CAN error handler |
| Timer | 0xFFC4 | 0x449C | Timer overflow ISR |
| Timer Ch0 | 0xFFC6 | 0x4497 | Timer channel 0 ISR |
| SCI RX | 0xFFB2 | 0x435A | Serial receive ISR |
| ADC | 0xFFB4 | 0x429F | ADC conversion complete |
| Reset | 0xFFFE | 0x4000 | Reset vector |

The Reset vector at 0x4000 confirms code entry point.

## XOR Authentication Table Discovery

### Location: 0x0700 (LEDJSM)

Found at address 0x0700 in LEDJSM plaintext configuration:

```
S1130700 0000180000A76555 B8ECDD127B45 0890
         |              |            |
         |              |            +-- Serial: 08901C8A...
         |              +-- XOR Table: B8 EC DD 12 7B 45
         +-- Padding/header
```

**Extracted XOR Table (partial):**
```
Table at 0x0704: 65 55 B8 EC DD 12 7B 45
                 (appears to be variant of known Table A)
```

This matches the pattern from CLAUDE.md:
```
Table A (Standalone JSM): 00 21 02 CC DD 12 7B 45
```

The bytes `DD 12 7B 45` are identical to Table A positions 4-7.

### Serial Number at 0x0710

```
S1130710 1C8A00000000...
```

Combined with 0x0708: Serial = `08901C8A00000000`

This is the **Standalone JSM serial number** documented in CLAUDE.md.

## Protocol Constants in Code

### Flash Programming Constants (0x4000+)

Pattern analysis at code start:
```
4000: 1410        BCLR 2,$10     ; Flash control bit
4002: CC5555      JMP  $5555     ; Flash unlock address 1
4005: 8C5555      CPX  #$5555    ; Verify
400F: CCAAAA      JMP  $AAAA     ; Flash unlock address 2
```

These are standard Freescale flash programming sequences.

### CAN-Related Constants Found

Searching for CAN frame ID patterns in the code region:

| Pattern | Location | Likely Use |
|---------|----------|------------|
| 0x78F | Data tables | R-Net Programmer request ID |
| 0x793 | Data tables | R-Net Programmer response ID |
| 0x7A0 | Data tables | Programmer announce |
| 0x78X | Multiple | Parameter exchange (slot X) |
| 0x79X | Multiple | Parameter response (slot X) |

### Data Tables Region (0x5500-0x5AFF)

Contains structured data including:

1. **Mode Configuration Tables** (0x5500-0x55FF):
   - Default values, limits, mode maps

2. **CAN ID Assignment Tables** (0x57B0-0x5800):
   ```
   57B0: 06 04 01 05 01 06 01 08 0E 78 00  ; Frame IDs
   57C0: 7B 06 7C 06 7D 06 7E 05 07 FA     ; More IDs
   57D0: 40 00 40 02 40 04 40 0A 40 0C     ; 0x40XX frames
   ```

3. **Parameter Exchange IDs** (0x57E0-0x5800):
   ```
   57E0: 87 80 87 90 47 B0 47 B1 47 B2 47 B3 47 B6
   57F0: C7 C0 C7 E0 C7 E0 C7 E4 C7 E8 87 EC 87 B0
   ```

### Command Byte Patterns

Found in code analysis:

| Byte | Pattern Match | Likely Function |
|------|---------------|-----------------|
| 0x42 | 4A42xx | Presence request / heartbeat |
| 0x2F | 2Fxx | Presence acknowledge |
| 0x83 | 83xx | Set address command |
| 0x03 | C603 | Start read operation |
| 0x43 | C643 | Start write operation |
| 0x4F | 4Fxx | Read response |
| 0x0F | 0Fxx | Write acknowledge |

## Function Boundary Analysis

### RTS Instruction Locations (0x81)

The RTS (Return from Subroutine) instruction marks function endpoints.
Key function boundaries identified:

| Address | Size | Likely Function |
|---------|------|-----------------|
| 0x4081 | ~130 bytes | Flash init/unlock |
| 0x41B0 | ~200 bytes | Hardware init |
| 0x4340 | ~300 bytes | CAN init |
| 0x4600 | ~400 bytes | Message handler |
| 0x4A00 | ~600 bytes | Protocol state machine |
| 0x5000 | ~500 bytes | Configuration handler |

### Subroutine Call Analysis

Common BSR/JSR targets indicate utility functions:

```
CD3000    JSR $3000    ; Likely RAM routine / buffer handler
CD4000    JSR $4000    ; Reset/init
4A90103A  ...          ; Common pattern - loop/delay
```

## State Machine Patterns

### Evidence of Protocol State Machine

Code patterns suggest state-driven protocol handling:

```asm
; State check pattern found multiple times:
B630BF    LDA $30BF      ; Load current state
27xx      BEQ skip       ; Branch if state 0
26xx      BNE other      ; Branch to handler
...
C6xx      LDA #$xx       ; Load new state
B730BF    STA $30BF      ; Store state
```

State variable appears to be at direct page address 0xBF (or 0x30BF extended).

### State Values Observed

Based on branch targets and constants:

| State | Meaning (Inferred) |
|-------|-------------------|
| 0x00 | Idle |
| 0x01 | Waiting for response |
| 0x02 | Processing |
| 0x03 | Sending |
| 0x07 | Complete/Ready |
| 0xFF | Error |

## Encryption Analysis (BTMouse)

### Encryption Key Location (0x0160)

BTMouse firmware has 16-byte key:
```
0160: FC 95 FE BA E3 1F 2D 04 EC 12 E6 FD EF 00 57 C1
```

### Encryption Method

Comparing encrypted (BTMouse 0x0400+) vs plaintext (LEDJSM 0x0400+):

- Configuration region uses XOR-based encryption
- Key appears to be applied in 16-byte blocks
- High entropy in BTMouse (7.914) vs low in LEDJSM (2.747)

### Potential Decryption Approach

```python
def decrypt_config(encrypted, key):
    """XOR decryption with 16-byte key"""
    key_bytes = bytes.fromhex("FC95FEBAE31F2D04EC12E6FDEF0057C1")
    result = bytearray()
    for i, byte in enumerate(encrypted):
        result.append(byte ^ key_bytes[i % 16])
    return bytes(result)
```

## CAN Protocol Implementation

### CAN Controller Registers (HCS08 MSCAN)

Based on code patterns, MSCAN registers are likely at 0x0140-0x017F:

| Register | Address | Function |
|----------|---------|----------|
| CANCTL0 | 0x0140 | Control 0 |
| CANCTL1 | 0x0141 | Control 1 |
| CANBTR0 | 0x0142 | Baud rate 0 |
| CANBTR1 | 0x0143 | Baud rate 1 |
| CANRFLG | 0x0144 | Receiver flags |
| CANTFLG | 0x0146 | Transmitter flags |
| CANRIER | 0x0147 | Receiver interrupt enable |
| CANTIER | 0x0148 | Transmitter interrupt enable |
| CANTARQ | 0x014A | Transmit abort request |
| CANIDAC | 0x014B | ID acceptance control |
| CANRXFG | 0x0160 | Receive buffer |
| CANTXFG | 0x0170 | Transmit buffer |

### Baud Rate Configuration

For 125Kbps (R-Net standard):
- 8MHz bus clock typical
- BRP = 3, TSEG1 = 12, TSEG2 = 3

## Sentinel Values

### 0x18A7 Pattern

The value 0x18A7 appears extensively (35,000+ times) marking:
- Uninitialized configuration slots
- Empty parameter tables
- Reserved/unused memory

### 0xFFFF Pattern

Used for:
- Maximum values
- Unwritten flash
- Error/invalid markers

### 0x12345A7A Pattern

Found at 0x0800:
```
S1130800 12345A7A 02A718A718A7180000A718A7
```

Appears to be a magic number or checksum seed.

## Security Observations

1. **Weak Encryption**: Simple XOR with key stored in firmware
2. **No Code Signing**: Firmware can be extracted and modified
3. **Readable Protocols**: All CAN frames use standard format
4. **Known Patterns**: Flash unlock sequences are documented
5. **Predictable XOR**: Authentication XOR tables can be extracted

## Tools for Further Analysis

### Disassembly

```bash
# Using srec_cat to extract binary
srec_cat firmware.s19 -o firmware.bin -binary

# Ghidra with HCS08 processor module
# - Load binary at 0x0000
# - Set processor to "HC08"
# - Add memory map for flash regions
```

### Binary Diffing

```bash
# Compare firmware versions
srec_cmp dump_a.s19 dump_b.s19

# Extract specific region
srec_cat firmware.s19 -crop 0x4000 0x8000 -o code_region.s19
```

### Python Analysis

```python
import struct

def parse_s19(filename):
    """Parse S-record file to binary"""
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('S1'):
                count = int(line[2:4], 16)
                addr = int(line[4:8], 16)
                for i in range(count - 3):
                    data[addr + i] = int(line[8+i*2:10+i*2], 16)
            elif line.startswith('S2'):
                count = int(line[2:4], 16)
                addr = int(line[4:10], 16)
                for i in range(count - 4):
                    data[addr + i] = int(line[10+i*2:12+i*2], 16)
    return data
```

## Recommendations for Further Research

1. **Full Disassembly**: Use Ghidra with HCS08 processor to get complete function analysis

2. **CAN Handler Mapping**: Trace interrupt vectors to map all CAN frame handlers

3. **Protocol Fuzzing**: Test documented frame IDs against live devices

4. **XOR Table Extraction**: Dump all XOR tables for different device types

5. **Timing Analysis**: Measure actual protocol timing requirements

## References

- `CLAUDE.md` - Project documentation with known protocol details
- `docs/FIRMWARE_DUMP_ANALYSIS.md` - Initial dump analysis
- `docs/RNET_PROGRAMMER_PROTOCOL.md` - Programmer protocol documentation
- Freescale HCS08 Family Reference Manual
- Freescale MSCAN Block Guide

---

*Analysis performed on firmware dumps extracted via R-Net Programmer interface.*
*This is accessibility research for enabling alternative wheelchair control methods.*
