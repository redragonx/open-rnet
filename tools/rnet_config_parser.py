#!/usr/bin/env python3
"""
R-Net Configuration File Parser

Parses .R-net files exported from R-Net Programmer software.
Extracts speed profiles, motor limits, seating functions, and other settings.

Usage:
    python3 rnet_config_parser.py <file.R-net>              # Parse single file
    python3 rnet_config_parser.py <file.R-net> --json       # Output as JSON
    python3 rnet_config_parser.py <file1> <file2> --diff    # Compare two configs
    python3 rnet_config_parser.py <file.R-net> --raw        # Show raw hex regions
    python3 rnet_config_parser.py <file.R-net> --motor      # Focus on motor settings

Author: Stephen Chavez
"""

import argparse
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any


# Constants
XOR_PATTERN = bytes.fromhex('9d82c7a3f28db441')
PROFILE_MARKER = b'>@<'
SPEED_PREFIX = b'dddd'


@dataclass
class SpeedProfile:
    """Speed/drive profile configuration"""
    name: str
    offset: int
    max_forward: int = 0
    max_reverse: int = 0
    acceleration: int = 0
    deceleration: int = 0
    turn_speed: int = 0
    raw_data: str = ""


@dataclass
class ModeProfile:
    """Input mode profile (Drive, Seating, Bluetooth, etc.)"""
    name: str
    offset: int
    enabled: bool = True
    raw_data: str = ""


@dataclass
class SeatingFunction:
    """Seating/actuator function configuration"""
    name: str
    offset: int
    speed: int = 0
    range_min: int = 0
    range_max: int = 0
    raw_data: str = ""


@dataclass
class MotorSettings:
    """Motor controller settings"""
    profile_limits: Dict[int, int] = field(default_factory=dict)  # profile_num -> current %
    base_current: int = 0
    max_current: int = 0
    acceleration_limit: int = 0
    raw_offsets: Dict[int, int] = field(default_factory=dict)  # offset -> value


@dataclass
class RNetConfig:
    """Complete R-Net configuration"""
    filename: str
    size: int
    header_magic: str
    checksum: str
    serial: str = ""

    mode_profiles: List[ModeProfile] = field(default_factory=list)
    speed_profiles: List[SpeedProfile] = field(default_factory=list)
    seating_functions: List[SeatingFunction] = field(default_factory=list)
    motor_settings: MotorSettings = field(default_factory=MotorSettings)

    xor_pattern_count: int = 0
    raw_sections: Dict[str, str] = field(default_factory=dict)


