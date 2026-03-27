#!/usr/bin/env python3
"""
R-Net Self-Programmer - Adjust Your Own Wheelchair Settings
============================================================
User-friendly tool for wheelchair users to read, backup, and modify
their R-Net chair configuration via SocketCAN (Raspberry Pi + PiCAN2
or any Linux CAN adapter).

Protocol: POP (Parameter Object Protocol) on CAN IDs 0x78F / 0x793
Memory model: ODI EEPROM class (0x0100) - .R-net file offsets = live addresses
Source: DongleInterface.dll v3.0.0.0 reverse engineering, PG Drives Technology

Based on DEFCON24 research by Stephen Chavez & Specter.

Usage:
    python3 rnet_self_program.py                    # Interactive mode
    python3 rnet_self_program.py view               # View current settings
    python3 rnet_self_program.py backup -o save.bin  # Backup config
    python3 rnet_self_program.py restore save.bin    # Restore backup
    python3 rnet_self_program.py set motor_current_limit 80 --profile 1
"""

import sys
import os
import time
import signal
import atexit
import argparse
import json
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

# Import the CAN protocol layer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rnet_programmer import RNetProgrammer, POPCommand, ODIClass


# ============================================================================
# Safety and Parameter Definitions
# ============================================================================

class SafetyLevel(Enum):
    SAFE = "safe"           # Low risk: display settings, names
    CAUTION = "caution"     # Medium risk: speed, acceleration
    DANGER = "danger"       # High risk: motor current, safety limits

SAFETY_WARNINGS = {
    SafetyLevel.DANGER: (
        "  !! WARNING: This parameter affects safety-critical systems.\n"
        "  !! Incorrect values can cause motor damage, loss of control, or tipping.\n"
        "  !! Ensure the chair is on a test stand with wheels off the ground."
    ),
    SafetyLevel.CAUTION: (
        "  ! CAUTION: This parameter affects driving behavior.\n"
        "  ! Test changes carefully in a safe area."
    ),
}


class ParamType(Enum):
    UINT8 = 1       # Single byte, 0-255
    INT8 = 2        # Signed byte, -128 to 127
    UINT16_LE = 3   # 16-bit little-endian


@dataclass
class ParamDef:
    """Definition of a configurable parameter."""
    name: str               # Human-readable name
    address: int            # EEPROM base address
    param_type: ParamType   # Data type
    min_val: int            # Minimum allowed value
    max_val: int            # Maximum allowed value
    default_val: int        # Factory default (for reference)
    unit: str               # Display unit (%, etc.)
    safety: SafetyLevel     # Safety classification
    description: str        # Help text
    per_profile: bool = False    # True if per-profile parameter
    profile_stride: int = 0      # Address increment between profiles
    category: str = "general"    # Grouping category


# Motor current limit offsets (verified across 25 .R-net config files)
MOTOR_LIMIT_OFFSETS = [
    0x0B23, 0x0B30, 0x0B3D, 0x0B4A, 0x0B57, 0x0B64,
    0x0B71, 0x0B7E, 0x0B8B, 0x0B98, 0x0BA5, 0x0BB2
]

# Max speed CAN frame (0x0A040100#XX)
MAX_SPEED_ADDRESS = 0x0430  # Approximate EEPROM location for speed setting

# Speed profile discovery
SPEED_PREFIX = b'\x64\x64\x64\x64'  # 'dddd'
SPEED_REGION_START = 0x0250
SPEED_REGION_END = 0x0600
SPEED_PROFILE_SIZE = 24  # 4 prefix + 16 name + 4-8 config


# ============================================================================
# Parameter Registry
# ============================================================================

