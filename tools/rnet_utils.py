#!/usr/bin/env python3
"""
R-Net Protocol Utilities
========================
Tools for analyzing and decoding the R-Net CAN bus protocol used in power wheelchairs.

Based on DEFCON24 research by Stephen Chavez & Specter.

Features:
- Serial number XOR key derivation
- Frame decoding and analysis
- Capture file parsing
- Protocol message dissection
"""

import struct
import sys
import argparse
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum, auto


# ============================================================================
# Known XOR Tables for Serial Number Authentication
# ============================================================================

XOR_TABLES = {
    "standalone_jsm": {
        "description": "Standalone JSM Network (serial 08901c8a)",
        "table": [0x00, 0x21, 0x02, 0xCC, 0xDD, 0x12, 0x7B, 0x45],
        "example_serial": [0x08, 0x90, 0x1C, 0x8A, 0x00, 0x00, 0x00, 0x00],
    },
    "m300": {
        "description": "M300 Multi-Device Network (serial 50c01c8f)",
        "table": [0x83, 0x52, 0xAD, 0x1B, 0xED, 0x06, 0x2C, 0x4E],
        "example_serial": [0x50, 0xC0, 0x1C, 0x8F, 0x00, 0x00, 0x00, 0x00],
    },
    "btm": {
        "description": "Bluetooth Module Network",
        "table": [0x47, 0xA1, 0x62, 0xAD, 0x2E, 0x05, 0xB3, 0xEC],
        "example_serial": None,
    },
}


# ============================================================================
# Device Types and Slots
# ============================================================================

class DeviceType(Enum):
    PM = auto()    # Power Module
    JSM = auto()   # Joystick Module
    IOM = auto()   # Input/Output Module
    BTM = auto()   # Bluetooth Module
    ILM = auto()   # Indicator Light Module
    CJSM = auto()  # Color JSM
    ICS = auto()   # R-Net Programmer
    UNKNOWN = auto()


SLOT_NAMES = {
    0: "PM (Power Module)",
    1: "JSM (Joystick Module)",
    2: "Slot 2",
    3: "Slot 3",
    4: "Slot 4",
    5: "Slot 5",
    6: "Slot 6",
    7: "Slot 7",
    8: "cJSM Slot 8",
    0xF: "R-Net Programmer",
}


# ============================================================================
# Serial Number / XOR Key Functions
# ============================================================================

def derive_keys(serial: List[int], xor_table: List[int]) -> List[int]:
    """
    Derive authentication keys from a serial number using XOR table.

    Args:
        serial: 8-byte serial number as list of ints
        xor_table: 8-byte XOR table as list of ints

    Returns:
        8-byte list of derived keys
    """
    if len(serial) != 8 or len(xor_table) != 8:
        raise ValueError("Serial and XOR table must be 8 bytes each")
    return [s ^ x for s, x in zip(serial, xor_table)]


def extract_xor_table(serial: List[int], keys: List[int]) -> List[int]:
    """
    Extract XOR table given a known serial and observed keys.

    Args:
        serial: 8-byte serial number
        keys: 8-byte observed keys from authentication frames

    Returns:
        8-byte XOR table
    """
    if len(serial) != 8 or len(keys) != 8:
        raise ValueError("Serial and keys must be 8 bytes each")
    return [s ^ k for s, k in zip(serial, keys)]


def parse_serial_heartbeat(frame_data: bytes) -> Optional[List[int]]:
    """
    Parse serial number from 00E# heartbeat frame.

    Args:
        frame_data: 8 bytes of frame data

    Returns:
        8-byte serial number or None if invalid
    """
    if len(frame_data) < 8:
        return None
    # First 4 bytes are serial, last 4 are usually 00000000
    return list(frame_data[:8])


def parse_auth_frame_id(frame_id: int) -> Tuple[int, int, int, int]:
    """
    Parse a serial authentication frame ID (0x1FXXXXXX format).

    Frame ID structure:
        0x1F [SEQ][SLOT] [KEY][VALUE]

    Args:
        frame_id: 29-bit extended frame ID

    Returns:
        Tuple of (sequence, slot, key, value)
    """
    if (frame_id >> 24) != 0x1F:
        raise ValueError(f"Not an auth frame: 0x{frame_id:08X}")

    seq_slot = (frame_id >> 16) & 0xFF
    key_val = frame_id & 0xFFFF

    seq = (seq_slot >> 4) & 0x0F
    slot = seq_slot & 0x0F
    key = (key_val >> 8) & 0xFF
    value = key_val & 0xFF

    return seq, slot, key, value


