#!/usr/bin/env python3
"""
Deep analysis of BTMouse firmware - check for stream cipher, compression, or inherent structure.
"""

import sys
from collections import Counter


def parse_s19(filename: str) -> dict[int, int]:
    """Parse Motorola S-record file to address->byte mapping."""
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
    """Extract contiguous region from parsed data."""
    return bytes(data.get(addr, 0xFF) for addr in range(start, start + length))


def hexdump(data: bytes, base_addr: int = 0, width: int = 16) -> str:
    """Format data as hex dump."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{base_addr + i:04X}: {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def main():
    btmouse_data = parse_s19("btmouse_dump.s19")
    ledjsm_data = parse_s19("ledjsm_dump.s19")

    KEY = bytes.fromhex("FC95FEBAE31F2D04EC12E6FDEF0057C1")

    print("=" * 70)
    print("BTMouse Deep Analysis")
    print("=" * 70)

    # Look at BTMouse config region structure
    print("\n1. BTMouse Config Region (0x0400-0x0800)")
    print("-" * 70)

    btm_config = extract_region(btmouse_data, 0x0400, 0x400)

    # Byte frequency analysis
    freq = Counter(btm_config)
    print("\nTop 10 most common bytes:")
    for byte, count in freq.most_common(10):
        pct = 100 * count / len(btm_config)
        print(f"  0x{byte:02X}: {count:4d} ({pct:5.2f}%)")

    # Check for runs/patterns
    print("\nLongest runs of same byte:")
    max_runs = []
    current_byte = btm_config[0]
    current_run = 1
    for i in range(1, len(btm_config)):
        if btm_config[i] == current_byte:
            current_run += 1
        else:
            if current_run >= 4:
                max_runs.append((current_run, current_byte, i - current_run))
            current_byte = btm_config[i]
            current_run = 1
    max_runs.sort(reverse=True)
    for run_len, byte, offset in max_runs[:10]:
        print(f"  {run_len} x 0x{byte:02X} at offset 0x{0x0400 + offset:04X}")

    # Check for structure around sentinel-like patterns
    print("\n2. Looking for Structure Patterns")
    print("-" * 70)

    # Check every 16 bytes for patterns
    print("\n16-byte block first bytes (looking for structure):")
    for i in range(0, min(512, len(btm_config)), 16):
        block = btm_config[i:i+16]
        print(f"  0x{0x0400+i:04X}: {block[0]:02X} {block[1]:02X} {block[2]:02X} {block[3]:02X}  ...  {block[-4]:02X} {block[-3]:02X} {block[-2]:02X} {block[-1]:02X}")

    # Compare with LEDJSM to find regions that ARE similar
    print("\n3. Finding Similar Regions Between BTMouse and LEDJSM")
    print("-" * 70)

    # Check various regions for similarity
    regions = [
        (0x0000, 0x0100, "Header"),
        (0x0100, 0x0060, "Pre-key"),
        (0x0160, 0x0010, "Key/XOR"),
        (0x0170, 0x0090, "Post-key to config"),
        (0x0200, 0x0200, "0x0200-0x0400"),
        (0x0400, 0x0400, "Config 0x0400"),
        (0x0800, 0x0400, "Config 0x0800"),
        (0x0C00, 0x0400, "Config 0x0C00"),
        (0x1000, 0x1000, "Extended config"),
        (0x4000, 0x0100, "Code start"),
        (0x5000, 0x0100, "Code middle"),
    ]

    print(f"\n{'Region':<25} {'Address':<15} {'Match %':<10} {'Notes'}")
    print("-" * 70)

    for start, length, name in regions:
        btm = extract_region(btmouse_data, start, length)
        led = extract_region(ledjsm_data, start, length)
        matches = sum(1 for a, b in zip(btm, led) if a == b)
        pct = 100 * matches / length
        notes = ""
        if pct > 90:
            notes = "IDENTICAL"
        elif pct > 50:
            notes = "Similar"
        elif pct < 10:
            notes = "Different"
        print(f"{name:<25} 0x{start:04X}-0x{start+length:04X}  {pct:6.1f}%    {notes}")

    # Examine regions that are identical
    print("\n4. Examining Identical/Similar Regions")
    print("-" * 70)

    # Check 0x0200-0x0400 region
    print("\nRegion 0x0200-0x0400 (pre-config):")
    btm_200 = extract_region(btmouse_data, 0x0200, 0x80)
    led_200 = extract_region(ledjsm_data, 0x0200, 0x80)
    print("BTMouse:")
    print(hexdump(btm_200[:64], 0x0200))
    print("\nLEDJSM:")
    print(hexdump(led_200[:64], 0x0200))

    # Check extended config region
    print("\n5. Extended Config Region (0x1000+)")
    print("-" * 70)

    btm_1000 = extract_region(btmouse_data, 0x1000, 0x100)
    led_1000 = extract_region(ledjsm_data, 0x1000, 0x100)

    # LEDJSM has 0x18A7 sentinel here
    print("\nLEDJSM 0x1000 (should be 0x18A7 sentinel):")
    print(hexdump(led_1000[:64], 0x1000))

    print("\nBTMouse 0x1000:")
    print(hexdump(btm_1000[:64], 0x1000))

    # Check for 0x18A7 equivalent in BTMouse
    print("\n6. BTMouse Sentinel Analysis")
    print("-" * 70)

    # If BTMouse uses XOR with key, 0x18A7 would become something else
    # encrypted_sentinel = 0x18A7 XOR key[0:2]
    sentinel_plain = bytes([0x18, 0xA7])
    sentinel_encrypted = bytes(a ^ b for a, b in zip(sentinel_plain, KEY[:2]))
    print(f"If 0x18A7 encrypted with key: {sentinel_encrypted.hex().upper()}")

    # Search for this pattern in BTMouse
    search_pattern = sentinel_encrypted
    btm_full = extract_region(btmouse_data, 0x0400, 0x4000)
    occurrences = btm_full.count(search_pattern)
    print(f"Occurrences of encrypted sentinel in BTMouse config: {occurrences}")

    # Also search for common patterns that could be sentinel
    print("\nMost common 2-byte patterns in BTMouse config (0x0400-0x1000):")
    btm_config_full = extract_region(btmouse_data, 0x0400, 0xC00)
    pairs = Counter(btm_config_full[i:i+2] for i in range(len(btm_config_full)-1))
    for pattern, count in pairs.most_common(10):
        print(f"  {pattern.hex().upper()}: {count}")

    # Final check: is this Bluetooth-specific data?
    print("\n7. Bluetooth-Specific Analysis")
    print("-" * 70)

    # Check for MAC address patterns (6 bytes, often starting with known OUI)
    # Or Bluetooth Class of Device patterns
    print("\nSearching for potential Bluetooth MAC addresses or pairing data...")

    # MAC addresses often have patterns like XX:XX:XX:XX:XX:XX
    # Check if config looks like stored Bluetooth device info
    print("\nBTMouse 0x0400-0x0500 with potential field boundaries:")
    print(hexdump(btm_config[:256], 0x0400))

    # Check 0x0160 key for Bluetooth significance
    print("\n8. Key at 0x0160 Analysis")
    print("-" * 70)
    print(f"Key: {KEY.hex().upper()}")
    print(f"As 4 32-bit words (LE): ", end="")
    for i in range(0, 16, 4):
        word = int.from_bytes(KEY[i:i+4], 'little')
        print(f"0x{word:08X} ", end="")
    print()

    # This could be a Bluetooth link key (128-bit)
    print("\nPossible interpretations:")
    print("  - Bluetooth Link Key (128-bit AES key for pairing)")
    print("  - Custom authentication key for R-Net")
    print("  - XOR table for serial number (8 bytes doubled)")
    print("  - Random/unique device identifier")

    # Check if first 8 bytes repeat as second 8
    if KEY[:8] == KEY[8:]:
        print("\n  -> Key has repeating 8-byte pattern!")
    else:
        print("\n  -> Key does NOT repeat (likely full 128-bit key)")


if __name__ == "__main__":
    main()