class RNetConfigParser:
    """Parser for .R-net configuration files"""

    # Known seating function names
    SEATING_NAMES = [
        'Tilt', 'Seat Lift', 'Recline', 'Transfer Tilt', 'Leg', 'Leg Rest',
        'Layback', 'Elevator', 'Head Rest', 'Backrest', 'Footrest'
    ]

    # Known mode names
    MODE_NAMES = [
        'Drive', 'Seating', 'Bluetooth', 'Bluetooth2', 'iDevice', 'IR Mode',
        'Programming', 'Mouse Control', 'Environmental', 'Attendant',
        'Input Module', 'Output Module'
    ]

    # Motor current limit offsets (discovered from 90amp mod analysis)
    MOTOR_LIMIT_OFFSETS = [
        0x0B23, 0x0B30, 0x0B3D, 0x0B4A, 0x0B57, 0x0B64,
        0x0B71, 0x0B7E, 0x0B8B, 0x0B98, 0x0BA5, 0x0BB2
    ]

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = b''
        self.config = None

    def parse(self) -> RNetConfig:
        """Parse the R-net file and return configuration"""
        with open(self.filepath, 'rb') as f:
            self.data = f.read()

        # Extract serial from filename
        serial = ""
        match = re.search(r'(C[SR]\d{8})', os.path.basename(self.filepath))
        if match:
            serial = match.group(1)

        self.config = RNetConfig(
            filename=os.path.basename(self.filepath),
            size=len(self.data),
            header_magic=self.data[:4].hex(),
            checksum=self.data[0x18:0x1C].hex() if len(self.data) > 0x1C else "",
            serial=serial
        )

        # Count XOR pattern occurrences
        self.config.xor_pattern_count = self.data.count(XOR_PATTERN)

        # Parse sections
        self._parse_mode_profiles()
        self._parse_speed_profiles()
        self._parse_seating_functions()
        self._parse_motor_settings()
        self._extract_raw_sections()

        return self.config

    def _clean_string(self, data: bytes) -> str:
        """Extract clean ASCII string from binary data"""
        try:
            # Decode and filter printable chars
            s = data.decode('ascii', errors='ignore')
            s = ''.join(c if 32 <= ord(c) < 127 else '' for c in s)
            return s.strip()
        except:
            return ''

    def _parse_mode_profiles(self):
        """Parse input mode profiles (Drive, Seating, etc.)"""
        # Mode profiles are around 0x0160-0x0250
        # Format: 16-byte name + ">@<" marker + control bytes

        start = 0x0160
        end = min(len(self.data), 0x0300)
        seen_names = set()

        i = start
        while i < end - 20:
            # Look for the >@< marker
            if self.data[i+16:i+19] == PROFILE_MARKER:
                name = self._clean_string(self.data[i:i+16])
                if name and len(name) >= 3 and name not in seen_names:
                    # Check if it's a known mode or looks valid
                    is_known = any(known.lower() in name.lower() for known in self.MODE_NAMES)
                    # Must start with capital letter and be valid name
                    is_valid = name[0].isupper() and not all(c in 'dDxX-#' for c in name)
                    if is_known or is_valid:
                        seen_names.add(name)
                        profile = ModeProfile(
                            name=name,
                            offset=i,
                            enabled=True,  # Could parse control bytes
                            raw_data=self.data[i:i+24].hex()
                        )
                        self.config.mode_profiles.append(profile)
                i += 20
            else:
                i += 1

    def _parse_speed_profiles(self):
        """Parse speed/drive profiles (Indoor, Fast, etc.)"""
        # Speed profiles are around 0x0250-0x0600
        # Format: prefix (often 'dddd') + 16-byte name + config bytes
        # Profile blocks are typically 24-28 bytes with structure:
        #   [prefix 4 bytes] [name 16 bytes, padded] [config ~8 bytes]

        start = 0x0250
        end = min(len(self.data), 0x0600)

        seen_names = set()

        # Look for 'dddd' prefix followed by readable name
        i = start
        while i < end - 28:
            chunk = self.data[i:i+28]

            # Speed profiles start with 'dddd' prefix (0x64646464)
            if chunk[:4] == SPEED_PREFIX:
                # Extract the 16-byte name field
                name_raw = chunk[4:20]
                name = self._clean_string(name_raw)

                # Valid profile names are at least 3 chars and not just 'd's
                if name and len(name) >= 3:
                    # Normalize: strip leading 'd' chars that leaked in
                    while name.startswith('d') and len(name) > 3:
                        name = name[1:]

                    # Skip pure noise patterns
                    noise_patterns = ['xx', 'dd', '##', '--']
                    is_noise = (
                        all(c in 'dDxX-#0123456789 ' for c in name) or
                        any(name.startswith(p) for p in noise_patterns) or
                        name.count('d') > len(name) // 2
                    )

                    if name and name not in seen_names and not is_noise:
                        seen_names.add(name)

                        # Parse configuration bytes (after 20-byte name block)
                        config_bytes = chunk[20:28]

                        profile = SpeedProfile(
                            name=name,
                            offset=i,
                            max_forward=config_bytes[0] if len(config_bytes) > 0 else 0,
                            max_reverse=config_bytes[1] if len(config_bytes) > 1 else 0,
                            acceleration=config_bytes[2] if len(config_bytes) > 2 else 0,
                            deceleration=config_bytes[3] if len(config_bytes) > 3 else 0,
                            turn_speed=config_bytes[4] if len(config_bytes) > 4 else 0,
                            raw_data=chunk.hex()
                        )
                        self.config.speed_profiles.append(profile)

                # Jump past this block
                i += 24
            else:
                i += 1

        # Secondary pass: look for keyword-based profiles that might not have dddd prefix
        keywords = ['SLOW', 'FAST', 'MEDIUM', 'MED', 'Indoor', 'Outdoor',
                   'Normal', 'Profile', 'Speed', 'DANGER', 'DIABLO',
                   'SOCCER', 'Torque', 'idiot', 'PWR', 'Standard', 'Attendant',
                   'High', 'Low']

        for i in range(start, end - 20, 4):  # Step by 4 to avoid overlaps
            text = self._clean_string(self.data[i:i+16])
            if text and len(text) >= 4 and text not in seen_names:
                # Must contain a speed-related keyword
                if any(kw.lower() in text.lower() for kw in keywords):
                    # Verify it's a clean name (starts with uppercase letter, no junk prefix)
                    if text[0].isupper() and not any(text.startswith(p) for p in ['ddd', 'xxx', '---']):
                        seen_names.add(text)
                        profile = SpeedProfile(
                            name=text,
                            offset=i,
                            raw_data=self.data[i:i+24].hex()
                        )
                        self.config.speed_profiles.append(profile)

    def _parse_seating_functions(self):
        """Parse seating/actuator function configuration"""
        # Seating functions are around 0x0C00-0x1000
        # Format: 20-byte name (padded) + control bytes

        start = 0x0800
        end = min(len(self.data), 0x1200)

        seen_names = set()

        for i in range(start, end - 20):
            text = self._clean_string(self.data[i:i+20])

            if text in self.SEATING_NAMES and text not in seen_names:
                seen_names.add(text)

                # Parse control bytes after name
                config_bytes = self.data[i+20:i+28] if len(self.data) > i + 28 else b''

                func = SeatingFunction(
                    name=text,
                    offset=i,
                    speed=config_bytes[0] if len(config_bytes) > 0 else 0,
                    range_min=config_bytes[1] if len(config_bytes) > 1 else 0,
                    range_max=config_bytes[2] if len(config_bytes) > 2 else 0,
                    raw_data=self.data[i:i+28].hex()
                )
                self.config.seating_functions.append(func)

    def _parse_motor_settings(self):
        """Parse motor controller settings"""
        settings = MotorSettings()

        # Parse known motor limit offsets
        for idx, offset in enumerate(self.MOTOR_LIMIT_OFFSETS):
            if offset < len(self.data):
                value = self.data[offset]
                settings.profile_limits[idx] = value
                settings.raw_offsets[offset] = value

        # Find base/max current in the 0x0600-0x0800 region
        # Look for values in the 50-100 range (percentage)
        for i in range(0x0600, min(len(self.data), 0x0800)):
            val = self.data[i]
            if 40 <= val <= 100:
                settings.raw_offsets[i] = val

        # Estimate base current from profile limits
        if settings.profile_limits:
            values = list(settings.profile_limits.values())
            settings.base_current = min(values) if values else 0
            settings.max_current = max(values) if values else 0

        self.config.motor_settings = settings

    def _extract_raw_sections(self):
        """Extract raw hex data for key sections"""
        sections = {
            'header': (0x0000, 0x0020),
            'metadata': (0x0100, 0x0160),
            'mode_region': (0x0160, 0x0250),
            'speed_region': (0x0250, 0x0400),
            'motor_region': (0x0B00, 0x0BC0),
        }

        for name, (start, end) in sections.items():
            if start < len(self.data):
                actual_end = min(end, len(self.data))
                self.config.raw_sections[name] = self.data[start:actual_end].hex()