def build_auth_frame_id(seq: int, slot: int, key: int, value: int) -> int:
    """
    Build a serial authentication frame ID.

    Args:
        seq: Sequence number (0-7)
        slot: Device slot (0-F)
        key: Derived key byte
        value: Serial byte or challenge value

    Returns:
        29-bit extended frame ID
    """
    return (0x1F << 24) | ((seq & 0xF) << 20) | ((slot & 0xF) << 16) | ((key & 0xFF) << 8) | (value & 0xFF)


def format_serial(serial: List[int]) -> str:
    """Format serial number as hex string."""
    return ''.join(f'{b:02X}' for b in serial)


def parse_serial_string(serial_str: str) -> List[int]:
    """Parse hex string to serial number list."""
    serial_str = serial_str.replace(' ', '').replace(':', '')
    if len(serial_str) != 16:
        raise ValueError("Serial must be 16 hex characters (8 bytes)")
    return [int(serial_str[i:i+2], 16) for i in range(0, 16, 2)]


# ============================================================================
# Frame Parsing and Analysis
# ============================================================================

@dataclass
class RNetFrame:
    """Parsed R-Net CAN frame."""
    frame_id: int
    is_extended: bool
    is_rtr: bool
    data: bytes
    description: str = ""
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    @property
    def id_str(self) -> str:
        """Frame ID as cansend-format string."""
        if self.is_extended:
            return f"{self.frame_id:08X}"
        return f"{self.frame_id:03X}"

    @property
    def data_str(self) -> str:
        """Data as hex string."""
        return ''.join(f'{b:02X}' for b in self.data)

    def __str__(self) -> str:
        rtr = "R" if self.is_rtr else ""
        return f"{self.id_str}#{self.data_str}{rtr}"


def parse_cansend_frame(frame_str: str) -> RNetFrame:
    """
    Parse a cansend-format frame string.

    Args:
        frame_str: Frame in format "ID#DATA" or "ID#R"

    Returns:
        Parsed RNetFrame object
    """
    if '#' not in frame_str:
        raise ValueError(f"Invalid frame format: {frame_str}")

    parts = frame_str.split('#')
    id_str = parts[0].upper()
    data_str = parts[1].upper() if len(parts) > 1 else ""

    is_rtr = data_str.endswith('R')
    if is_rtr:
        data_str = data_str[:-1]

    is_extended = len(id_str) == 8
    frame_id = int(id_str, 16)

    # Parse data
    data_str = data_str.replace('.', '')
    data = bytes.fromhex(data_str) if data_str else b''

    frame = RNetFrame(
        frame_id=frame_id,
        is_extended=is_extended,
        is_rtr=is_rtr,
        data=data
    )

    # Decode frame
    decode_frame(frame)

    return frame