def _build_motor_params() -> Dict[str, ParamDef]:
    """Build motor current limit parameter definitions."""
    params = {}
    for idx, offset in enumerate(MOTOR_LIMIT_OFFSETS):
        profile_num = idx + 1
        key = f"motor_current_limit_p{profile_num}"
        params[key] = ParamDef(
            name=f"Motor Current Limit (Profile {profile_num})",
            address=offset,
            param_type=ParamType.UINT8,
            min_val=0,
            max_val=100,
            default_val=55,
            unit="%",
            safety=SafetyLevel.DANGER,
            description=(
                f"Maximum motor current for profile {profile_num}. "
                "Stock=55%. Values above 80% increase motor heat and wear."
            ),
            category="motor"
        )
    return params


PARAM_REGISTRY: Dict[str, ParamDef] = {
    **_build_motor_params(),
}


# ============================================================================
# Speed Profile Discovery
# ============================================================================

@dataclass
class SpeedProfile:
    """A discovered speed profile from live device."""
    name: str
    offset: int
    max_forward: int = 0
    max_reverse: int = 0
    acceleration: int = 0
    deceleration: int = 0
    turn_speed: int = 0
    raw_config: bytes = b''


def discover_profiles_from_data(data: bytes,
                                 region_start: int = SPEED_REGION_START
                                 ) -> List[SpeedProfile]:
    """Scan EEPROM data for speed profiles using dddd prefix pattern.
    Same detection logic as rnet_config_parser.py:_parse_speed_profiles.
    """
    profiles = []
    seen_names = set()

    end = min(len(data), SPEED_REGION_END - region_start)
    i = 0
    while i < end - 28:
        chunk = data[i:i + 28]

        if chunk[:4] == SPEED_PREFIX:
            name_raw = chunk[4:20]
            try:
                name = name_raw.decode('ascii', errors='ignore')
                name = ''.join(c if 32 <= ord(c) < 127 else '' for c in name).strip()
            except Exception:
                name = ''

            # Clean leading 'd' chars
            while name.startswith('d') and len(name) > 3:
                name = name[1:]

            # Skip noise
            is_noise = (
                not name or len(name) < 3 or
                all(c in 'dDxX-#0123456789 ' for c in name) or
                name.count('d') > len(name) // 2
            )

            if name and name not in seen_names and not is_noise:
                seen_names.add(name)
                config_bytes = chunk[20:28]
                profiles.append(SpeedProfile(
                    name=name,
                    offset=region_start + i,
                    max_forward=config_bytes[0] if len(config_bytes) > 0 else 0,
                    max_reverse=config_bytes[1] if len(config_bytes) > 1 else 0,
                    acceleration=config_bytes[2] if len(config_bytes) > 2 else 0,
                    deceleration=config_bytes[3] if len(config_bytes) > 3 else 0,
                    turn_speed=config_bytes[4] if len(config_bytes) > 4 else 0,
                    raw_config=bytes(config_bytes),
                ))
            i += SPEED_PROFILE_SIZE
        else:
            i += 1

    return profiles


# ============================================================================
# Live Config Reader
# ============================================================================