def format_output(config: RNetConfig, show_raw: bool = False) -> str:
    """Format configuration for display"""
    lines = []

    lines.append("=" * 70)
    lines.append(f"R-NET CONFIGURATION: {config.filename}")
    lines.append("=" * 70)
    lines.append("")

    # Basic info
    lines.append("BASIC INFO")
    lines.append("-" * 40)
    lines.append(f"  File size:     {config.size} bytes")
    lines.append(f"  Serial:        {config.serial or 'N/A'}")
    lines.append(f"  Header magic:  {config.header_magic}")
    lines.append(f"  Checksum:      {config.checksum}")
    lines.append(f"  XOR patterns:  {config.xor_pattern_count}")
    lines.append("")

    # Mode profiles
    if config.mode_profiles:
        lines.append("MODE PROFILES")
        lines.append("-" * 40)
        for p in config.mode_profiles:
            lines.append(f"  {p.name:20} @ 0x{p.offset:04X}")
        lines.append("")

    # Speed profiles
    if config.speed_profiles:
        lines.append("SPEED PROFILES")
        lines.append("-" * 40)
        lines.append(f"  {'Name':<20} {'Fwd':>5} {'Rev':>5} {'Acc':>5} {'Dec':>5} {'Turn':>5}")
        lines.append(f"  {'-'*20} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
        for p in config.speed_profiles:
            lines.append(f"  {p.name:<20} {p.max_forward:>5} {p.max_reverse:>5} "
                        f"{p.acceleration:>5} {p.deceleration:>5} {p.turn_speed:>5}")
        lines.append("")

    # Motor settings
    if config.motor_settings.profile_limits:
        lines.append("MOTOR SETTINGS")
        lines.append("-" * 40)
        lines.append(f"  Base current:  {config.motor_settings.base_current}%")
        lines.append(f"  Max current:   {config.motor_settings.max_current}%")
        lines.append("")
        lines.append("  Profile current limits:")
        for idx, limit in sorted(config.motor_settings.profile_limits.items()):
            offset = RNetConfigParser.MOTOR_LIMIT_OFFSETS[idx] if idx < len(RNetConfigParser.MOTOR_LIMIT_OFFSETS) else 0
            lines.append(f"    Profile {idx+1}: {limit:3}%  (offset 0x{offset:04X})")
        lines.append("")

    # Seating functions
    if config.seating_functions:
        lines.append("SEATING FUNCTIONS")
        lines.append("-" * 40)
        for f in config.seating_functions:
            lines.append(f"  {f.name:16} @ 0x{f.offset:04X}  speed={f.speed}")
        lines.append("")

    # Raw sections
    if show_raw and config.raw_sections:
        lines.append("RAW SECTIONS")
        lines.append("-" * 40)
        for name, hex_data in config.raw_sections.items():
            lines.append(f"\n  [{name}]")
            # Format hex in rows of 32 chars (16 bytes)
            for i in range(0, min(len(hex_data), 128), 32):
                lines.append(f"    {hex_data[i:i+32]}")
        lines.append("")

    return '\n'.join(lines)


def compare_configs(config1: RNetConfig, config2: RNetConfig) -> str:
    """Compare two configurations and show differences"""
    lines = []

    lines.append("=" * 70)
    lines.append("CONFIGURATION COMPARISON")
    lines.append("=" * 70)
    lines.append(f"  File 1: {config1.filename} ({config1.size} bytes)")
    lines.append(f"  File 2: {config2.filename} ({config2.size} bytes)")
    lines.append("")

    # Compare speed profiles
    names1 = {p.name for p in config1.speed_profiles}
    names2 = {p.name for p in config2.speed_profiles}

    if names1 != names2:
        lines.append("SPEED PROFILE DIFFERENCES")
        lines.append("-" * 40)
        only1 = names1 - names2
        only2 = names2 - names1
        if only1:
            lines.append(f"  Only in {config1.filename}: {', '.join(only1)}")
        if only2:
            lines.append(f"  Only in {config2.filename}: {', '.join(only2)}")
        lines.append("")

    # Compare motor settings
    lines.append("MOTOR LIMIT COMPARISON")
    lines.append("-" * 40)
    lines.append(f"  {'Profile':<12} {config1.filename[:15]:<18} {config2.filename[:15]:<18} {'Change':<10}")
    lines.append(f"  {'-'*12} {'-'*18} {'-'*18} {'-'*10}")

    all_profiles = set(config1.motor_settings.profile_limits.keys()) | set(config2.motor_settings.profile_limits.keys())
    for idx in sorted(all_profiles):
        val1 = config1.motor_settings.profile_limits.get(idx, 0)
        val2 = config2.motor_settings.profile_limits.get(idx, 0)
        change = ""
        if val1 != val2:
            diff = val2 - val1
            change = f"{'+' if diff > 0 else ''}{diff}%"
        lines.append(f"  Profile {idx+1:<4} {val1:>5}%{'':<12} {val2:>5}%{'':<12} {change}")

    lines.append("")

    # Compare seating functions
    funcs1 = {f.name for f in config1.seating_functions}
    funcs2 = {f.name for f in config2.seating_functions}

    if funcs1 != funcs2:
        lines.append("SEATING FUNCTION DIFFERENCES")
        lines.append("-" * 40)
        only1 = funcs1 - funcs2
        only2 = funcs2 - funcs1
        if only1:
            lines.append(f"  Only in {config1.filename}: {', '.join(only1)}")
        if only2:
            lines.append(f"  Only in {config2.filename}: {', '.join(only2)}")
        lines.append("")

    return '\n'.join(lines)


def format_motor_focus(config: RNetConfig) -> str:
    """Format motor-focused output"""
    lines = []

    lines.append("=" * 70)
    lines.append(f"MOTOR SETTINGS: {config.filename}")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    ms = config.motor_settings
    lines.append(f"Base current limit:  {ms.base_current}%")
    lines.append(f"Max current limit:   {ms.max_current}%")
    lines.append("")

    # Per-profile limits
    lines.append("Profile Current Limits:")
    lines.append("-" * 40)
    for idx, limit in sorted(ms.profile_limits.items()):
        offset = RNetConfigParser.MOTOR_LIMIT_OFFSETS[idx] if idx < len(RNetConfigParser.MOTOR_LIMIT_OFFSETS) else 0
        bar = '█' * (limit // 5) + '░' * (20 - limit // 5)
        lines.append(f"  Profile {idx+1:2}: [{bar}] {limit:3}%  (0x{offset:04X})")
    lines.append("")

    # All motor-related values found
    if ms.raw_offsets:
        lines.append("All Motor Region Values (0x0600-0x0BC0):")
        lines.append("-" * 40)
        # Group by offset range
        ranges = [
            (0x0600, 0x0700, "Acceleration/Speed"),
            (0x0700, 0x0800, "Turning/Response"),
            (0x0B00, 0x0BC0, "Current Limits"),
        ]
        for start, end, desc in ranges:
            values_in_range = [(off, val) for off, val in ms.raw_offsets.items()
                              if start <= off < end and 40 <= val <= 100]
            if values_in_range:
                lines.append(f"\n  {desc} (0x{start:04X}-0x{end:04X}):")
                for off, val in sorted(values_in_range)[:10]:
                    lines.append(f"    0x{off:04X}: {val}%")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Parse R-Net configuration files (.R-net)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s config.R-net                    # Parse and display config
  %(prog)s config.R-net --json             # Output as JSON
  %(prog)s stock.R-net mod.R-net --diff    # Compare two configs
  %(prog)s config.R-net --motor            # Focus on motor settings
  %(prog)s config.R-net --raw              # Include raw hex sections
        """
    )

    parser.add_argument('files', nargs='+', help='R-net file(s) to parse')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--diff', '-d', action='store_true', help='Compare two files')
    parser.add_argument('--raw', '-r', action='store_true', help='Include raw hex sections')
    parser.add_argument('--motor', '-m', action='store_true', help='Focus on motor settings')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')

    args = parser.parse_args()

    # Validate files
    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

    # Parse files
    configs = []
    for filepath in args.files:
        parser_obj = RNetConfigParser(filepath)
        config = parser_obj.parse()
        configs.append(config)

    # Output
    if args.diff and len(configs) >= 2:
        print(compare_configs(configs[0], configs[1]))
    elif args.json:
        # Convert to JSON-serializable format
        output = []
        for config in configs:
            d = asdict(config)
            output.append(d)
        print(json.dumps(output[0] if len(output) == 1 else output, indent=2))
    elif args.motor:
        for config in configs:
            print(format_motor_focus(config))
    else:
        for config in configs:
            print(format_output(config, show_raw=args.raw))


if __name__ == '__main__':
    main()