def decode_frame(frame: RNetFrame) -> None:
    """
    Decode an R-Net frame and populate description/details.

    Modifies frame in place.
    """
    fid = frame.frame_id
    data = frame.data

    # Standard frames (11-bit)
    if not frame.is_extended:
        if fid == 0x000:
            frame.description = "Sleep command" if not frame.is_rtr else "Sleep all devices"
        elif fid == 0x00C:
            frame.description = "Network test"
        elif fid == 0x00E:
            frame.description = "Serial heartbeat"
            if len(data) >= 4:
                frame.details['serial'] = format_serial(list(data[:4]))
        elif fid == 0x040:
            frame.description = "Open parameter page"
        elif fid == 0x041:
            frame.description = "Close parameter page"
        elif fid == 0x050:
            frame.description = "Mode map"
        elif fid == 0x061:
            frame.description = "Mode control"
            if len(data) >= 4:
                if data[0] == 0x40 and data[1] == 0x40:
                    frame.details['action'] = "Suspend mode"
                elif data[0] == 0x00 and data[1] >= 0x40:
                    frame.details['action'] = f"Select mode {data[1] - 0x40}"
        elif 0x780 <= fid <= 0x78F:
            slot = fid - 0x780
            frame.description = f"Parameter request (slot {slot})"
            if len(data) >= 2:
                frame.details['command'] = decode_param_command(data[0])
                frame.details['register'] = f"0x{data[1]:02X}"
        elif 0x790 <= fid <= 0x79F:
            slot = fid - 0x790
            frame.description = f"Parameter response (slot {slot})"
            if len(data) >= 2:
                frame.details['command'] = decode_param_command(data[0])
        elif fid == 0x7B0:
            frame.description = "Config mode 0"
        elif fid == 0x7B1:
            frame.description = "Config mode 1"
        elif fid == 0x7B3:
            frame.description = "Serial exchange request" if frame.is_rtr else "Serial exchange"
        else:
            frame.description = f"Standard frame 0x{fid:03X}"

    # Extended frames (29-bit)
    else:
        # Serial authentication frames
        if (fid >> 24) == 0x1F:
            try:
                seq, slot, key, value = parse_auth_frame_id(fid)
                action = "RTR challenge" if frame.is_rtr else "Response"
                frame.description = f"Serial auth {action}"
                frame.details = {
                    'sequence': seq,
                    'slot': slot,
                    'key': f"0x{key:02X}",
                    'value': f"0x{value:02X}",
                }
            except ValueError:
                frame.description = "Unknown auth frame"

        # Joystick position: 02000X00 where X is slot
        elif (fid & 0xFFFFF0FF) == 0x02000000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Joystick position (slot {slot})"
            if len(data) >= 2:
                x = struct.unpack('b', bytes([data[0]]))[0]
                y = struct.unpack('b', bytes([data[1]]))[0]
                frame.details = {'x': x, 'y': y}

        # Speed setting: 0A040X00 where X is slot
        elif (fid & 0xFFFFF0FF) == 0x0A040000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Speed setting (slot {slot})"
            if len(data) >= 1:
                frame.details['speed_percent'] = data[0]

        # Horn: 0C040X0Y where X is slot, Y is 0=start 1=stop
        elif (fid & 0xFFFFF0F0) == 0x0C040000:
            slot = (fid >> 8) & 0xF
            state = "start" if (fid & 0x0F) == 0x00 else "stop"
            frame.description = f"Horn {state} (slot {slot})"

        # Battery level: 1C0C0X00 where X is slot
        elif (fid & 0xFFFFF0FF) == 0x1C0C0000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Battery level (slot {slot})"
            if len(data) >= 1:
                frame.details['battery_percent'] = data[0]

        # Motor current: 14300X00 where X is slot
        elif (fid & 0xFFFFF0FF) == 0x14300000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Motor current (slot {slot})"
            if len(data) >= 4:
                left = struct.unpack('<H', data[0:2])[0]
                right = struct.unpack('<H', data[2:4])[0]
                frame.details = {'left': left, 'right': right}

        # JSM heartbeat
        elif fid == 0x03C30F0F:
            frame.description = "JSM heartbeat"

        # PM heartbeat: 0C140X00 where X is slot
        elif (fid & 0xFFFFF0FF) == 0x0C140000:
            slot = (fid >> 8) & 0xF
            frame.description = f"PM heartbeat (slot {slot})"

        # Tone/buzzer
        elif fid == 0x181C0D00:
            frame.description = "Play tones"
            if len(data) >= 2:
                tones = []
                for i in range(0, len(data), 2):
                    if i + 1 < len(data):
                        length = data[i]
                        note = data[i + 1]
                        tones.append(f"L{length}:N{note}")
                frame.details['tones'] = tones

        # Device enumeration
        elif (fid & 0xFFFFFF00) == 0x1FB00000:
            slot = fid & 0xF
            frame.description = f"Device enumeration (slot {slot})"
            if len(data) >= 8:
                frame.details['serial'] = format_serial(list(data[:8]))

        # Configuration transfer
        elif 0x1E3C0000 <= fid <= 0x1E8FFFFF:
            frame.description = "Configuration transfer"

        # Lighting
        elif (fid & 0xFFFF0000) == 0x0C000000:
            frame.description = "Lighting control"
            if len(data) >= 1:
                lights = []
                if data[0] & 0x01:
                    lights.append("Left")
                if data[0] & 0x04:
                    lights.append("Right")
                if data[0] & 0x10:
                    lights.append("Hazard")
                if data[0] & 0x80:
                    lights.append("Flood")
                frame.details['active'] = lights

        # Distance counter: 1C300X04
        elif (fid & 0xFFFFF0FF) == 0x1C300004:
            slot = (fid >> 8) & 0xF
            frame.description = f"Distance counter (slot {slot})"
            if len(data) >= 8:
                left = struct.unpack('<I', data[0:4])[0]
                right = struct.unpack('<I', data[4:8])[0]
                frame.details = {'left_dist': left, 'right_dist': right}

        # Power down/ready: 1C240X0Y
        elif (fid & 0xFFFFF0F0) == 0x1C240000:
            slot = (fid >> 8) & 0xF
            state = "ready" if (fid & 0x0F) == 0x01 else "power down"
            frame.description = f"Device {state} (slot {slot})"

        # Motor enable: 0C180X0Y
        elif (fid & 0xFFFFF0F0) == 0x0C180000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Motor control (slot {slot})"
            if len(data) >= 2:
                frame.details = {'motor_left': data[0], 'motor_right': data[1]}

        # Error/status: 140C0X0Y
        elif (fid & 0xFFFFF0F0) == 0x140C0000:
            slot = (fid >> 8) & 0xF
            frame.description = f"Status/error (slot {slot})"

        else:
            frame.description = f"Extended frame 0x{fid:08X}"


