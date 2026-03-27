#!/usr/bin/env python3
"""
Analyze BTMouse encryption scheme by comparing with LEDJSM plaintext.
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
    result = bytearray()
    for addr in range(start, start + length):
        result.append(data.get(addr, 0xFF))
    return bytes(result)


def main():
    btmouse_data = parse_s19("btmouse_dump.s19")
    ledjsm_data = parse_s19("ledjsm_dump.s19")

    KEY = bytes.fromhex("FC95FEBAE31F2D04EC12E6FDEF0057C1")

    print("=" * 70)
    print("Encryption Analysis: Block-by-block XOR key derivation")
    print("=" * 70)

    # Extract and compare multiple 16-byte blocks
    print("\nDerived XOR key for each 16-byte block (encrypted XOR plaintext):\n")
    print("Block  Address    Derived Key (XOR of encrypted ^ plaintext)")
    print("-" * 70)

    config_start = 0x0400
    block_size = 16

    derived_keys = []
    for block_num in range(32):  # First 32 blocks (512 bytes)
        addr = config_start + block_num * block_size
        btmouse_block = extract_region(btmouse_data, addr, block_size)
        ledjsm_block = extract_region(ledjsm_data, addr, block_size)

        # XOR to find the key used for this block
        derived_key = bytes(a ^ b for a, b in zip(btmouse_block, ledjsm_block))
        derived_keys.append(derived_key)

        print(f"{block_num:4d}   0x{addr:04X}    {derived_key.hex().upper()}")

    # Check if keys have any relationship to the stored key
    print("\n" + "=" * 70)
    print("Key Pattern Analysis")
    print("=" * 70)

    # XOR derived keys with the stored key
    print("\nDerived keys XOR stored key (0x0160):")
    for i, dk in enumerate(derived_keys[:8]):
        xor_result = bytes(a ^ b for a, b in zip(dk, KEY))
        print(f"  Block {i}: {xor_result.hex().upper()}")

    # Check if there's a pattern based on address
    print("\n" + "=" * 70)
    print("Address-based key derivation test")
    print("=" * 70)

    # Maybe key[i] = stored_key[i] XOR (address byte or counter)
    for block_num in range(8):
        addr = config_start + block_num * block_size
        addr_lo = addr & 0xFF
        addr_hi = (addr >> 8) & 0xFF
        block_counter = block_num & 0xFF

        print(f"\nBlock {block_num} at 0x{addr:04X}:")
        print(f"  Derived key: {derived_keys[block_num].hex().upper()}")

        # Test: key XOR address low byte
        test1 = bytes((KEY[i] ^ addr_lo) for i in range(16))
        print(f"  KEY ^ addr_lo(0x{addr_lo:02X}): {test1.hex().upper()}")

        # Test: key XOR block counter
        test2 = bytes((KEY[i] ^ block_counter) for i in range(16))
        print(f"  KEY ^ block(0x{block_counter:02X}):  {test2.hex().upper()}")

    # Check for LFSR/stream cipher pattern
    print("\n" + "=" * 70)
    print("Stream Cipher Analysis (byte-by-byte)")
    print("=" * 70)

    # Get a longer stream of keystream bytes
    keystream_len = 256
    btmouse_config = extract_region(btmouse_data, config_start, keystream_len)
    ledjsm_config = extract_region(ledjsm_data, config_start, keystream_len)
    keystream = bytes(a ^ b for a, b in zip(btmouse_config, ledjsm_config))

    print(f"\nFull keystream (first {keystream_len} bytes):")
    for i in range(0, keystream_len, 16):
        print(f"  {config_start + i:04X}: {keystream[i:i+16].hex().upper()}")

    # Check for repeating patterns
    print("\nChecking for repeating keystream patterns...")
    for period in [16, 32, 64, 128, 256]:
        if keystream_len >= period * 2:
            matches = sum(1 for i in range(period) if keystream[i] == keystream[i + period])
            print(f"  Period {period:3d}: {matches}/{period} bytes match ({100*matches/period:.1f}%)")

    # Check if configs might actually be DIFFERENT data (not encrypted same data)
    print("\n" + "=" * 70)
    print("Configuration Difference Analysis")
    print("=" * 70)

    print("\nAre BTMouse and LEDJSM configs fundamentally different?")
    print("(Comparing header region which should be similar if same format)\n")

    # Compare headers
    for region_name, start, length in [
        ("Device Header", 0x0000, 32),
        ("Key Region", 0x0160, 32),
        ("Config Start", 0x0400, 32),
    ]:
        btm_region = extract_region(btmouse_data, start, length)
        led_region = extract_region(ledjsm_data, start, length)
        diff_count = sum(1 for a, b in zip(btm_region, led_region) if a != b)
        print(f"{region_name} (0x{start:04X}):")
        print(f"  BTMouse: {btm_region[:16].hex().upper()}...")
        print(f"  LEDJSM:  {led_region[:16].hex().upper()}...")
        print(f"  Differences: {diff_count}/{length} bytes ({100*diff_count/length:.1f}%)\n")

    # Maybe BTMouse has a DIFFERENT config, not an encrypted version of the same
    print("=" * 70)
    print("Hypothesis: BTMouse config is NOT encrypted LEDJSM config")
    print("=" * 70)
    print("""
The high entropy in BTMouse config region could mean:
1. Encrypted with complex cipher (not simple XOR)
2. Compressed data
3. Simply DIFFERENT configuration data with high variation

Evidence for "different config" hypothesis:
- Device IDs are different (0x0000 vs 0x6380)
- The 0x0160 region shows completely different patterns
- No obvious XOR key produces meaningful decryption

The "encryption key" at 0x0160 might be:
- Authentication key for R-Net bus (not config encryption)
- Bluetooth pairing key (BTMouse is Bluetooth module)
- XOR table for serial number exchange
""")

    # Compare code region (should be identical if same firmware base)
    print("=" * 70)
    print("Code Region Comparison (0x4000-0x4100)")
    print("=" * 70)

    code_btm = extract_region(btmouse_data, 0x4000, 256)
    code_led = extract_region(ledjsm_data, 0x4000, 256)
    code_diff = sum(1 for a, b in zip(code_btm, code_led) if a != b)

    print(f"\nCode region differences: {code_diff}/256 bytes ({100*code_diff/256:.1f}%)")
    if code_diff == 0:
        print("Code regions are IDENTICAL - same firmware, different config data")
    else:
        print("Code regions differ - different firmware versions or device types")

    # Show first difference in code
    for i, (a, b) in enumerate(zip(code_btm, code_led)):
        if a != b:
            print(f"\nFirst code difference at 0x{0x4000+i:04X}: BTM={a:02X} LED={b:02X}")
            break


if __name__ == "__main__":
    main()
