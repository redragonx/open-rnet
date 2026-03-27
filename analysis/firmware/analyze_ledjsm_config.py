#!/usr/bin/env python3
"""
Analyze LEDJSM plaintext configuration and generate documentation.
"""

import sys
from collections import Counter


def parse_s19(filename: str) -> dict[int, int]:
    """Parse Motorola S-record file."""
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('S1'):
                count = int(line[2:4], 16)
                addr = int(line[4:8], 16)
                for i in range(count - 3):
                    byte_offset = 8 + i * 2
                    data[addr + i] = int(line[byte_offset:byte_offset + 2], 16)
            elif line.startswith('S2'):
                count = int(line[2:4], 16)
                addr = int(line[4:10], 16)
                for i in range(count - 4):
                    byte_offset = 10 + i * 2
                    data[addr + i] = int(line[byte_offset:byte_offset + 2], 16)
    return data


def extract_region(data: dict[int, int], start: int, length: int) -> bytes:
    return bytes(data.get(addr, 0xFF) for addr in range(start, start + length))


def read_u8(data: bytes, offset: int) -> int:
    return data[offset]


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_u16_be(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def read_u32_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16) | (data[offset + 3] << 24)


def hexdump(data: bytes, base_addr: int = 0, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{base_addr + i:04X}: {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def is_sentinel(data: bytes, offset: int) -> bool:
    """Check if offset contains 0x18A7 sentinel."""
    if offset + 1 < len(data):
        return data[offset] == 0x18 and data[offset + 1] == 0xA7
    return False


def find_non_sentinel_regions(data: bytes, base_addr: int) -> list:
    """Find regions that are not 0x18A7 sentinel."""
    regions = []
    in_data = False
    start = 0

    for i in range(0, len(data) - 1, 2):
        is_sent = (data[i] == 0x18 and data[i + 1] == 0xA7)
        if not is_sent and not in_data:
            in_data = True
            start = i
        elif is_sent and in_data:
            in_data = False
            if i - start >= 4:  # Only record regions >= 4 bytes
                regions.append((base_addr + start, i - start, data[start:i]))

    if in_data:
        regions.append((base_addr + start, len(data) - start, data[start:]))

    return regions


def analyze_config():
    """Main analysis function."""
    ledjsm_data = parse_s19("ledjsm_dump.s19")

    output = []
    output.append("=" * 78)
    output.append("LEDJSM Configuration Analysis")
    output.append("=" * 78)
    output.append("")
    output.append("Source: LEDJSM firmware dump (Motorola S-Record)")
    output.append("Device ID: 0x6380 (LED Joystick Module)")
    output.append("")

    # ==========================================================================
    # HEADER REGION (0x0000 - 0x00FF)
    # ==========================================================================
    output.append("=" * 78)
    output.append("1. HEADER REGION (0x0000 - 0x00FF)")
    output.append("=" * 78)
    output.append("")

    header = extract_region(ledjsm_data, 0x0000, 0x100)

    output.append("Raw dump:")
    output.append(hexdump(header, 0x0000))
    output.append("")

    # Parse known header fields
    output.append("Parsed fields:")
    output.append(f"  0x0000: Device Type ID     = 0x{read_u16_be(header, 0x00):04X}")
    output.append(f"  0x0002: Reserved           = {header[0x02:0x08].hex().upper()}")
    output.append(f"  0x0008: Device Flags       = 0x{read_u32_le(header, 0x08):08X}")
    output.append(f"  0x000C: Version            = 0x{read_u32_le(header, 0x0C):08X}")
    output.append(f"  0x0010: Reserved           = {header[0x10:0x12].hex().upper()}")
    output.append(f"  0x0012: Config Variant     = 0x{read_u16_be(header, 0x12):04X}")
    output.append(f"  0x0014: Reserved           = {header[0x14:0x16].hex().upper()}")
    output.append(f"  0x0016: Mode Flags         = 0x{read_u16_be(header, 0x16):04X}")
    output.append(f"  0x0018-0x0021: Reserved    = {header[0x18:0x22].hex().upper()}")
    output.append(f"  0x0022: Checksum/CRC       = 0x{read_u16_be(header, 0x22):04X}")
    output.append(f"  0x0030: Max Profiles?      = 0x{header[0x30]:02X} ({header[0x30]})")
    output.append(f"  0x0037: Speed Limit?       = 0x{header[0x37]:02X} ({header[0x37]})")
    output.append(f"  0x00FE: Feature Flags      = 0x{header[0xFE]:02X}")
    output.append("")

    # ==========================================================================
    # KEY/SERIAL REGION (0x0100 - 0x01FF)
    # ==========================================================================
    output.append("=" * 78)
    output.append("2. KEY/SERIAL REGION (0x0100 - 0x01FF)")
    output.append("=" * 78)
    output.append("")

    key_region = extract_region(ledjsm_data, 0x0100, 0x100)
    output.append("Raw dump:")
    output.append(hexdump(key_region, 0x0100))
    output.append("")

    output.append("Parsed fields:")
    output.append(f"  0x0160: Encryption Key     = {key_region[0x60:0x70].hex().upper()}")
    output.append(f"         (LEDJSM has no key - all zeros except 0x016E-0x016F)")
    output.append(f"  0x016E: Unknown            = 0x{read_u16_be(key_region, 0x6E):04X}")
    output.append("")

    # ==========================================================================
    # CONFIGURATION REGION (0x0400 - 0x0FFF)
    # ==========================================================================
    output.append("=" * 78)
    output.append("3. CONFIGURATION REGION (0x0400 - 0x1000)")
    output.append("=" * 78)
    output.append("")

    config = extract_region(ledjsm_data, 0x0400, 0xC00)

    output.append("3.1 Config Header (0x0400 - 0x0410)")
    output.append("-" * 78)
    output.append(hexdump(config[0:0x20], 0x0400))
    output.append("")
    output.append("Parsed fields:")
    output.append(f"  0x0400: Config Type        = 0x{read_u16_be(config, 0x00):04X}")
    output.append(f"  0x0402-0x0409: Reserved    = {config[0x02:0x0A].hex().upper()}")
    output.append(f"  0x040A: Slot Config        = {config[0x0A:0x10].hex().upper()}")
    output.append(f"          (6 bytes, likely 6 slot enable flags)")
    output.append(f"  0x0410: Mode Config        = {config[0x10:0x18].hex().upper()}")
    output.append("")

    # Look for structured data patterns
    output.append("3.2 Speed/Control Settings (0x0430 - 0x0450)")
    output.append("-" * 78)
    output.append(hexdump(config[0x30:0x60], 0x0430))
    output.append("")
    output.append("Parsed fields:")
    output.append(f"  0x0430: Speed Setting      = 0x{config[0x30]:02X} ({config[0x30]}%)")
    output.append(f"  0x0431-0x0437: Mode Params = {config[0x31:0x38].hex().upper()}")
    output.append(f"  0x0438: Control Bytes      = {config[0x38:0x40].hex().upper()}")
    output.append(f"          (0x81 appears to be a common control value)")
    output.append("")

    output.append("3.3 Device Identifier (0x0444)")
    output.append("-" * 78)
    output.append(f"  0x0444: Device ID?         = 0x{read_u16_be(config, 0x44):04X}")
    output.append("")

    output.append("3.4 Limits Configuration (0x04D0 - 0x04E0)")
    output.append("-" * 78)
    output.append(hexdump(config[0xD0:0xE0], 0x04D0))
    output.append("")
    output.append("Parsed fields:")
    output.append(f"  0x04D4: Config Value       = 0x{config[0xD4]:02X} ({config[0xD4]})")
    output.append(f"  0x04D6: Max Value (FFFF)   = 0x{read_u16_be(config, 0xD6):04X}")
    output.append(f"  0x04D8: Max Percent        = 0x{config[0xD8]:02X} ({config[0xD8]}%)")
    output.append("")

    # Find sentinel boundaries
    output.append("3.5 Active Data Regions (non-0x18A7)")
    output.append("-" * 78)
    output.append("")

    regions = find_non_sentinel_regions(config, 0x0400)
    for addr, length, data in regions:
        output.append(f"Region 0x{addr:04X} - 0x{addr+length:04X} ({length} bytes):")
        if length <= 64:
            output.append(hexdump(data, addr))
        else:
            output.append(hexdump(data[:32], addr))
            output.append("  ...")
            output.append(hexdump(data[-32:], addr + length - 32))
        output.append("")

    # ==========================================================================
    # DETAILED CONFIG TABLES
    # ==========================================================================
    output.append("=" * 78)
    output.append("4. DETAILED CONFIGURATION TABLES")
    output.append("=" * 78)
    output.append("")

    # Full config dump with annotations
    output.append("4.1 Full Config Dump (0x0400 - 0x0600)")
    output.append("-" * 78)
    output.append("")

    for offset in range(0, 0x200, 0x10):
        addr = 0x0400 + offset
        chunk = config[offset:offset + 0x10]

        # Annotate known fields
        annotation = ""
        if offset == 0x00:
            annotation = "  <- Config type"
        elif offset == 0x00 and chunk[0:2] == bytes([0x18, 0x02]):
            annotation = "  <- Type 0x1802"
        elif offset == 0x30:
            annotation = f"  <- Speed={chunk[0]}%"
        elif offset == 0x40:
            annotation = "  <- Device params"
        elif all(b in (0x18, 0xA7) for b in chunk):
            annotation = "  <- SENTINEL (uninitialized)"
        elif chunk.count(0xFF) > 12:
            annotation = "  <- Max values"
        elif chunk.count(0x81) > 3:
            annotation = "  <- Control flags (0x81)"

        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        output.append(f"{addr:04X}: {hex_str}  {ascii_str}{annotation}")

    output.append("")

    # ==========================================================================
    # VALUE INTERPRETATION
    # ==========================================================================
    output.append("=" * 78)
    output.append("5. VALUE INTERPRETATION")
    output.append("=" * 78)
    output.append("")

    output.append("5.1 Common Byte Values")
    output.append("-" * 78)
    freq = Counter(config)
    output.append("Most frequent bytes in config region:")
    for byte, count in freq.most_common(15):
        pct = 100 * count / len(config)
        meaning = ""
        if byte == 0x18:
            meaning = "(sentinel high byte)"
        elif byte == 0xA7:
            meaning = "(sentinel low byte)"
        elif byte == 0x00:
            meaning = "(zero/null)"
        elif byte == 0xFF:
            meaning = "(max/unset)"
        elif byte == 0x01:
            meaning = "(enabled/true)"
        elif byte == 0x81:
            meaning = "(control flag)"
        output.append(f"  0x{byte:02X}: {count:5d} ({pct:5.1f}%) {meaning}")
    output.append("")

    output.append("5.2 Sentinel Pattern (0x18A7)")
    output.append("-" * 78)
    sentinel_count = sum(1 for i in range(0, len(config)-1, 2)
                        if config[i] == 0x18 and config[i+1] == 0xA7)
    output.append(f"  Occurrences in config: {sentinel_count}")
    output.append(f"  Meaning: Uninitialized/default configuration slot")
    output.append(f"  Used to mark empty profile slots, unused parameters")
    output.append("")

    output.append("5.3 Control Values")
    output.append("-" * 78)
    output.append("  0x81: Appears frequently in control byte positions")
    output.append("        Likely meaning: 'enabled' or 'active' flag")
    output.append("  0xFF: Maximum value or 'no limit'")
    output.append("  0x00: Disabled or zero")
    output.append("  0x01: Enabled or increment of 1")
    output.append("  0x32 (50): Common speed setting (50%)")
    output.append("  0x64 (100): Maximum percentage")
    output.append("")

    # ==========================================================================
    # EXTENDED CONFIG (0x1000+)
    # ==========================================================================
    output.append("=" * 78)
    output.append("6. EXTENDED CONFIGURATION (0x1000 - 0x4000)")
    output.append("=" * 78)
    output.append("")

    ext_config = extract_region(ledjsm_data, 0x1000, 0x100)
    output.append("Sample (0x1000 - 0x1100):")
    output.append(hexdump(ext_config[:64], 0x1000))
    output.append("")
    output.append("Status: Entirely filled with 0x18A7 sentinel")
    output.append("        This region is reserved but not used in this device")
    output.append("")

    # ==========================================================================
    # XOR TABLE DISCOVERY
    # ==========================================================================
    output.append("=" * 78)
    output.append("7. XOR TABLE / AUTHENTICATION DATA (0x0700)")
    output.append("=" * 78)
    output.append("")

    xor_region = extract_region(ledjsm_data, 0x0700, 0x40)
    output.append("Raw dump:")
    output.append(hexdump(xor_region, 0x0700))
    output.append("")

    output.append("Parsed fields:")
    output.append(f"  0x0704: XOR Table (8 bytes) = {xor_region[0x04:0x0C].hex().upper()}")
    output.append(f"          Matches Table A pattern: DD 12 7B 45 (bytes 4-7)")
    output.append(f"  0x0708: Serial Number       = {xor_region[0x08:0x10].hex().upper()}")
    output.append(f"          = 08901C8A (standalone JSM serial)")
    output.append("")

    # ==========================================================================
    # STRUCTURE SUMMARY
    # ==========================================================================
    output.append("=" * 78)
    output.append("8. CONFIGURATION STRUCTURE SUMMARY")
    output.append("=" * 78)
    output.append("")
    output.append("""
Memory Map:
-----------
0x0000 - 0x00FF   Device Header (256 bytes)
                  - Device ID, version, flags, checksum

0x0100 - 0x015F   Reserved (96 bytes, all zeros)

0x0160 - 0x016F   Encryption/Auth Key (16 bytes)
                  - LEDJSM: Empty (zeros + 0xE693)
                  - BTMouse: Full 128-bit key

0x0170 - 0x01FF   Reserved (144 bytes)

0x0200 - 0x03FF   Reserved (512 bytes, all zeros)

0x0400 - 0x04DF   Active Configuration (~224 bytes)
                  - Config type and flags
                  - Slot configuration (6 slots)
                  - Mode configuration
                  - Speed settings
                  - Control parameters
                  - Device identifiers

0x04E0 - 0x0FFF   Profile/Extended Config (~2848 bytes)
                  - Mostly 0x18A7 sentinel
                  - Some scattered config values

0x1000 - 0x3FFF   Extended Config (12KB)
                  - All 0x18A7 sentinel
                  - Reserved for additional profiles

0x4000 - 0xFFFF   Firmware Code
                  - HCS08 machine code
                  - Interrupt vectors at 0xFF80-0xFFFF

Key Values:
-----------
0x18A7  = Uninitialized slot marker (sentinel)
0x81    = Enabled/active control flag
0xFF    = Maximum or unlimited
0x00    = Disabled or zero
0x32    = 50% (common speed default)
0x64    = 100% (maximum percentage)

Configuration Fields:
--------------------
0x0400: Config type (0x1802 for LEDJSM)
0x040A: Slot enable flags (6 bytes)
0x0410: Mode configuration (8 bytes)
0x0430: Speed setting (percentage)
0x0438: Control byte array (0x81 flags)
0x0444: Device identifier
0x04D4: Config value
0x04D6: Max value (0xFFFF)
0x04D8: Max percentage (100)
""")

    return '\n'.join(output)


def main():
    analysis = analyze_config()

    # Print to console
    print(analysis)

    # Write to file
    output_file = "docs/LEDJSM_CONFIG_ANALYSIS.txt"
    with open(output_file, 'w') as f:
        f.write(analysis)

    print(f"\n\nAnalysis saved to: {output_file}")


if __name__ == "__main__":
    main()