def decode_param_command(cmd: int) -> str:
    """Decode parameter exchange command byte."""
    commands = {
        0x20: "Open page / Set pointer",
        0x21: "Response with data",
        0x40: "Request data",
        0x41: "ACK (pointer exists)",
        0x83: "ICS read address",
        0x8F: "ICS operation complete",
        0xC1: "Error (address not found)",
    }
    return commands.get(cmd, f"Unknown (0x{cmd:02X})")


# ============================================================================
# Capture File Analysis
# ============================================================================

def parse_candump_line(line: str) -> Optional[Tuple[float, str, RNetFrame]]:
    """
    Parse a line from candump -l output.

    Format: (timestamp) interface frame
    Example: (1234567890.123456) can0 02000100#0064

    Returns:
        Tuple of (timestamp, interface, frame) or None
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    try:
        # Format: (timestamp) interface frame
        if line.startswith('('):
            parts = line.split()
            timestamp = float(parts[0].strip('()'))
            interface = parts[1]
            frame_str = parts[2]
        else:
            # Simple format: interface frame
            parts = line.split()
            timestamp = 0.0
            interface = parts[0]
            frame_str = parts[1]

        frame = parse_cansend_frame(frame_str)
        return timestamp, interface, frame
    except (ValueError, IndexError):
        return None


def analyze_capture_file(filepath: str) -> Dict:
    """
    Analyze a candump log file.

    Returns summary statistics and interesting frames.
    """
    stats = {
        'total_frames': 0,
        'standard_frames': 0,
        'extended_frames': 0,
        'rtr_frames': 0,
        'frame_types': {},
        'serials_seen': set(),
        'auth_sequences': [],
        'joystick_samples': [],
        'errors': [],
    }

    with open(filepath, 'r') as f:
        for line in f:
            result = parse_candump_line(line)
            if not result:
                continue

            timestamp, interface, frame = result
            stats['total_frames'] += 1

            if frame.is_extended:
                stats['extended_frames'] += 1
            else:
                stats['standard_frames'] += 1

            if frame.is_rtr:
                stats['rtr_frames'] += 1

            # Track frame types
            desc = frame.description
            stats['frame_types'][desc] = stats['frame_types'].get(desc, 0) + 1

            # Track serials
            if 'serial' in frame.details:
                stats['serials_seen'].add(frame.details['serial'])

            # Track auth frames
            if frame.description.startswith("Serial auth"):
                stats['auth_sequences'].append({
                    'timestamp': timestamp,
                    'frame': str(frame),
                    'details': frame.details.copy(),
                })

            # Sample joystick positions
            if frame.description.startswith("Joystick position"):
                if len(stats['joystick_samples']) < 100:  # Limit samples
                    stats['joystick_samples'].append({
                        'timestamp': timestamp,
                        'x': frame.details.get('x', 0),
                        'y': frame.details.get('y', 0),
                    })

    # Convert set to list for JSON serialization
    stats['serials_seen'] = list(stats['serials_seen'])

    return stats


# ============================================================================
# XOR Table Extraction from Captures
# ============================================================================

def extract_xor_from_auth_frames(frames: List[RNetFrame], known_serial: List[int]) -> Optional[List[int]]:
    """
    Extract XOR table from a sequence of authentication frames.

    Args:
        frames: List of auth response frames (non-RTR)
        known_serial: The serial number being authenticated

    Returns:
        Extracted XOR table or None if insufficient data
    """
    keys = [None] * 8

    for frame in frames:
        if frame.is_rtr:
            continue
        try:
            seq, slot, key, value = parse_auth_frame_id(frame.frame_id)
            if seq < 8:
                keys[seq] = key
        except ValueError:
            continue

    if None in keys:
        return None

    return extract_xor_table(known_serial, keys)


# ============================================================================
# Pretty Printing
# ============================================================================

def print_frame_analysis(frame: RNetFrame, verbose: bool = False) -> None:
    """Print detailed frame analysis."""
    print(f"\nFrame: {frame}")
    print(f"  Type: {'Extended' if frame.is_extended else 'Standard'} {'RTR' if frame.is_rtr else 'Data'}")
    print(f"  Description: {frame.description}")

    if frame.details:
        print("  Details:")
        for key, value in frame.details.items():
            print(f"    {key}: {value}")


def print_xor_analysis(serial: List[int], xor_table: List[int]) -> None:
    """Print XOR key derivation analysis."""
    keys = derive_keys(serial, xor_table)

    print("\nSerial Number Authentication Analysis")
    print("=" * 50)
    print(f"Serial:    {format_serial(serial)}")
    print(f"XOR Table: {format_serial(xor_table)}")
    print(f"Keys:      {format_serial(keys)}")
    print()
    print("Sequence breakdown:")
    print("-" * 50)
    for i in range(8):
        print(f"  Seq {i}: serial[{i}]=0x{serial[i]:02X} XOR table[{i}]=0x{xor_table[i]:02X} = key[{i}]=0x{keys[i]:02X}")
    print()
    print("Expected auth frames (RTR challenges):")
    for i in range(8):
        fid = build_auth_frame_id(i, 1, keys[i], 0x00)
        print(f"  Seq {i}: 0x{fid:08X}#R")
    print()
    print("Expected auth frames (responses):")
    for i in range(8):
        fid = build_auth_frame_id(i, 1, keys[i], serial[i])
        print(f"  Seq {i}: 0x{fid:08X}#")


# ============================================================================
# Command Line Interface
# ============================================================================

def cmd_decode_serial(args):
    """Handle serial decode command."""
    serial = parse_serial_string(args.serial)

    # Try to find matching XOR table
    if args.xor_table:
        xor_table = parse_serial_string(args.xor_table)
        print_xor_analysis(serial, xor_table)
    else:
        print(f"Serial: {format_serial(serial)}")
        print("\nTrying known XOR tables:")
        for name, table_info in XOR_TABLES.items():
            xor_table = table_info['table']
            keys = derive_keys(serial, xor_table)
            print(f"\n  {name}: {table_info['description']}")
            print(f"    XOR Table: {format_serial(xor_table)}")
            print(f"    Keys:      {format_serial(keys)}")


def cmd_decode_frame(args):
    """Handle frame decode command."""
    for frame_str in args.frames:
        try:
            frame = parse_cansend_frame(frame_str)
            print_frame_analysis(frame, args.verbose)
        except ValueError as e:
            print(f"Error parsing '{frame_str}': {e}")


def cmd_analyze_capture(args):
    """Handle capture analysis command."""
    stats = analyze_capture_file(args.file)

    print(f"\nCapture Analysis: {args.file}")
    print("=" * 60)
    print(f"Total frames:    {stats['total_frames']}")
    print(f"Standard frames: {stats['standard_frames']}")
    print(f"Extended frames: {stats['extended_frames']}")
    print(f"RTR frames:      {stats['rtr_frames']}")

    print(f"\nSerials seen:    {len(stats['serials_seen'])}")
    for serial in stats['serials_seen']:
        print(f"  {serial}")

    print(f"\nAuth sequences:  {len(stats['auth_sequences'])}")

    print("\nFrame type distribution:")
    for desc, count in sorted(stats['frame_types'].items(), key=lambda x: -x[1]):
        print(f"  {count:6d}  {desc}")


def cmd_extract_xor(args):
    """Handle XOR table extraction command."""
    serial = parse_serial_string(args.serial)
    keys = parse_serial_string(args.keys)

    xor_table = extract_xor_table(serial, keys)

    print(f"Serial:    {format_serial(serial)}")
    print(f"Keys:      {format_serial(keys)}")
    print(f"XOR Table: {format_serial(xor_table)}")


def cmd_list_tables(args):
    """List known XOR tables."""
    print("\nKnown XOR Tables")
    print("=" * 60)
    for name, info in XOR_TABLES.items():
        print(f"\n{name}:")
        print(f"  Description: {info['description']}")
        print(f"  XOR Table:   {format_serial(info['table'])}")
        if info['example_serial']:
            print(f"  Example S/N: {format_serial(info['example_serial'])}")
            keys = derive_keys(info['example_serial'], info['table'])
            print(f"  Keys:        {format_serial(keys)}")


def cmd_extract_auth(args):
    """Extract authentication info from capture file."""
    auth_data = {}  # slot -> {serial, keys, challenges}

    with open(args.file, 'r') as f:
        for line in f:
            result = parse_candump_line(line)
            if not result:
                continue

            timestamp, interface, frame = result

            # Track serial heartbeats
            if frame.description == "Serial heartbeat" and 'serial' in frame.details:
                serial_str = frame.details['serial']
                # Assume slot 1 for JSM serial heartbeats
                if 1 not in auth_data:
                    auth_data[1] = {'serial': serial_str, 'keys': [None] * 8, 'responses': [None] * 8}

            # Track auth frames
            if frame.description.startswith("Serial auth"):
                try:
                    seq, slot, key, value = parse_auth_frame_id(frame.frame_id)
                    if slot not in auth_data:
                        auth_data[slot] = {'serial': None, 'keys': [None] * 8, 'responses': [None] * 8}

                    auth_data[slot]['keys'][seq] = key
                    if not frame.is_rtr:
                        auth_data[slot]['responses'][seq] = value
                except ValueError:
                    pass

    print(f"\nAuthentication Analysis: {args.file}")
    print("=" * 60)

    for slot, data in sorted(auth_data.items()):
        print(f"\nSlot {slot}:")
        if data['serial']:
            print(f"  Serial (from heartbeat): {data['serial']}")

        if None not in data['keys']:
            print(f"  Keys:      {format_serial(data['keys'])}")
        else:
            print(f"  Keys:      {data['keys']} (incomplete)")

        if None not in data['responses']:
            print(f"  Responses: {format_serial(data['responses'])}")

            # If we have complete keys and responses, try to extract XOR table
            if None not in data['keys']:
                serial = data['responses']
                keys = data['keys']
                xor_table = extract_xor_table(serial, keys)
                print(f"  XOR Table: {format_serial(xor_table)}")

                # Check if it matches any known table
                for name, info in XOR_TABLES.items():
                    if xor_table == info['table']:
                        print(f"  Matches:   {name} ({info['description']})")
                        break
        else:
            responses_str = [f"{v:02X}" if v is not None else "??" for v in data['responses']]
            print(f"  Responses: {''.join(responses_str)} (incomplete)")


def cmd_generate_auth(args):
    """Generate authentication frames for a given serial and XOR table."""
    serial = parse_serial_string(args.serial)

    # Get XOR table
    if args.xor_table:
        xor_table = parse_serial_string(args.xor_table)
    elif args.table_name:
        if args.table_name not in XOR_TABLES:
            print(f"Unknown table: {args.table_name}")
            print(f"Known tables: {', '.join(XOR_TABLES.keys())}")
            return
        xor_table = XOR_TABLES[args.table_name]['table']
    else:
        print("Must specify either --xor or --table")
        return

    slot = args.slot
    keys = derive_keys(serial, xor_table)

    print(f"\nGenerated Auth Frames for Serial {format_serial(serial)}")
    print(f"Slot: {slot}, XOR Table: {format_serial(xor_table)}")
    print("=" * 60)

    if args.format == 'cansend':
        print("\n# RTR Challenges (from PM):")
        for seq in range(8):
            fid = build_auth_frame_id(seq, slot, keys[seq], 0x00)
            print(f"# cansend can0 {fid:08X}#R")

        print("\n# Responses (from device):")
        for seq in range(8):
            fid = build_auth_frame_id(seq, slot, keys[seq], serial[seq])
            print(f"cansend can0 {fid:08X}#")

        print("\n# Serial heartbeat:")
        print(f"cansend can0 00E#{format_serial(serial)}")

    elif args.format == 'python':
        print("\n# Python code for can2RNET:")
        print(f"serial = {serial}")
        print(f"xor_table = {xor_table}")
        print(f"keys = {keys}")
        print(f"slot = {slot}")
        print()
        print("# Send serial heartbeat")
        print(f"cansend(sock, '00E#{format_serial(serial)}')")
        print()
        print("# Respond to RTR challenges:")
        for seq in range(8):
            fid = build_auth_frame_id(seq, slot, keys[seq], serial[seq])
            print(f"cansend(sock, '{fid:08X}#')  # seq {seq}")


def cmd_joystick_calc(args):
    """Calculate joystick frame values."""
    x = max(-100, min(100, args.x))
    y = max(-100, min(100, args.y))

    # Convert to signed byte
    x_byte = x & 0xFF
    y_byte = y & 0xFF

    slot = args.slot
    frame_id = 0x02000000 | (slot << 8)

    print(f"\nJoystick Frame Calculation")
    print("=" * 40)
    print(f"Input:  X={x:+4d}, Y={y:+4d}")
    print(f"Bytes:  X=0x{x_byte:02X}, Y=0x{y_byte:02X}")
    print(f"Slot:   {slot}")
    print(f"Frame:  {frame_id:08X}#{x_byte:02X}{y_byte:02X}")
    print()
    print(f"# cansend command:")
    print(f"cansend can0 {frame_id:08X}#{x_byte:02X}{y_byte:02X}")

    if args.continuous:
        print()
        print("# Continuous sending (every 10ms):")
        print(f"while true; do cansend can0 {frame_id:08X}#{x_byte:02X}{y_byte:02X}; sleep 0.01; done")


def cmd_extract_display(args):
    """Extract display text from cJSM parameter frames."""
    text_chunks = []
    mode_configs = []

    with open(args.file, 'r') as f:
        for line in f:
            result = parse_candump_line(line)
            if not result:
                continue

            timestamp, interface, frame = result

            # Look for parameter response frames with 0x8C register (text)
            if not frame.is_extended and 0x790 <= frame.frame_id <= 0x79F:
                if len(frame.data) >= 8:
                    cmd = frame.data[0]
                    reg = frame.data[1]
                    if cmd == 0x20 and reg == 0x8C:
                        # Extract text from bytes 4-7
                        text_data = frame.data[4:8]
                        try:
                            text = text_data.decode('ascii', errors='replace')
                            text_chunks.append({
                                'timestamp': timestamp,
                                'slot': frame.frame_id - 0x790,
                                'text': text,
                                'raw': text_data.hex(),
                            })
                        except:
                            pass

            # Look for mode config frames (0x1ECXXXXX)
            if frame.is_extended and (frame.frame_id >> 20) == 0x1EC:
                mode = (frame.frame_id >> 16) & 0xF
                subaddr = (frame.frame_id >> 8) & 0xFF
                dtype = frame.frame_id & 0xFF
                mode_configs.append({
                    'timestamp': timestamp,
                    'mode': mode,
                    'subaddr': subaddr,
                    'type': dtype,
                    'data': frame.data.hex() if frame.data else '',
                })

    print(f"\ncJSM Display Analysis: {args.file}")
    print("=" * 60)

    # Reconstruct text strings
    if text_chunks:
        print(f"\nDisplay Text ({len(text_chunks)} chunks):")
        print("-" * 40)

        # Group consecutive text chunks
        current_string = ""
        for chunk in text_chunks:
            text = chunk['text']
            if text.strip():
                current_string += text
            else:
                if current_string.strip():
                    print(f"  \"{current_string.strip()}\"")
                current_string = ""

        if current_string.strip():
            print(f"  \"{current_string.strip()}\"")

        if args.verbose:
            print("\nRaw text chunks:")
            for chunk in text_chunks[:50]:
                print(f"  [{chunk['raw']}] \"{chunk['text']}\"")
            if len(text_chunks) > 50:
                print(f"  ... and {len(text_chunks) - 50} more")

    # Show mode configs
    if mode_configs and args.verbose:
        print(f"\nMode Configuration Frames ({len(mode_configs)} frames):")
        print("-" * 40)
        modes_seen = {}
        for cfg in mode_configs:
            key = (cfg['mode'], cfg['subaddr'], cfg['type'])
            if key not in modes_seen:
                modes_seen[key] = cfg
                print(f"  Mode {cfg['mode']}, Sub 0x{cfg['subaddr']:02X}, Type 0x{cfg['type']:02X}: {cfg['data']}")

    if not text_chunks and not mode_configs:
        print("No cJSM display data found in capture.")


def main():
    parser = argparse.ArgumentParser(
        description="R-Net Protocol Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decode a serial number with known XOR table
  %(prog)s decode-serial 08901c8a00000000 --xor 002102ccdd127b45

  # Decode frames
  %(prog)s decode-frame 02000100#0064 00E#08901C8A00000000

  # Analyze a capture file
  %(prog)s analyze capture.log

  # Extract authentication info and XOR table from capture
  %(prog)s extract-auth capture.log

  # Generate auth frames for spoofing a serial
  %(prog)s generate-auth 08901c8a00000000 --table standalone_jsm
  %(prog)s generate-auth 50c01c8f00000000 --table m300 --format python

  # Calculate joystick frame for given position
  %(prog)s joystick 0 100      # full forward
  %(prog)s joystick 50 50 -c   # diagonal with continuous

  # Extract XOR table from observed serial and keys
  %(prog)s extract-xor --serial 08901c8a00000000 --keys 08b11e46dd127b45

  # List known XOR tables
  %(prog)s list-tables
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # decode-serial command
    p_serial = subparsers.add_parser('decode-serial', help='Decode serial number authentication')
    p_serial.add_argument('serial', help='8-byte serial number as hex (e.g., 08901c8a00000000)')
    p_serial.add_argument('--xor', dest='xor_table', help='8-byte XOR table as hex')
    p_serial.set_defaults(func=cmd_decode_serial)

    # decode-frame command
    p_frame = subparsers.add_parser('decode-frame', help='Decode R-Net frames')
    p_frame.add_argument('frames', nargs='+', help='Frames in cansend format (e.g., 02000100#0064)')
    p_frame.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    p_frame.set_defaults(func=cmd_decode_frame)

    # analyze command
    p_analyze = subparsers.add_parser('analyze', help='Analyze capture file')
    p_analyze.add_argument('file', help='Path to candump log file')
    p_analyze.set_defaults(func=cmd_analyze_capture)

    # extract-xor command
    p_xor = subparsers.add_parser('extract-xor', help='Extract XOR table from serial and keys')
    p_xor.add_argument('--serial', required=True, help='8-byte serial number as hex')
    p_xor.add_argument('--keys', required=True, help='8-byte observed keys as hex')
    p_xor.set_defaults(func=cmd_extract_xor)

    # list-tables command
    p_list = subparsers.add_parser('list-tables', help='List known XOR tables')
    p_list.set_defaults(func=cmd_list_tables)

    # extract-auth command
    p_auth = subparsers.add_parser('extract-auth', help='Extract authentication info from capture')
    p_auth.add_argument('file', help='Path to candump log file')
    p_auth.set_defaults(func=cmd_extract_auth)

    # generate-auth command
    p_genauth = subparsers.add_parser('generate-auth', help='Generate auth frames for spoofing')
    p_genauth.add_argument('serial', help='8-byte serial number as hex')
    p_genauth.add_argument('--xor', dest='xor_table', help='8-byte XOR table as hex')
    p_genauth.add_argument('--table', dest='table_name', help='Use named XOR table (standalone_jsm, m300, btm)')
    p_genauth.add_argument('--slot', type=int, default=1, help='Device slot (default: 1)')
    p_genauth.add_argument('--format', choices=['cansend', 'python'], default='cansend',
                           help='Output format (default: cansend)')
    p_genauth.set_defaults(func=cmd_generate_auth)

    # joystick command
    p_joy = subparsers.add_parser('joystick', help='Calculate joystick frame values')
    p_joy.add_argument('x', type=int, help='X position (-100 to +100)')
    p_joy.add_argument('y', type=int, help='Y position (-100 to +100)')
    p_joy.add_argument('--slot', type=int, default=1, help='Device slot (default: 1)')
    p_joy.add_argument('--continuous', '-c', action='store_true', help='Show continuous send command')
    p_joy.set_defaults(func=cmd_joystick_calc)

    # extract-display command
    p_display = subparsers.add_parser('extract-display', help='Extract cJSM display text from capture')
    p_display.add_argument('file', help='Path to candump log file')
    p_display.add_argument('-v', '--verbose', action='store_true', help='Show raw chunks and mode configs')
    p_display.set_defaults(func=cmd_extract_display)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
