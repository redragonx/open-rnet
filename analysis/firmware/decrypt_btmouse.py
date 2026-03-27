#!/usr/bin/env python3
"""
Decrypt BTMouse configuration using XOR key from firmware.

Key found at offset 0x0160 in BTMouse firmware dump.
"""

import sys
from pathlib import Path


def parse_s19(filename: str) -> dict[int, int]:
    """Parse Motorola S-record file to address->byte mapping."""
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('S1'):
                # S1: 16-bit address
                count = int(line[2:4], 16)
                addr = int(line[4:8], 16)
                # Data bytes: count - 3 (2 addr + 1 checksum)
                for i in range(count - 3):
                    byte_offset = 8 + i * 2
                    data[addr + i] = int(line[byte_offset:byte_offset + 2], 16)

            elif line.startswith('S2'):
                # S2: 24-bit address
                count = int(line[2:4], 16)
                addr = int(line[4:10], 16)
                # Data bytes: count - 4 (3 addr + 1 checksum)
                for i in range(count - 4):
                    byte_offset = 10 + i * 2
                    data[addr + i] = int(line[byte_offset:byte_offset + 2], 16)

    return data


def extract_region(data: dict[int, int], start: int, length: int) -> bytes:
    """Extract contiguous region from parsed data."""
    result = bytearray()
    for addr in range(start, start + length):
        result.append(data.get(addr, 0xFF))
    return bytes(result)


def xor_decrypt(data: bytes, key: bytes) -> bytes:
    """XOR decrypt data with repeating key."""
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])
    return bytes(result)


def hexdump(data: bytes, base_addr: int = 0, width: int = 16) -> str:
    """Format data as hex dump."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{base_addr + i:04X}: {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data."""
    import math
    if not data:
        return 0.0
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1
    entropy = 0.0
    for count in freq.values():
        p = count / len(data)
        entropy -= p * math.log2(p)
    return entropy


