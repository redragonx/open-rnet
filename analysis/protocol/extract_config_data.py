#!/usr/bin/env python3
"""
Extract configuration transfer data from R-Net pcap files.

The config transfer protocol uses extended frames in the 0x1E3X-0x1E8X range:
- 0x1E3C0001-3: Transfer header (3 segments with CRC)
- 0x1E4E0001-N: Data blocks with sequence numbers
- 0x1E4F0001-N: Data continuation
- 0x1E3F0002: Acknowledgment
- 0x1E80000F: Transfer complete
"""

import sys
import subprocess
import struct
import os
from collections import defaultdict


def extract_can_frames(pcap_file: str) -> list:
    """Extract CAN frames from pcap using tshark."""
    cmd = ['tshark', '-r', pcap_file, '-T', 'fields', '-e', 'can.id', '-e', 'data']
    result = subprocess.run(cmd, capture_output=True, text=True)

    frames = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            try:
                frame_id = int(parts[0])
                data = bytes.fromhex(parts[1]) if parts[1] else b''
                frames.append((frame_id, data))
            except (ValueError, IndexError):
                pass
    return frames


def parse_config_transfer(frames: list) -> dict:
    """Parse configuration transfer frames and extract data blocks."""
    transfers = defaultdict(lambda: {'header': [], 'data': [], 'complete': False})
    current_transfer = 0

    for frame_id, data in frames:
        # Convert to hex for easier matching
        fid_hex = frame_id

        # Header frames: 0x1E3C0001-3
        if 0x1E3C0000 <= fid_hex <= 0x1E3CFFFF:
            seq = fid_hex & 0xF
            transfers[current_transfer]['header'].append((seq, data))

        # Data frames: 0x1E4E0001-N
        elif 0x1E4E0000 <= fid_hex <= 0x1E4EFFFF:
            seq = fid_hex & 0xFFFF
            transfers[current_transfer]['data'].append((seq, data))

        # Continuation: 0x1E4F0001-N
        elif 0x1E4F0000 <= fid_hex <= 0x1E4FFFFF:
            seq = fid_hex & 0xFFFF
            transfers[current_transfer]['data'].append((seq, data))

        # ACK: 0x1E3F0002
        elif 0x1E3F0000 <= fid_hex <= 0x1E3FFFFF:
            pass  # Acknowledgment

        # Complete: 0x1E80000F
        elif fid_hex == 0x1E80000F:
            transfers[current_transfer]['complete'] = True
            current_transfer += 1

    return dict(transfers)


def extract_data_payload(transfers: dict) -> bytes:
    """Extract raw data payload from transfers."""
    all_data = b''

    for tid, transfer in sorted(transfers.items()):
        # Sort data blocks by sequence
        sorted_data = sorted(transfer['data'], key=lambda x: x[0])
        for seq, data in sorted_data:
            # Skip the first byte (sequence number) if present
            if len(data) > 1:
                all_data += data[1:]  # Skip sequence byte

    return all_data


def analyze_for_images(data: bytes) -> list:
    """Look for image signatures and patterns in data."""
    findings = []

    # Check for common image signatures
    signatures = [
        (b'BM', 'BMP'),
        (b'\x89PNG', 'PNG'),
        (b'\xff\xd8\xff', 'JPEG'),
        (b'GIF8', 'GIF'),
        (b'\x00\x00\x01\x00', 'ICO'),
    ]

    for sig, fmt in signatures:
        idx = data.find(sig)
        if idx != -1:
            findings.append(f"Found {fmt} signature at offset {idx}")

    # Look for monochrome bitmap patterns (repeating bit patterns)
    for width in [8, 16, 32, 64, 128]:
        for offset in range(0, min(len(data), 1000), width):
            chunk = data[offset:offset + width * 8]
            if len(chunk) >= width * 4:
                # Check for row-like patterns
                rows = [chunk[i:i+width] for i in range(0, len(chunk), width)]
                if len(rows) >= 4:
                    unique_rows = len(set(rows))
                    if unique_rows < len(rows) // 2:
                        findings.append(f"Possible bitmap pattern at offset {offset}, width {width}")
                        break

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_config_data.py <pcap_file> [output_file]")
        print("\nLooks for configuration transfer data in R-Net pcap files")
        print("and extracts any bitmap or image data found.")
        sys.exit(1)

    pcap_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(pcap_file):
        print(f"Error: File not found: {pcap_file}")
        sys.exit(1)

    print(f"Extracting CAN frames from: {pcap_file}")
    frames = extract_can_frames(pcap_file)
    print(f"Total frames: {len(frames)}")

    # Filter for config transfer frames
    config_frames = [(fid, data) for fid, data in frames
                     if 0x1E000000 <= fid <= 0x1EFFFFFF]
    print(f"Config transfer frames: {len(config_frames)}")

    if not config_frames:
        print("No configuration transfer frames found.")
        return

    # Parse transfers
    transfers = parse_config_transfer(config_frames)
    print(f"Transfer sessions: {len(transfers)}")

    for tid, transfer in sorted(transfers.items()):
        print(f"\n  Transfer {tid}:")
        print(f"    Header blocks: {len(transfer['header'])}")
        print(f"    Data blocks: {len(transfer['data'])}")
        print(f"    Complete: {transfer['complete']}")

    # Extract payload
    payload = extract_data_payload(transfers)
    print(f"\nTotal payload size: {len(payload)} bytes")

    # Analyze for images
    print("\nAnalyzing for image data...")
    findings = analyze_for_images(payload)
    if findings:
        for f in findings:
            print(f"  {f}")
    else:
        print("  No standard image formats detected")

    # Save payload if output file specified
    if output_file:
        with open(output_file, 'wb') as f:
            f.write(payload)
        print(f"\nPayload saved to: {output_file}")

        # Also show file type
        result = subprocess.run(['file', output_file], capture_output=True, text=True)
        print(f"File type: {result.stdout.strip()}")

    # Show hex dump of first 256 bytes
    print("\nFirst 256 bytes of payload:")
    for i in range(0, min(256, len(payload)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in payload[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in payload[i:i+16])
        print(f"  {i:04x}: {hex_part:<48} {ascii_part}")


if __name__ == '__main__':
    main()