class LiveConfigReader:
    """Reads/writes named parameters from a live R-Net device."""

    def __init__(self, programmer: RNetProgrammer):
        self.programmer = programmer
        self._profiles: Optional[List[SpeedProfile]] = None

    def _safe_read(self, address: int, size: int) -> Optional[bytes]:
        """Read with heartbeat pause to avoid frame collision."""
        self.programmer._heartbeat_stop.set()
        time.sleep(0.05)
        try:
            return self.programmer.read_address(address, size)
        finally:
            self.programmer._heartbeat_stop.clear()

    def _safe_write(self, address: int, data: bytes) -> bool:
        """Write with heartbeat pause."""
        self.programmer._heartbeat_stop.set()
        time.sleep(0.05)
        try:
            return self.programmer.write_address(address, data)
        finally:
            self.programmer._heartbeat_stop.clear()

    def read_param(self, param_key: str) -> Optional[int]:
        """Read a named parameter from the live device."""
        pdef = PARAM_REGISTRY.get(param_key)
        if not pdef:
            return None

        size = 1 if pdef.param_type in (ParamType.UINT8, ParamType.INT8) else 2
        raw = self._safe_read(pdef.address, size)
        if raw is None:
            return None

        if pdef.param_type == ParamType.UINT8:
            return raw[0]
        elif pdef.param_type == ParamType.INT8:
            return raw[0] if raw[0] < 128 else raw[0] - 256
        elif pdef.param_type == ParamType.UINT16_LE:
            return raw[0] | (raw[1] << 8)
        return None

    def write_param(self, param_key: str, value: int) -> bool:
        """Write a named parameter to the live device."""
        pdef = PARAM_REGISTRY.get(param_key)
        if not pdef:
            return False

        if pdef.param_type in (ParamType.UINT8, ParamType.INT8):
            data = bytes([value & 0xFF])
        elif pdef.param_type == ParamType.UINT16_LE:
            data = bytes([value & 0xFF, (value >> 8) & 0xFF])
        else:
            return False

        return self._safe_write(pdef.address, data)

    def verify_write(self, param_key: str, expected: int) -> bool:
        """Read back a parameter and verify it matches expected value."""
        time.sleep(0.02)  # Brief delay for EEPROM commit
        actual = self.read_param(param_key)
        return actual == expected

    def read_all_motor_limits(self) -> Dict[int, Optional[int]]:
        """Read all motor current limits (12 profiles)."""
        results = {}
        for idx in range(len(MOTOR_LIMIT_OFFSETS)):
            key = f"motor_current_limit_p{idx + 1}"
            results[idx + 1] = self.read_param(key)
        return results

    def discover_profiles(self) -> List[SpeedProfile]:
        """Scan live device for speed profiles."""
        if self._profiles is not None:
            return self._profiles

        region_size = SPEED_REGION_END - SPEED_REGION_START
        data = self._safe_read(SPEED_REGION_START, region_size)
        if not data:
            self._profiles = []
            return self._profiles

        self._profiles = discover_profiles_from_data(data, SPEED_REGION_START)
        return self._profiles

    def read_speed_profile(self, profile: SpeedProfile) -> SpeedProfile:
        """Re-read a speed profile's config bytes from live device."""
        raw = self._safe_read(profile.offset + 20, 8)
        if raw:
            profile.max_forward = raw[0]
            profile.max_reverse = raw[1]
            profile.acceleration = raw[2]
            profile.deceleration = raw[3]
            profile.turn_speed = raw[4] if len(raw) > 4 else 0
            profile.raw_config = bytes(raw)
        return profile

    def read_region(self, start: int, length: int) -> Optional[bytes]:
        """Raw region read."""
        return self._safe_read(start, length)


# ============================================================================
# Backup Manager
# ============================================================================

class BackupManager:
    """Handles backup/restore of device configuration."""

    def __init__(self, reader: LiveConfigReader):
        self.reader = reader
        self._backup_created = False
        self._backup_file = ""

    def create_backup(self, filename: Optional[str] = None) -> str:
        """Dump config region (0x0000-0x1000) to a backup file."""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"rnet_backup_{timestamp}.bin"

        print(f"\n  Backing up configuration to {filename}...")
        data = self.reader.read_region(0x0000, 0x1000)
        if not data or len(data) < 0x0100:
            raise RuntimeError("Backup failed - insufficient data read from device")

        with open(filename, 'wb') as f:
            f.write(data)

        self._backup_created = True
        self._backup_file = filename
        print(f"  Backup saved: {filename} ({len(data)} bytes)")
        return filename

    def restore_backup(self, filename: str) -> bool:
        """Restore a backup file to the device."""
        if not os.path.exists(filename):
            print(f"  Error: File not found: {filename}")
            return False

        with open(filename, 'rb') as f:
            data = f.read()

        print(f"\n  Restore file: {filename} ({len(data)} bytes)")
        print("  This will OVERWRITE the current device configuration.")
        response = input("  Are you sure? Type 'RESTORE' to confirm: ")
        if response != 'RESTORE':
            print("  Restore cancelled.")
            return False

        # Write in 4-byte chunks (programmer protocol limitation)
        total = len(data)
        written = 0
        errors = 0

        print(f"  Writing {total} bytes...")
        for offset in range(0, total, 4):
            chunk = data[offset:offset + 4]
            if len(chunk) < 4:
                chunk = chunk.ljust(4, b'\x00')

            if not self.reader._safe_write(offset, chunk):
                errors += 1
                print(f"  Write error at 0x{offset:04X}")
                if errors > 10:
                    print("  Too many errors, aborting restore.")
                    return False

            written += len(chunk)
            if written % 256 == 0:
                pct = (written / total) * 100
                print(f"  [{pct:5.1f}%] 0x{offset:04X} / 0x{total:04X}", end='\r')

        print(f"\n  Restore complete: {written} bytes written, {errors} errors")
        return errors == 0

    @property
    def has_backup(self) -> bool:
        return self._backup_created

    def ensure_backup(self) -> str:
        """Ensure a backup exists before writing. Returns backup filename."""
        if self._backup_created:
            return self._backup_file
        print("\n  A backup is required before making any changes.")
        return self.create_backup()