def main():
    btmouse_file = "btmouse_dump.s19"
    ledjsm_file = "ledjsm_dump.s19"

    # BTMouse encryption key at 0x0160
    KEY = bytes.fromhex("FC95FEBAE31F2D04EC12E6FDEF0057C1")

    print("=" * 60)
    print("BTMouse Configuration Decryption")
    print("=" * 60)
    print(f"\nKey (0x0160): {KEY.hex().upper()}")
    print(f"Key length: {len(KEY)} bytes")

    # Parse both files
    print(f"\nParsing {btmouse_file}...")
    btmouse_data = parse_s19(btmouse_file)
    print(f"  Loaded {len(btmouse_data)} bytes")

    print(f"\nParsing {ledjsm_file}...")
    ledjsm_data = parse_s19(ledjsm_file)
    print(f"  Loaded {len(ledjsm_data)} bytes")

    # Extract config regions
    config_start = 0x0400
    config_length = 0x0C00  # 3KB config region

    btmouse_config = extract_region(btmouse_data, config_start, config_length)
    ledjsm_config = extract_region(ledjsm_data, config_start, config_length)

    print(f"\n{'=' * 60}")
    print("Entropy Analysis (before decryption)")
    print("=" * 60)
    print(f"BTMouse config entropy: {calculate_entropy(btmouse_config):.3f} bits/byte")
    print(f"LEDJSM config entropy:  {calculate_entropy(ledjsm_config):.3f} bits/byte")
    print("(High entropy = encrypted/random, Low entropy = structured/plaintext)")

    # Decrypt BTMouse config
    decrypted_config = xor_decrypt(btmouse_config, KEY)

    print(f"\n{'=' * 60}")
    print("Entropy Analysis (after decryption)")
    print("=" * 60)
    print(f"Decrypted BTMouse entropy: {calculate_entropy(decrypted_config):.3f} bits/byte")

    # Compare first 256 bytes
    print(f"\n{'=' * 60}")
    print("Comparison: First 256 bytes of config region (0x0400)")
    print("=" * 60)

    print("\n--- LEDJSM (plaintext reference) ---")
    print(hexdump(ledjsm_config[:256], config_start))

    print("\n--- BTMouse (encrypted) ---")
    print(hexdump(btmouse_config[:256], config_start))

    print("\n--- BTMouse (decrypted with key) ---")
    print(hexdump(decrypted_config[:256], config_start))

    # Check if decryption produced similar structure
    print(f"\n{'=' * 60}")
    print("Structure Analysis")
    print("=" * 60)

    # Look for common patterns
    sentinel = bytes([0x18, 0xA7])  # LEDJSM sentinel
    sentinel_count_ledjsm = ledjsm_config.count(sentinel)
    sentinel_count_decrypted = decrypted_config.count(sentinel)

    print(f"0x18A7 sentinel occurrences:")
    print(f"  LEDJSM:    {sentinel_count_ledjsm}")
    print(f"  Decrypted: {sentinel_count_decrypted}")

    # Check for ASCII strings
    def find_ascii_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
        strings = []
        current = ""
        start = 0
        for i, b in enumerate(data):
            if 32 <= b < 127:
                if not current:
                    start = i
                current += chr(b)
            else:
                if len(current) >= min_len:
                    strings.append((start, current))
                current = ""
        if len(current) >= min_len:
            strings.append((start, current))
        return strings

    print(f"\nASCII strings found in decrypted config:")
    for offset, string in find_ascii_strings(decrypted_config, 4)[:20]:
        print(f"  0x{config_start + offset:04X}: \"{string}\"")

    # Try alternative key interpretations
    print(f"\n{'=' * 60}")
    print("Alternative Decryption Attempts")
    print("=" * 60)

    # Try reversing key
    key_reversed = KEY[::-1]
    decrypted_rev = xor_decrypt(btmouse_config, key_reversed)
    print(f"\nKey reversed:")
    print(f"  Entropy: {calculate_entropy(decrypted_rev):.3f}")

    # Try key from different offset (the 2-byte value in LEDJSM at 0x016E)
    ledjsm_key_bytes = extract_region(ledjsm_data, 0x0160, 16)
    print(f"\nLEDJSM bytes at 0x0160: {ledjsm_key_bytes.hex().upper()}")

    # XOR BTMouse key with LEDJSM key location to see pattern
    xor_keys = bytes(a ^ b for a, b in zip(KEY, ledjsm_key_bytes))
    print(f"BTMouse key XOR LEDJSM 0x0160: {xor_keys.hex().upper()}")

    # Try using the XOR of encrypted and plaintext config as key discovery
    print(f"\n{'=' * 60}")
    print("Key Discovery via Known Plaintext")
    print("=" * 60)

    # XOR first 16 bytes of encrypted with plaintext to reveal key
    derived_key = bytes(a ^ b for a, b in zip(btmouse_config[:16], ledjsm_config[:16]))
    print(f"Derived key (encrypted XOR plaintext):")
    print(f"  {derived_key.hex().upper()}")

    # Check if this repeats
    derived_key_2 = bytes(a ^ b for a, b in zip(btmouse_config[16:32], ledjsm_config[16:32]))
    print(f"  {derived_key_2.hex().upper()} (bytes 16-31)")

    # Use derived key to decrypt
    decrypted_derived = xor_decrypt(btmouse_config, derived_key)
    print(f"\nDecrypted with derived key:")
    print(f"  Entropy: {calculate_entropy(decrypted_derived):.3f}")
    print(hexdump(decrypted_derived[:128], config_start))

    # Save decrypted data
    output_file = "btmouse_config_decrypted.bin"
    with open(output_file, 'wb') as f:
        f.write(decrypted_derived)
    print(f"\nSaved decrypted config to: {output_file}")

    # Also save with original key
    output_file2 = "btmouse_config_decrypted_origkey.bin"
    with open(output_file2, 'wb') as f:
        f.write(decrypted_config)
    print(f"Saved decrypted config (original key) to: {output_file2}")


if __name__ == "__main__":
    main()
