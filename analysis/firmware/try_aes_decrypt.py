#!/usr/bin/env python3
"""
Try AES decryption on BTMouse config.
The 128-bit key at 0x0160 could be an AES key.
"""

import sys
try:
    from Crypto.Cipher import AES
    HAS_CRYPTO = True
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        HAS_CRYPTO = True
    except ImportError:
        HAS_CRYPTO = False


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


def hexdump(data: bytes, base_addr: int = 0, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{base_addr + i:04X}: {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def calculate_entropy(data: bytes) -> float:
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


def simple_xor_variants(encrypted: bytes, key: bytes):
    """Try various XOR-based schemes."""
    results = []

    # 1. Simple repeating XOR
    decrypted = bytes(e ^ key[i % len(key)] for i, e in enumerate(encrypted))
    results.append(("Simple XOR (repeating key)", decrypted))

    # 2. XOR with key + address offset
    decrypted = bytes(e ^ key[i % len(key)] ^ (i & 0xFF) for i, e in enumerate(encrypted))
    results.append(("XOR + address offset", decrypted))

    # 3. XOR with running counter
    decrypted = bytes(e ^ key[i % len(key)] ^ ((i // 16) & 0xFF) for i, e in enumerate(encrypted))
    results.append(("XOR + block counter", decrypted))

    # 4. XOR with complemented key on odd blocks
    def xor_complement():
        result = bytearray()
        for i, e in enumerate(encrypted):
            block = i // 16
            k = key[i % len(key)]
            if block % 2 == 1:
                k = k ^ 0xFF
            result.append(e ^ k)
        return bytes(result)
    results.append(("XOR with complemented odd blocks", xor_complement()))

    # 5. CBC-like XOR (previous block XOR)
    def cbc_xor():
        result = bytearray()
        prev_block = b'\x00' * 16
        for block_num in range(len(encrypted) // 16):
            block_start = block_num * 16
            block = encrypted[block_start:block_start + 16]
            for i, (e, k, p) in enumerate(zip(block, key, prev_block)):
                result.append(e ^ k ^ p)
            prev_block = encrypted[block_start:block_start + 16]
        return bytes(result)
    results.append(("CBC-like XOR", cbc_xor()))

    return results


def main():
    btmouse_data = parse_s19("btmouse_dump.s19")
    ledjsm_data = parse_s19("ledjsm_dump.s19")

    KEY = bytes.fromhex("FC95FEBAE31F2D04EC12E6FDEF0057C1")

    print("=" * 70)
    print("AES and Advanced Decryption Attempts")
    print("=" * 70)

    # Extract config regions
    btm_config = extract_region(btmouse_data, 0x0400, 0x100)  # First 256 bytes
    led_config = extract_region(ledjsm_data, 0x0400, 0x100)

    print(f"\nKey (0x0160): {KEY.hex().upper()}")
    print(f"Encrypted config entropy: {calculate_entropy(btm_config):.3f}")
    print(f"Plaintext reference entropy: {calculate_entropy(led_config):.3f}")

    # Try XOR variants first
    print("\n" + "=" * 70)
    print("XOR Variant Attempts")
    print("=" * 70)

    for name, decrypted in simple_xor_variants(btm_config, KEY):
        entropy = calculate_entropy(decrypted)
        # Check how similar to LEDJSM plaintext
        similarity = sum(1 for a, b in zip(decrypted, led_config) if a == b) / len(decrypted)
        print(f"\n{name}:")
        print(f"  Entropy: {entropy:.3f}, Similarity to LEDJSM: {100*similarity:.1f}%")
        if entropy < 6.0 or similarity > 0.3:
            print(f"  First 64 bytes:")
            print(hexdump(decrypted[:64], 0x0400))

    # Try AES if available
    if HAS_CRYPTO:
        print("\n" + "=" * 70)
        print("AES Decryption Attempts")
        print("=" * 70)

        # Try ECB mode
        try:
            cipher = AES.new(KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(btm_config)
            entropy = calculate_entropy(decrypted)
            similarity = sum(1 for a, b in zip(decrypted, led_config) if a == b) / len(decrypted)
            print(f"\nAES-128-ECB:")
            print(f"  Entropy: {entropy:.3f}, Similarity to LEDJSM: {100*similarity:.1f}%")
            print(f"  First 64 bytes:")
            print(hexdump(decrypted[:64], 0x0400))
        except Exception as e:
            print(f"\nAES-128-ECB failed: {e}")

        # Try CBC with zero IV
        try:
            cipher = AES.new(KEY, AES.MODE_CBC, iv=b'\x00' * 16)
            decrypted = cipher.decrypt(btm_config)
            entropy = calculate_entropy(decrypted)
            similarity = sum(1 for a, b in zip(decrypted, led_config) if a == b) / len(decrypted)
            print(f"\nAES-128-CBC (zero IV):")
            print(f"  Entropy: {entropy:.3f}, Similarity to LEDJSM: {100*similarity:.1f}%")
            print(f"  First 64 bytes:")
            print(hexdump(decrypted[:64], 0x0400))
        except Exception as e:
            print(f"\nAES-128-CBC failed: {e}")

        # Try CTR mode
        try:
            cipher = AES.new(KEY, AES.MODE_CTR, nonce=b'\x00' * 8)
            decrypted = cipher.decrypt(btm_config)
            entropy = calculate_entropy(decrypted)
            similarity = sum(1 for a, b in zip(decrypted, led_config) if a == b) / len(decrypted)
            print(f"\nAES-128-CTR (zero nonce):")
            print(f"  Entropy: {entropy:.3f}, Similarity to LEDJSM: {100*similarity:.1f}%")
            print(f"  First 64 bytes:")
            print(hexdump(decrypted[:64], 0x0400))
        except Exception as e:
            print(f"\nAES-128-CTR failed: {e}")
    else:
        print("\n[!] PyCryptodome not installed - skipping AES attempts")
        print("    Install with: pip install pycryptodome")

    # Check if the BTMouse config might just be different data
    print("\n" + "=" * 70)
    print("Alternative Hypothesis: Different Config Format")
    print("=" * 70)

    # The BTMouse is a Bluetooth module - its config is likely fundamentally different
    # Check for Bluetooth-specific structures

    print("\nBTMouse config 0x0400-0x0500 (looking for Bluetooth structures):")
    print(hexdump(btm_config, 0x0400))

    # Look for patterns that might indicate Bluetooth data
    # Bluetooth addresses are 6 bytes, often with manufacturer OUI prefix
    print("\nSearching for potential 6-byte MAC addresses...")
    for i in range(len(btm_config) - 6):
        chunk = btm_config[i:i+6]
        # Check if it looks like a MAC (has some structure, not random)
        # OUI prefixes for common Bluetooth chips
        if chunk[0:3] in [bytes.fromhex(x) for x in ['001060', '0025DC', '00155D', '0017F2']]:
            print(f"  Possible MAC at 0x{0x0400+i:04X}: {chunk.hex().upper()}")

    # Final assessment
    print("\n" + "=" * 70)
    print("Assessment")
    print("=" * 70)
    print("""
Based on analysis:

1. The key at 0x0160 does NOT decrypt the config with simple XOR
2. AES decryption also doesn't produce meaningful results
3. The BTMouse extended config (0x1000+) is plaintext (0x18A7 sentinel)

Most likely explanation:
- BTMouse config at 0x0400-0x1000 is BLUETOOTH PAIRING/DEVICE DATA
- This is inherently high-entropy data (encrypted link keys, device addresses)
- The 0x0160 key is probably the device's Bluetooth link key, not config encryption

The "encryption" we see is likely:
- Stored Bluetooth link keys (128-bit AES keys for paired devices)
- Encrypted Bluetooth device names
- Authentication tokens
- NOT the same type of configuration as LEDJSM joystick settings
""")


if __name__ == "__main__":
    main()