# ============================================================================
# Safety Validator
# ============================================================================

class SafetyValidator:
    """Validates parameter changes and displays safety warnings."""

    @staticmethod
    def validate(param_key: str, value: int) -> Tuple[bool, str]:
        """Check if a value is within bounds."""
        pdef = PARAM_REGISTRY.get(param_key)
        if not pdef:
            return False, f"Unknown parameter: {param_key}"
        if value < pdef.min_val or value > pdef.max_val:
            return False, (
                f"Value {value} out of range "
                f"[{pdef.min_val}-{pdef.max_val}] {pdef.unit}"
            )
        return True, ""

    @staticmethod
    def confirm_change(param_key: str, old_val: int, new_val: int) -> bool:
        """Interactive confirmation with before/after display."""
        pdef = PARAM_REGISTRY[param_key]

        print(f"\n  {'=' * 50}")
        print(f"  PARAMETER CHANGE")
        print(f"  {'=' * 50}")
        print(f"  Parameter:  {pdef.name}")
        print(f"  Current:    {old_val} {pdef.unit}")
        print(f"  New:        {new_val} {pdef.unit}")
        print(f"  Default:    {pdef.default_val} {pdef.unit}")

        warning = SAFETY_WARNINGS.get(pdef.safety)
        if warning:
            print()
            print(warning)

        print()
        response = input("  Apply this change? [y/N]: ")
        return response.lower() == 'y'


# ============================================================================
# User Interface
# ============================================================================

class SelfProgrammerUI:
    """Interactive menu-driven interface for self-programming."""

    def __init__(self, interface: str = 'can0', verbose: bool = False):
        self.interface = interface
        self.verbose = verbose
        self.programmer: Optional[RNetProgrammer] = None
        self.reader: Optional[LiveConfigReader] = None
        self.backup_mgr: Optional[BackupManager] = None
        self.validator = SafetyValidator()
        self._running = False

    def _setup_signals(self):
        """Register signal handlers for clean shutdown."""
        def handler(sig, frame):
            print("\n\n  Interrupted - cleaning up...")
            self.cleanup()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        atexit.register(self.cleanup)

    def cleanup(self):
        """Stop heartbeat and close CAN socket."""
        if self.programmer:
            try:
                self.programmer.disconnect()
            except Exception:
                pass
            self.programmer = None

    def connect(self) -> bool:
        """Connect to the R-Net bus and enable programmer mode."""
        print(f"\n  Connecting to CAN bus ({self.interface})...")
        self.programmer = RNetProgrammer(
            interface=self.interface,
            verbose=self.verbose
        )

        if not self.programmer.connect():
            print("  Failed to connect to CAN bus.")
            print(f"  Make sure '{self.interface}' is up:")
            print(f"    sudo ip link set {self.interface} up type can bitrate 125000")
            return False

        print("  CAN bus connected.")
        print("  Enabling programmer mode...")

        if not self.programmer.enable_programmer_mode():
            print("  Failed to enable programmer mode.")
            print("  Is the wheelchair powered on?")
            self.programmer.disconnect()
            return False

        print("  Programmer mode active. Heartbeat running.")
        self.reader = LiveConfigReader(self.programmer)
        self.backup_mgr = BackupManager(self.reader)
        return True

    def run(self):
        """Main interactive loop."""
        self._setup_signals()

        print("=" * 56)
        print("  R-Net Self-Programmer v1.0")
        print("  For wheelchair users - adjust YOUR chair settings")
        print("=" * 56)

        if not self.connect():
            return

        self._running = True
        while self._running:
            self._main_menu()

        self.cleanup()
        print("\n  Goodbye.")

    def _main_menu(self):
        """Top-level menu."""
        print("\n  MAIN MENU")
        print("  " + "-" * 30)
        print("  1. View Current Settings")
        print("  2. Edit Motor Current Limits")
        print("  3. View Speed Profiles")
        print("  4. Backup Configuration")
        print("  5. Restore Configuration")
        print("  6. Raw Memory Read")
        print("  7. Exit")

        choice = input("\n  Choice [1-7]: ").strip()

        if choice == '1':
            self._view_settings()
        elif choice == '2':
            self._edit_motor_limits()
        elif choice == '3':
            self._view_speed_profiles()
        elif choice == '4':
            self._do_backup()
        elif choice == '5':
            self._do_restore()
        elif choice == '6':
            self._raw_read()
        elif choice == '7':
            self._running = False
        else:
            print("  Invalid choice.")

    def _view_settings(self):
        """Display all current settings."""
        print("\n  Reading current settings...")

        # Motor current limits
        limits = self.reader.read_all_motor_limits()
        print("\n  MOTOR CURRENT LIMITS")
        print("  " + "-" * 40)
        print(f"  {'Profile':<15} {'Current':>10} {'Stock':>10}")
        print("  " + "-" * 40)

        for profile_num, value in sorted(limits.items()):
            if value is not None:
                stock = 55
                marker = ""
                if value != stock:
                    marker = " <-- modified" if value > stock else " <-- reduced"
                bar = "#" * (value // 5)
                print(f"  Profile {profile_num:<6} {value:>8}% {stock:>8}%  |{bar}|{marker}")
            else:
                print(f"  Profile {profile_num:<6}    read error")

        # Speed profiles
        profiles = self.reader.discover_profiles()
        if profiles:
            print(f"\n  SPEED PROFILES ({len(profiles)} found)")
            print("  " + "-" * 50)
            print(f"  {'Name':<20} {'Fwd':>5} {'Rev':>5} {'Acc':>5} {'Dec':>5} {'Turn':>5}")
            print("  " + "-" * 50)
            for p in profiles:
                p = self.reader.read_speed_profile(p)
                print(f"  {p.name:<20} {p.max_forward:>5} {p.max_reverse:>5} "
                      f"{p.acceleration:>5} {p.deceleration:>5} {p.turn_speed:>5}")

    def _edit_motor_limits(self):
        """Edit motor current limits per profile."""
        print("\n  Reading motor current limits...")
        limits = self.reader.read_all_motor_limits()

        print("\n  MOTOR CURRENT LIMITS")
        print("  " + "-" * 40)
        for profile_num, value in sorted(limits.items()):
            if value is not None:
                print(f"  {profile_num:>2}. Profile {profile_num}: {value}%")

        print(f"  {len(limits) + 1:>2}. Set ALL profiles to same value")
        print("   0. Back")

        choice = input("\n  Select profile to edit [0-13]: ").strip()

        if choice == '0':
            return

        try:
            choice_num = int(choice)
        except ValueError:
            print("  Invalid choice.")
            return

        if choice_num == len(limits) + 1:
            # Set all profiles
            self._set_all_motor_limits(limits)
            return

        if choice_num < 1 or choice_num > len(limits):
            print("  Invalid profile number.")
            return

        key = f"motor_current_limit_p{choice_num}"
        old_val = limits.get(choice_num)
        if old_val is None:
            print("  Could not read current value.")
            return

        pdef = PARAM_REGISTRY[key]
        print(f"\n  Current Motor Current Limit (Profile {choice_num}): {old_val}%")
        print(f"  Range: {pdef.min_val}-{pdef.max_val}%")
        print(f"  Stock default: {pdef.default_val}%")
        print(f"\n{SAFETY_WARNINGS[SafetyLevel.DANGER]}")

        val_str = input(f"\n  New value (or Enter to cancel): ").strip()
        if not val_str:
            return

        try:
            new_val = int(val_str)
        except ValueError:
            print("  Invalid number.")
            return

        ok, msg = self.validator.validate(key, new_val)
        if not ok:
            print(f"  {msg}")
            return

        if not self.validator.confirm_change(key, old_val, new_val):
            print("  Change cancelled.")
            return

        # Ensure backup before first write
        try:
            self.backup_mgr.ensure_backup()
        except RuntimeError as e:
            print(f"  {e}")
            print("  Cannot proceed without backup.")
            return

        # Write
        print("  Writing...")
        if self.reader.write_param(key, new_val):
            if self.reader.verify_write(key, new_val):
                print(f"  Success: Profile {choice_num} motor current = {new_val}%")
            else:
                print("  WARNING: Write verification failed! Value may not have been saved.")
        else:
            print("  Write failed.")

    def _set_all_motor_limits(self, current_limits: Dict[int, Optional[int]]):
        """Set all motor current limits to the same value."""
        print(f"\n{SAFETY_WARNINGS[SafetyLevel.DANGER]}")
        val_str = input(f"\n  Set ALL profiles to what value? (0-100%, or Enter to cancel): ").strip()
        if not val_str:
            return

        try:
            new_val = int(val_str)
        except ValueError:
            print("  Invalid number.")
            return

        if new_val < 0 or new_val > 100:
            print("  Value must be 0-100%.")
            return

        # Show before/after for all
        print(f"\n  {'=' * 50}")
        print(f"  SET ALL MOTOR CURRENT LIMITS TO {new_val}%")
        print(f"  {'=' * 50}")
        for profile_num, old_val in sorted(current_limits.items()):
            if old_val is not None:
                change = "  (no change)" if old_val == new_val else f"  ({old_val}% -> {new_val}%)"
                print(f"  Profile {profile_num}: {change}")

        response = input(f"\n  Apply to ALL profiles? [y/N]: ").strip()
        if response.lower() != 'y':
            print("  Cancelled.")
            return

        # Ensure backup
        try:
            self.backup_mgr.ensure_backup()
        except RuntimeError as e:
            print(f"  {e}")
            return

        # Write all
        success = 0
        errors = 0
        for idx in range(len(MOTOR_LIMIT_OFFSETS)):
            key = f"motor_current_limit_p{idx + 1}"
            if self.reader.write_param(key, new_val):
                if self.reader.verify_write(key, new_val):
                    success += 1
                else:
                    errors += 1
                    print(f"  Profile {idx + 1}: verify failed")
            else:
                errors += 1
                print(f"  Profile {idx + 1}: write failed")

        print(f"\n  Done: {success} profiles updated, {errors} errors")

    def _view_speed_profiles(self):
        """View discovered speed profiles with details."""
        print("\n  Scanning for speed profiles...")
        profiles = self.reader.discover_profiles()

        if not profiles:
            print("  No speed profiles found in EEPROM region 0x0250-0x0600.")
            print("  This chair may use a different profile format.")
            return

        print(f"\n  SPEED PROFILES ({len(profiles)} found)")
        print("  " + "=" * 60)

        for i, p in enumerate(profiles):
            p = self.reader.read_speed_profile(p)
            print(f"\n  [{i + 1}] {p.name}")
            print(f"      Offset:       0x{p.offset:04X}")
            print(f"      Max Forward:  {p.max_forward}")
            print(f"      Max Reverse:  {p.max_reverse}")
            print(f"      Acceleration: {p.acceleration}")
            print(f"      Deceleration: {p.deceleration}")
            print(f"      Turn Speed:   {p.turn_speed}")
            print(f"      Raw config:   {p.raw_config.hex()}")

    def _do_backup(self):
        """Create a configuration backup."""
        filename = input("  Backup filename (Enter for auto): ").strip() or None
        try:
            self.backup_mgr.create_backup(filename)
        except RuntimeError as e:
            print(f"  Error: {e}")

    def _do_restore(self):
        """Restore from a backup file."""
        filename = input("  Backup file to restore: ").strip()
        if filename:
            self.backup_mgr.restore_backup(filename)

    def _raw_read(self):
        """Raw memory read for debugging."""
        addr_str = input("  Address (hex, e.g. 0x0B23): ").strip()
        size_str = input("  Size in bytes (default 16): ").strip() or "16"

        try:
            addr = int(addr_str, 0)
            size = int(size_str, 0)
        except ValueError:
            print("  Invalid address or size.")
            return

        if size > 256:
            print("  Maximum 256 bytes per read.")
            return

        print(f"\n  Reading {size} bytes from 0x{addr:04X}...")
        data = self.reader.read_region(addr, size)
        if not data:
            print("  Read failed.")
            return

        # Hex dump
        for offset in range(0, len(data), 16):
            row = data[offset:offset + 16]
            hex_part = ' '.join(f'{b:02X}' for b in row)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
            print(f"  {addr + offset:04X}: {hex_part:<48}  {ascii_part}")


# ============================================================================
# CLI Commands (Non-Interactive)
# ============================================================================

def cmd_view(args):
    """View current settings (non-interactive)."""
    prog = RNetProgrammer(interface=args.interface, verbose=args.verbose)
    if not prog.connect() or not prog.enable_programmer_mode():
        print("Failed to connect.")
        return 1

    reader = LiveConfigReader(prog)

    if args.json:
        result = {"motor_current_limits": {}, "speed_profiles": []}
        limits = reader.read_all_motor_limits()
        for k, v in limits.items():
            result["motor_current_limits"][f"profile_{k}"] = v

        profiles = reader.discover_profiles()
        for p in profiles:
            p = reader.read_speed_profile(p)
            result["speed_profiles"].append({
                "name": p.name, "offset": hex(p.offset),
                "max_forward": p.max_forward, "max_reverse": p.max_reverse,
                "acceleration": p.acceleration, "deceleration": p.deceleration,
                "turn_speed": p.turn_speed,
            })
        print(json.dumps(result, indent=2))
    else:
        ui = SelfProgrammerUI.__new__(SelfProgrammerUI)
        ui.reader = reader
        ui._view_settings()

    prog.disconnect()
    return 0


def cmd_backup(args):
    """Create backup (non-interactive)."""
    prog = RNetProgrammer(interface=args.interface, verbose=args.verbose)
    if not prog.connect() or not prog.enable_programmer_mode():
        print("Failed to connect.")
        return 1

    reader = LiveConfigReader(prog)
    mgr = BackupManager(reader)
    try:
        mgr.create_backup(args.output)
    except RuntimeError as e:
        print(f"Error: {e}")
        prog.disconnect()
        return 1

    prog.disconnect()
    return 0


def cmd_restore(args):
    """Restore from backup (non-interactive)."""
    prog = RNetProgrammer(interface=args.interface, verbose=args.verbose)
    if not prog.connect() or not prog.enable_programmer_mode():
        print("Failed to connect.")
        return 1

    reader = LiveConfigReader(prog)
    mgr = BackupManager(reader)
    result = mgr.restore_backup(args.file)
    prog.disconnect()
    return 0 if result else 1


def cmd_set(args):
    """Set a parameter (non-interactive)."""
    param_key = args.param
    value = args.value

    if param_key not in PARAM_REGISTRY:
        print(f"Unknown parameter: {param_key}")
        print("Available parameters:")
        for key in sorted(PARAM_REGISTRY.keys()):
            pdef = PARAM_REGISTRY[key]
            print(f"  {key:<35} {pdef.name} [{pdef.min_val}-{pdef.max_val}{pdef.unit}]")
        return 1

    ok, msg = SafetyValidator.validate(param_key, value)
    if not ok:
        print(f"Validation error: {msg}")
        return 1

    prog = RNetProgrammer(interface=args.interface, verbose=args.verbose)
    if not prog.connect() or not prog.enable_programmer_mode():
        print("Failed to connect.")
        return 1

    reader = LiveConfigReader(prog)

    # Read current value
    old_val = reader.read_param(param_key)
    if old_val is None:
        print("Failed to read current value.")
        prog.disconnect()
        return 1

    pdef = PARAM_REGISTRY[param_key]
    if not args.force:
        if not SafetyValidator.confirm_change(param_key, old_val, value):
            print("Cancelled.")
            prog.disconnect()
            return 0

    # Backup first
    mgr = BackupManager(reader)
    try:
        mgr.ensure_backup()
    except RuntimeError as e:
        print(f"Backup failed: {e}")
        prog.disconnect()
        return 1

    # Write
    if reader.write_param(param_key, value):
        if reader.verify_write(param_key, value):
            print(f"Success: {pdef.name} = {value}{pdef.unit}")
        else:
            print("WARNING: Write verification failed!")
    else:
        print("Write failed.")

    prog.disconnect()
    return 0


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="R-Net Self-Programmer - Adjust your wheelchair settings",
        epilog=(
            "POP Protocol (Parameter Object Protocol)\n"
            "  Reads/writes EEPROM via CAN IDs 0x78F/0x793\n"
            "  Source: DongleInterface.dll v3.0.0.0 RE\n"
            "\n"
            "Safety: Always backup before making changes.\n"
            "        Test with wheels off the ground.\n"
            "        Have a spotter present.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-i', '--interface', default='can0',
                        help='CAN interface (default: can0)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show CAN frame debug output')

    subparsers = parser.add_subparsers(dest='command')

    # Interactive mode (default - no subcommand)

    p_view = subparsers.add_parser('view', help='View current settings')
    p_view.add_argument('--json', action='store_true',
                        help='Output as JSON')

    p_backup = subparsers.add_parser('backup', help='Backup configuration')
    p_backup.add_argument('-o', '--output', required=True,
                          help='Output filename')

    p_restore = subparsers.add_parser('restore', help='Restore from backup')
    p_restore.add_argument('file', help='Backup file to restore')

    p_set = subparsers.add_parser('set', help='Set a parameter value')
    p_set.add_argument('param', help='Parameter key (e.g. motor_current_limit_p1)')
    p_set.add_argument('value', type=int, help='New value')
    p_set.add_argument('--force', action='store_true',
                        help='Skip confirmation prompt')

    p_params = subparsers.add_parser('params', help='List available parameters')

    args = parser.parse_args()

    if args.command == 'view':
        sys.exit(cmd_view(args))
    elif args.command == 'backup':
        sys.exit(cmd_backup(args))
    elif args.command == 'restore':
        sys.exit(cmd_restore(args))
    elif args.command == 'set':
        sys.exit(cmd_set(args))
    elif args.command == 'params':
        print("Available parameters:")
        print(f"  {'Key':<35} {'Name':<35} {'Range':<15} {'Safety'}")
        print("  " + "-" * 90)
        for key in sorted(PARAM_REGISTRY.keys()):
            pdef = PARAM_REGISTRY[key]
            rng = f"{pdef.min_val}-{pdef.max_val}{pdef.unit}"
            print(f"  {key:<35} {pdef.name:<35} {rng:<15} {pdef.safety.value}")
    else:
        # Default: interactive mode
        ui = SelfProgrammerUI(
            interface=args.interface,
            verbose=args.verbose,
        )
        ui.run()


if __name__ == '__main__':
    main()
