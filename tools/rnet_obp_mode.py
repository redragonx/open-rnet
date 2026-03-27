#!/usr/bin/env python3
"""
R-Net OBP (On-Board Programming) Mode Tool
=============================================
Monitors and interacts with the R-Net OBP parameter exchange protocol.

OBP is the wheelchair's built-in programming mode, activated by the USER
through a button sequence on the JSM. It uses the standard parameter
exchange protocol (0x78X/0x79X) — NOT the POP programmer protocol
(0x78F/0x793) used by external dongle tools. See rnet_pop_shell.py or
rnet_programmer.py for the dongle-based approach.

How to enter OBP mode (requires "OBP Keycode Entry" = Yes):
  1. Hold Horn, then also hold On/Off until a short bleep
  2. Release Horn, keep holding On/Off through two more bleeps
  3. Release On/Off — a longer bleep confirms OBP mode is active

In OBP mode:
  - JSM display shows the parameter menu tree
  - Joystick forward/back = navigate parameters
  - Joystick left = go back / show full name
  - Speed Up/Down buttons = adjust selected parameter value
  - Driving is DISABLED (joystick repurposed for navigation)
  - Mode 8 is reserved for OBP
  - 5 minute inactivity timeout exits OBP

CAN bus behavior in OBP:
  - JSM sends parameter requests on 0x781 (slot 1)
  - PM responds on 0x790 (slot 0)
  - Joystick position frames (0x02000X00) STOP
  - Normal heartbeats (0x00E, 0x03C30F0F) continue

This tool can:
  - Monitor OBP parameter exchange traffic in real time
  - Decode parameter read/write frames
  - Read parameters by register/pointer ID (78X/79X protocol)
  - Write parameter values

Author: Stephen Chavez & Specter
Source: R-Net OBP Manual SK78571/4, DEFCON24 research,
        DongleInterface.dll v3.0.0.0 (PG Drives Technology)
"""

import argparse
import sys
import time
import threading
from typing import Optional
from dataclasses import dataclass

try:
    import can
    HAS_CAN = True
except ImportError:
    HAS_CAN = False
    print("[!] python-can not installed. Install with: pip install python-can")


# =============================================================================
# Parameter Exchange Protocol Constants
# =============================================================================

# Frame ID assignment: 0x780+slot (request), 0x790+slot (response)
# In OBP, the JSM (slot 1) talks to the PM (slot 0):
#   JSM request:  0x781
#   PM response:  0x790
# We can also send requests from an unused slot.

PARAM_REQ_BASE = 0x780     # + slot number
PARAM_RSP_BASE = 0x790     # + slot number

# Device slots
SLOT_PM = 0                # Power Module
SLOT_JSM = 1               # Joystick Module
SLOT_ICS_PROG = 0xF        # ICS Programmer

# Command bytes (byte 0 of parameter exchange frames)
CMD_OPEN = 0x20            # Open parameter page / check pointer exists
CMD_REQUEST = 0x40         # Request data at pointer
CMD_ACK = 0x41             # Acknowledge / pointer exists
CMD_DATA = 0x21            # Data response with value
CMD_ERROR = 0xC1           # Error response
CMD_CLOSE = 0x80           # Close parameter page (byte 0 of close frame)

# Register types (byte 1)
REG_PAGE = 0x80            # Page 0 access
REG_POINTER = 0x81         # Pointer/sub-pointer check
REG_DATA = 0x8F            # Data read/write
REG_TEXT = 0x8C            # Text display data (cJSM)

# Timing
PARAM_TIMEOUT = 0.5        # Parameter exchange timeout
INTER_FRAME_DELAY = 0.005  # 5ms between frames (parameter exchange is slower)
POP_HEARTBEAT_INTERVAL = 0.2  # 200ms POP heartbeat for enable mode

# Mode change frames (0x061)
# Pattern: 061#404X0000 (request, X=current mode), 061#004Y0000 (switch to mode Y)
# Mode number encoded in low nibble of byte 1: 0x40=mode0, 0x41=mode1, ..., 0x48=mode8
MODE_CHANGE_ID = 0x061
OBP_MODE_NUMBER = 8        # Mode 8 is reserved for OBP

# POP Programmer protocol constants (for enabling OBP Keycode Entry)
POP_ANNOUNCE_ID = 0x7A0
POP_REQUEST_ID = 0x78F
POP_RESPONSE_ID = 0x793
POP_CMD_HEARTBEAT = 0x42
POP_CMD_SET_ADDR = 0x83
POP_CMD_READ = 0x03
POP_CMD_WRITE = 0x43
POP_RSP_ACK = 0x2F
POP_RSP_READ = 0x4F
POP_RSP_WRITE = 0x0F
POP_RSP_COMPLETE = 0x8F
POP_RSP_ERROR = 0xC1
POP_READ_MODE = 0x17

# Known OBP parameter categories (from R-Net OBP Manual SK78571/4)
OBP_MENU = {
    'speeds': {
        'name': 'Speeds',
        'params': {
            (0x06, 0x01): 'Forward Speed',
            (0x06, 0x02): 'Forward Speed Minimum',
            (0x07, 0x01): 'Reverse Speed',
            (0x07, 0x02): 'Reverse Speed Minimum',
            (0x08, 0x01): 'Turn Speed',
            (0x08, 0x02): 'Turn Speed Minimum',
        }
    },
    'forward': {
        'name': 'Forward',
        'params': {
            (0x09, 0x01): 'Forward Acceleration',
            (0x09, 0x02): 'Forward Acceleration Minimum',
            (0x0A, 0x01): 'Forward Deceleration',
            (0x0A, 0x02): 'Forward Deceleration Minimum',
        }
    },
    'reverse': {
        'name': 'Reverse',
        'params': {
            (0x0B, 0x01): 'Reverse Acceleration',
            (0x0B, 0x02): 'Reverse Acceleration Minimum',
            (0x0C, 0x01): 'Reverse Deceleration',
            (0x0C, 0x02): 'Reverse Deceleration Minimum',
        }
    },
    'turn': {
        'name': 'Turn',
        'params': {
            (0x0D, 0x01): 'Turn Acceleration',
            (0x0D, 0x02): 'Turn Acceleration Minimum',
            (0x0E, 0x01): 'Turn Deceleration',
            (0x0E, 0x02): 'Turn Deceleration Minimum',
        }
    },
    'drive': {
        'name': 'Drive',
        'params': {
            (0x10, 0x01): 'Power',
            (0x11, 0x01): 'Torque',
            (0x12, 0x01): 'Tremor Damping',
        }
    },
    'controls': {
        'name': 'Controls',
        'params': {
            (0x14, 0x01): 'Short Throw',
            (0x15, 0x01): 'Deadband',
        }
    },
    'standby': {
        'name': 'Standby',
        'params': {
            (0x20, 0x01): 'Sleep Timer',
        }
    },
}

# Flat lookup: (pointer, sub) -> name
PARAM_NAMES = {}
for cat in OBP_MENU.values():
    PARAM_NAMES.update(cat['params'])


# =============================================================================
# Frame Decoder
# =============================================================================

def decode_param_frame(arb_id: int, data: bytes) -> str:
    """Decode a parameter exchange frame to human-readable string."""
    if len(data) < 4:
        return f"(short frame: {data.hex()})"

    is_request = (arb_id & 0xFF0) == PARAM_REQ_BASE
    slot = arb_id & 0x0F
    direction = "REQ" if is_request else "RSP"

    cmd = data[0]
    reg = data[1]
    param_bytes = data[4:8] if len(data) >= 8 else data[4:]

    cmd_names = {
        CMD_OPEN: "OPEN", CMD_REQUEST: "REQUEST", CMD_ACK: "ACK",
        CMD_DATA: "DATA", CMD_ERROR: "ERROR", CMD_CLOSE: "CLOSE",
    }
    reg_names = {
        REG_PAGE: "PAGE", REG_POINTER: "PTR", REG_DATA: "DATA", REG_TEXT: "TEXT",
    }

    cmd_str = cmd_names.get(cmd, f"0x{cmd:02X}")
    reg_str = reg_names.get(reg, f"0x{reg:02X}")

    # Try to decode parameter name
    param_info = ""
    if reg == REG_POINTER and len(data) >= 8:
        ptr = data[4]
        sub = data[6] if len(data) > 6 else 0
        name = PARAM_NAMES.get((ptr, sub), "")
        if name:
            param_info = f" [{name}]"
        else:
            param_info = f" [ptr=0x{ptr:02X} sub=0x{sub:02X}]"
    elif reg == REG_DATA and cmd == CMD_DATA and len(data) >= 6:
        val = int.from_bytes(data[4:8], 'little')
        param_info = f" = {val} (0x{val:04X})"
    elif reg == REG_DATA and cmd == CMD_REQUEST:
        param_info = " (read value)"

    return f"slot{slot} {direction} {cmd_str}/{reg_str}{param_info}"


# =============================================================================
# OBP Mode Controller
# =============================================================================

@dataclass
class OBPState:
    connected: bool = False
    obp_active: bool = False
    last_param_time: float = 0
    params_read: int = 0
    params_written: int = 0
    errors: int = 0


class RNetOBPMode:
    """
    R-Net OBP (On-Board Programming) mode controller.

    Monitors and interacts with the parameter exchange protocol
    used by the JSM during OBP mode (0x78X/0x79X frames).

    Unlike the POP programmer protocol (rnet_programmer.py), OBP uses
    the standard parameter exchange that all R-Net devices use for
    inter-device configuration.
    """

    def __init__(self, interface: str = "can0", verbose: bool = False,
                 slot: int = SLOT_JSM):
        self.interface = interface
        self.verbose = verbose
        self.slot = slot  # Which slot to send requests FROM
        self.target_slot = SLOT_PM  # Which slot to query (PM by default)
        self.state = OBPState()
        self.bus: Optional[can.Bus] = None
        self.lock = threading.Lock()

    @property
    def req_id(self) -> int:
        """Request frame ID for our slot."""
        return PARAM_REQ_BASE + self.slot

    @property
    def rsp_id(self) -> int:
        """Response frame ID from target slot."""
        return PARAM_RSP_BASE + self.target_slot

    def log(self, msg: str, level: str = "INFO"):
        if self.verbose or level in ("ERROR", "WARN"):
            prefix = {"INFO": "[*]", "OK": "[+]", "ERROR": "[-]", "WARN": "[!]", "DEBUG": "[.]"}
            print(f"{prefix.get(level, '[*]')} {msg}")

    def connect(self) -> bool:
        if not HAS_CAN:
            self.log("python-can not available", "ERROR")
            return False
        try:
            self.bus = can.Bus(channel=self.interface, bustype='socketcan')
            self.log(f"Connected to {self.interface}", "OK")
            self.state.connected = True
            return True
        except Exception as e:
            self.log(f"Failed to connect: {e}", "ERROR")
            return False

    def disconnect(self):
        if self.bus:
            self.bus.shutdown()
            self.bus = None
        self.state.connected = False

    def send_frame(self, arb_id: int, data: bytes) -> bool:
        if not self.bus:
            return False
        try:
            msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
            self.bus.send(msg)
            if self.verbose:
                self.log(f"TX: {arb_id:03X}#{data.hex().upper()}", "DEBUG")
            return True
        except Exception as e:
            self.log(f"Send failed: {e}", "ERROR")
            return False

    def recv_frame(self, timeout: float = PARAM_TIMEOUT,
                   filter_id: Optional[int] = None) -> Optional[can.Message]:
        if not self.bus:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.bus.recv(timeout=0.05)
                if msg and (filter_id is None or msg.arbitration_id == filter_id):
                    if self.verbose:
                        self.log(f"RX: {msg.arbitration_id:03X}#{msg.data.hex().upper()}", "DEBUG")
                    return msg
            except Exception:
                pass
        return None

    # =========================================================================
    # Parameter Exchange Operations
    # =========================================================================

    def check_pointer(self, pointer: int, sub: int = 0x01) -> bool:
        """
        Check if a parameter pointer exists on the target device.

        Sends: OPEN/PTR with pointer and sub-pointer
        Expects: ACK/PTR if exists, ERROR if not
        """
        # Frame: [CMD_OPEN][REG_POINTER][0x00][0x00][pointer][0x00][sub][0x00]
        data = bytes([CMD_OPEN, REG_POINTER, 0x00, 0x00, pointer, 0x00, sub, 0x00])

        with self.lock:
            self.send_frame(self.req_id, data)
            time.sleep(INTER_FRAME_DELAY)

            response = self.recv_frame(timeout=PARAM_TIMEOUT, filter_id=self.rsp_id)
            if response and len(response.data) >= 1:
                if response.data[0] == CMD_ACK:
                    return True
                elif response.data[0] == CMD_ERROR:
                    return False

        return False

    def read_param(self, pointer: int, sub: int = 0x01) -> Optional[int]:
        """
        Read a parameter value by pointer/sub-pointer.

        Protocol:
          1. OPEN/PTR — check pointer exists
          2. REQUEST/DATA — request the value
          3. DATA/DATA — response with value (bytes 4-7, little-endian)

        Returns parameter value as int, or None on failure.
        """
        # Step 1: Check pointer exists
        open_data = bytes([CMD_OPEN, REG_POINTER, 0x00, 0x00, pointer, 0x00, sub, 0x00])

        with self.lock:
            self.send_frame(self.req_id, open_data)
            time.sleep(INTER_FRAME_DELAY)

            ack = self.recv_frame(timeout=PARAM_TIMEOUT, filter_id=self.rsp_id)
            if not ack or ack.data[0] != CMD_ACK:
                name = PARAM_NAMES.get((pointer, sub), f"ptr=0x{pointer:02X}")
                self.log(f"Parameter not found: {name}", "WARN")
                self.state.errors += 1
                return None

            # Step 2: Request value
            req_data = bytes([CMD_REQUEST, REG_DATA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.send_frame(self.req_id, req_data)
            time.sleep(INTER_FRAME_DELAY)

            # Step 3: Read response
            rsp = self.recv_frame(timeout=PARAM_TIMEOUT, filter_id=self.rsp_id)
            if rsp and len(rsp.data) >= 8 and rsp.data[0] == CMD_DATA:
                value = int.from_bytes(rsp.data[4:8], 'little')
                self.state.params_read += 1
                self.state.last_param_time = time.time()
                return value

        self.state.errors += 1
        return None

    def write_param(self, pointer: int, sub: int, value: int) -> bool:
        """
        Write a parameter value.

        Protocol:
          1. OPEN/PTR — check pointer exists
          2. DATA/DATA — send new value
          3. ACK — confirmation
        """
        # Step 1: Check pointer
        open_data = bytes([CMD_OPEN, REG_POINTER, 0x00, 0x00, pointer, 0x00, sub, 0x00])

        with self.lock:
            self.send_frame(self.req_id, open_data)
            time.sleep(INTER_FRAME_DELAY)

            ack = self.recv_frame(timeout=PARAM_TIMEOUT, filter_id=self.rsp_id)
            if not ack or ack.data[0] != CMD_ACK:
                self.log(f"Parameter not found: ptr=0x{pointer:02X} sub=0x{sub:02X}", "WARN")
                return False

            # Step 2: Write value
            val_bytes = value.to_bytes(4, 'little')
            write_data = bytes([CMD_DATA, REG_DATA, 0x00, 0x00]) + val_bytes
            self.send_frame(self.req_id, write_data)
            time.sleep(INTER_FRAME_DELAY)

            # Step 3: Wait for ACK
            rsp = self.recv_frame(timeout=PARAM_TIMEOUT, filter_id=self.rsp_id)
            if rsp and rsp.data[0] == CMD_ACK:
                self.state.params_written += 1
                self.state.last_param_time = time.time()
                return True

        self.state.errors += 1
        return False

    # =========================================================================
    # OBP Enable / Force Entry
    # =========================================================================

    def _pop_send(self, data: bytes) -> bool:
        """Send a POP programmer frame on 0x78F."""
        return self.send_frame(POP_REQUEST_ID, data)

    def _pop_recv(self, timeout: float = 0.5) -> Optional[bytes]:
        """Receive a POP response frame from 0x793."""
        msg = self.recv_frame(timeout=timeout, filter_id=POP_RESPONSE_ID)
        if msg and msg.data:
            return bytes(msg.data)
        return None

    def _pop_handshake(self) -> bool:
        """Enter POP programmer mode (dongle emulation).

        Sends 0x7A0 announce + 0x78F heartbeat, waits for 0x793 ACK.
        This is needed to write OEM-level parameters like OBP Keycode Entry.
        """
        # Announce presence
        self.send_frame(POP_ANNOUNCE_ID, b'')
        time.sleep(0.1)

        # Send heartbeat, wait for ACK
        hb = bytes([POP_CMD_HEARTBEAT, 0x20, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00])
        for attempt in range(3):
            self._pop_send(hb)
            rsp = self._pop_recv(timeout=0.5)
            if rsp and rsp[0] == POP_RSP_ACK:
                return True
            time.sleep(0.2)
        return False

    def _pop_read(self, address: int) -> Optional[bytes]:
        """Read 4 bytes from EEPROM via POP Quick protocol."""
        addr_lo = address & 0xFF
        addr_hi = (address >> 8) & 0xFF

        # Set address: 78F#830001FF[addr_lo][addr_hi]0000
        self._pop_send(bytes([POP_CMD_SET_ADDR, 0x00, 0x01, 0xFF,
                              addr_lo, addr_hi, 0x00, 0x00]))
        time.sleep(0.002)

        # Start read: 78F#030001FF17000000
        self._pop_send(bytes([POP_CMD_READ, 0x00, 0x01, 0xFF,
                              POP_READ_MODE, 0x00, 0x00, 0x00]))

        rsp = self._pop_recv(timeout=0.5)
        if rsp and len(rsp) >= 8 and rsp[0] == POP_RSP_READ:
            self._pop_recv(timeout=0.2)  # COMPLETE
            return bytes(rsp[4:8])
        return None

    def _pop_write(self, address: int, data: bytes) -> bool:
        """Write up to 4 bytes to EEPROM via POP Quick protocol."""
        addr_lo = address & 0xFF
        addr_hi = (address >> 8) & 0xFF
        write_data = data[:4].ljust(4, b'\x00')

        # Set address
        self._pop_send(bytes([POP_CMD_SET_ADDR, 0x00, 0x01, 0xFF,
                              addr_lo, addr_hi, 0x00, 0x00]))
        time.sleep(0.002)

        # Write data: 78F#430001FF[4 bytes]
        self._pop_send(bytes([POP_CMD_WRITE, 0x00, 0x01, 0xFF]) + write_data)

        rsp = self._pop_recv(timeout=0.5)
        if rsp and rsp[0] == POP_RSP_WRITE:
            self._pop_recv(timeout=0.2)  # COMPLETE
            return True
        return False

    def _pop_heartbeat_once(self):
        """Send a single POP heartbeat to keep programmer session alive."""
        hb = bytes([POP_CMD_HEARTBEAT, 0x20, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00])
        self._pop_send(hb)
        self._pop_recv(timeout=0.2)

    def force_mode_change(self, target_mode: int = OBP_MODE_NUMBER,
                          current_mode: int = 0) -> bool:
        """
        Force a mode change via 0x061 mode change frames.

        R-Net mode change sequence (from captured traffic):
          061#40[0x40+current]0000  — request mode change
          061#00[0x40+target]0000   — switch to target mode

        Mode 8 is reserved for OBP. This bypasses the JSM UI.
        Non-destructive: does not write to EEPROM.
        """
        current_byte = 0x40 + current_mode
        target_byte = 0x40 + target_mode

        print(f"  Sending mode change: mode {current_mode} -> mode {target_mode} (OBP)...")
        self.send_frame(MODE_CHANGE_ID, bytes([0x40, current_byte, 0x00, 0x00]))
        time.sleep(0.1)
        self.send_frame(MODE_CHANGE_ID, bytes([0x00, target_byte, 0x00, 0x00]))
        time.sleep(0.2)

        # Check if parameter exchange starts (sign OBP activated)
        print("  Listening for parameter exchange activity...")
        deadline = time.time() + 3.0
        while time.time() < deadline:
            msg = self.recv_frame(timeout=0.1)
            if msg and 0x780 <= msg.arbitration_id <= 0x79F:
                print("  [+] Parameter exchange detected — OBP mode appears active!")
                self.state.obp_active = True
                return True

        print("  [!] No parameter exchange detected")
        return False

    # --- POP-based config backup/restore ---

    def _pop_dump_region(self, start: int, end: int,
                         label: str = "") -> Optional[bytearray]:
        """Dump an EEPROM region via POP. Returns bytes or None."""
        size = end - start
        result = bytearray()
        if label:
            print(f"  Reading {label} (0x{start:04X}-0x{end:04X}, {size} bytes)...")

        for addr in range(start, end, 4):
            if (addr - start) % 64 == 0:
                self._pop_heartbeat_once()
                if label:
                    pct = 100 * (addr - start) / size
                    print(f"\r  Reading {label}... {pct:.0f}%", end="", flush=True)

            chunk = self._pop_read(addr)
            if chunk:
                result.extend(chunk[:min(4, end - addr)])
            else:
                result.extend(b'\xFF' * min(4, end - addr))

        if label:
            print(f"\r  Reading {label}... done ({len(result)} bytes)")
        return result

    def backup_config(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Backup system config region to a file before making changes.

        Dumps 0x0000-0x1000 (4 KB) which covers headers, keys, and config.
        Returns the filename used, or None on failure.
        """
        if filename is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"obp_backup_{ts}.bin"

        print(f"\n  Backing up config to {filename}...")

        if not self._pop_handshake():
            print("  [-] Failed to enter POP programmer mode for backup")
            return None

        data = self._pop_dump_region(0x0000, 0x1000, "config backup")
        if data and len(data) > 0:
            with open(filename, 'wb') as f:
                f.write(data)
            print(f"  [+] Backup saved: {filename} ({len(data)} bytes)")
            return filename
        else:
            print("  [-] Backup failed")
            return None

    def enable_obp_at_address(self, address: int, value: int = 0x01,
                              skip_backup: bool = False) -> bool:
        """
        Write a specific EEPROM address to enable OBP via POP protocol.

        Safe mode (default): backs up config first, reads current value,
        shows what will change, writes, verifies read-back.

        Args:
            address: EEPROM address of OBP Keycode Entry parameter.
            value: Value to write (0x01 = enabled).
            skip_backup: Skip the backup step (advanced mode).
        """
        if not self._pop_handshake():
            print("  [-] Failed to enter POP programmer mode")
            return False

        print("  [+] POP programmer mode active")

        # Backup first (unless skipped)
        if not skip_backup:
            backup_file = self.backup_config()
            if not backup_file:
                print("  [-] Backup failed — aborting for safety")
                print("      Use advanced mode (--advanced) to skip backup")
                return False
            # Re-handshake after backup (session may have timed out)
            self._pop_handshake()

        # Read current value
        current = self._pop_read(address)
        if current:
            print(f"  Current value at 0x{address:04X}: {current.hex().upper()}")
            if current[0] == value:
                print(f"  [+] Already set to 0x{value:02X} — OBP should be enabled!")
                print("      Try the button combo: Horn + On/Off through the bleeps")
                return True
        else:
            print(f"  [!] Could not read 0x{address:04X} — continuing anyway")

        # Write
        print(f"  Writing 0x{value:02X} to 0x{address:04X}...")
        if not self._pop_write(address, bytes([value])):
            print("  [-] Write failed")
            return False

        # Verify
        self._pop_heartbeat_once()
        verify = self._pop_read(address)
        if verify and verify[0] == value:
            print(f"  [+] Verified: 0x{address:04X} = 0x{value:02X}")
        else:
            print(f"  [!] Verify read-back mismatch — check manually")

        print()
        print("  [+] OBP Keycode Entry should now be enabled!")
        print("      Power cycle the chair, then enter OBP:")
        print("      1. Hold Horn + On/Off → wait for short bleep")
        print("      2. Release Horn, keep On/Off → two more bleeps")
        print("      3. Release On/Off → long bleep = OBP active")
        return True

    def enable_obp_safe(self) -> bool:
        """
        SAFE MODE: Guided OBP enable with backup and step-by-step prompts.

        Steps:
          1. Try non-destructive mode change (no EEPROM writes)
          2. If that fails, enter POP programmer mode
          3. Backup the entire config region to a file
          4. Dump the system config area for the user to inspect
          5. Provide clear instructions for identifying the OBP byte
          6. Optionally write with verification
        """
        print("=" * 60)
        print("  OBP Enable — Safe Mode")
        print("=" * 60)
        print()
        print("  This will try to enable OBP (On-Board Programming) mode")
        print("  on your R-Net wheelchair. It uses two approaches:")
        print()
        print("  Step 1: Non-destructive mode change (safe, no EEPROM writes)")
        print("  Step 2: If needed, POP protocol to enable OBP in EEPROM")
        print("          (creates a backup FIRST, then writes with verify)")
        print()

        # --- Step 1: Try mode change ---
        print("─" * 60)
        print("  STEP 1: Trying mode change to mode 8 (OBP)...")
        print("─" * 60)
        print("  This sends CAN frames to switch modes. No EEPROM changes.")
        print()

        if self.force_mode_change(OBP_MODE_NUMBER):
            print()
            print("  OBP activated via mode change! No EEPROM writes needed.")
            return True

        print()
        print("  Mode change didn't activate OBP.")
        print("  This usually means OBP Keycode Entry is disabled in EEPROM.")
        print()

        # --- Step 2: POP programmer approach ---
        print("─" * 60)
        print("  STEP 2: Entering POP programmer mode...")
        print("─" * 60)
        print("  This emulates the R-Net programmer dongle to read/write EEPROM.")
        print()

        if not self._pop_handshake():
            print("  [-] Failed to connect via POP protocol.")
            print()
            print("  Troubleshooting:")
            print("    - Is the chair powered on?")
            print("    - Is the CAN interface up? (ip link set can0 up type can bitrate 125000)")
            print("    - Are the CAN wires connected correctly? (pin 1=CAN Lo, pin 2=CAN Hi)")
            return False

        print("  [+] Connected to R-Net bus via POP protocol")
        print()

        # --- Step 2a: Backup ---
        print("─" * 60)
        print("  STEP 2a: Creating config backup...")
        print("─" * 60)
        print("  Backing up 0x0000-0x1000 (4 KB) before any changes.")
        print()

        backup_file = self.backup_config()
        if not backup_file:
            print("  [-] Could not create backup. Aborting for safety.")
            print("      Fix the connection and try again.")
            return False

        print()

        # --- Step 2b: Dump system config for inspection ---
        print("─" * 60)
        print("  STEP 2b: Reading system config region...")
        print("─" * 60)
        self._pop_handshake()  # refresh session

        sys_data = self._pop_dump_region(0x0400, 0x0600, "system config")
        if not sys_data:
            print("  [-] Could not read system config")
            return False

        # Save the dump for reference
        sys_file = backup_file.replace('.bin', '_syscfg.bin')
        with open(sys_file, 'wb') as f:
            f.write(sys_data)
        print(f"  Saved system config dump: {sys_file}")

        # Show hex dump of first 128 bytes for inspection
        print()
        print("  System config region (0x0400-0x0480):")
        for i in range(0, min(128, len(sys_data)), 16):
            chunk = sys_data[i:i + 16]
            hex_p = ' '.join(f'{b:02X}' for b in chunk)
            asc_p = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"    {0x0400 + i:04X}: {hex_p:<48}  {asc_p}")

        print()
        print("─" * 60)
        print("  STEP 2c: What to do next")
        print("─" * 60)
        print()
        print("  The OBP Keycode Entry parameter is a single byte somewhere")
        print("  in the system config (0x0400-0x0600). Its exact address")
        print("  varies by PM firmware version.")
        print()
        print("  To find it, you can:")
        print()
        print("  Option A — Compare with a working chair:")
        print("    If you have another chair with OBP enabled, dump its config")
        print("    and diff the two files to find the differing byte:")
        print(f"      rnet_programmer.py dump 0x0400 0x0600 -o working_cfg.bin")
        print(f"      xxd {sys_file} > a.hex && xxd working_cfg.bin > b.hex")
        print(f"      diff a.hex b.hex")
        print()
        print("  Option B — Use a known address:")
        print("    If you know the address for your firmware, write it:")
        print("      obp> enable-at 0x04XX")
        print("    or from CLI:")
        print("      rnet_obp_mode.py --enable-obp-addr 0x04XX")
        print()
        print("  Option C — Try common offsets:")
        print("    Some known locations to try (one at a time, power cycle between):")
        print("      obp> write-pop 0x0420 01")
        print("      obp> write-pop 0x0440 01")
        print("      obp> write-pop 0x0450 01")
        print()
        print(f"  Your backup is at: {backup_file}")
        print(f"  To restore: rnet_programmer.py write 0x0000 --input {backup_file}")
        print()

        return False

    def enable_obp_advanced(self, address: Optional[int] = None) -> bool:
        """
        ADVANCED MODE: Direct OBP enable without prompts or backup.

        If address is given, writes directly. Otherwise tries mode change only.
        """
        print("=" * 60)
        print("  OBP Enable — Advanced Mode (no backup, no prompts)")
        print("=" * 60)
        print()

        # Try mode change first (always safe)
        print("[1] Mode change to mode 8...")
        if self.force_mode_change(OBP_MODE_NUMBER):
            return True

        if address is not None:
            print()
            print(f"[2] Writing 0x01 to EEPROM 0x{address:04X} via POP...")
            return self.enable_obp_at_address(address, skip_backup=True)
        else:
            print()
            print("[!] Mode change failed and no address specified.")
            print("    Use --enable-obp-addr 0xNNNN or safe mode (--enable)")
            return False

    def enable_obp(self, address: Optional[int] = None,
                   advanced: bool = False) -> bool:
        """
        Enable OBP mode. Routes to safe or advanced workflow.

        Safe mode (default):
          - Tries non-destructive mode change first
          - Creates EEPROM backup before any writes
          - Shows config dump for manual inspection
          - Guides user through finding the right address

        Advanced mode (--advanced):
          - Skips backup and prompts
          - Tries mode change, then direct write if address given
        """
        if advanced:
            return self.enable_obp_advanced(address)
        else:
            if address is not None:
                # Safe mode with known address
                print("=" * 60)
                print("  OBP Enable — Safe Mode (known address)")
                print("=" * 60)
                print()
                print("  Step 1: Non-destructive mode change...")
                if self.force_mode_change(OBP_MODE_NUMBER):
                    return True
                print()
                print("  Step 2: Writing via POP (with backup)...")
                return self.enable_obp_at_address(address)
            else:
                return self.enable_obp_safe()

    # =========================================================================
    # Monitor Mode
    # =========================================================================

    def monitor(self, duration: float = 0):
        """
        Monitor parameter exchange traffic on the bus.

        Decodes 0x780-0x78F (requests) and 0x790-0x79F (responses)
        frames in real time.
        """
        print("Monitoring parameter exchange traffic (0x78X/0x79X)...")
        print("Enter OBP mode on the chair: Hold Horn + On/Off through bleeps")
        print("Press Ctrl+C to stop\n")

        start = time.time()
        try:
            while duration == 0 or (time.time() - start) < duration:
                msg = self.bus.recv(timeout=0.1) if self.bus else None
                if not msg:
                    continue

                aid = msg.arbitration_id
                # Filter to parameter exchange frames only
                if (0x780 <= aid <= 0x79F) and len(msg.data) >= 4:
                    elapsed = time.time() - start
                    decoded = decode_param_frame(aid, msg.data)
                    raw = msg.data.hex().upper()
                    print(f"[{elapsed:8.3f}] {aid:03X}#{raw}  {decoded}")

        except KeyboardInterrupt:
            print("\nStopped.")

    # =========================================================================
    # Scan Parameters
    # =========================================================================

    def scan_params(self):
        """Scan known OBP parameters and print their values."""
        print("Scanning known OBP parameters...\n")

        for cat_key, cat in OBP_MENU.items():
            print(f"--- {cat['name']} ---")
            for (ptr, sub), name in cat['params'].items():
                value = self.read_param(ptr, sub)
                if value is not None:
                    print(f"  {name:35s} = {value:5d}  (ptr=0x{ptr:02X} sub=0x{sub:02X})")
                else:
                    print(f"  {name:35s} = ???    (ptr=0x{ptr:02X} sub=0x{sub:02X})")
                time.sleep(INTER_FRAME_DELAY)
            print()

        print(f"Done. Read: {self.state.params_read}, Errors: {self.state.errors}")

    # =========================================================================
    # Interactive Mode
    # =========================================================================

    def interactive_mode(self):
        """Interactive OBP parameter shell."""
        print()
        print("=" * 60)
        print("R-Net OBP Interactive Mode")
        print("=" * 60)
        print()
        print("NOTE: The chair must be in OBP mode for parameter access.")
        print("Enter OBP: Hold Horn + On/Off through the bleep sequence.")
        print("If OBP is disabled, use 'enable' to force it on.")
        print()
        print("Commands:")
        print("  read <ptr> [sub]     - Read parameter (hex, default sub=0x01)")
        print("  write <ptr> <sub> <val> - Write parameter value")
        print("  scan                 - Scan all known OBP parameters")
        print("  monitor              - Monitor parameter exchange traffic")
        print("  check <ptr> [sub]    - Check if parameter exists")
        print("  enable               - Force OBP on (mode change + POP fallback)")
        print("  enable-at <addr>     - Enable OBP by writing EEPROM address via POP")
        print("  read-pop <addr> [len] - Read raw EEPROM via POP (hex addr)")
        print("  write-pop <addr> <hex> - Write raw EEPROM via POP")
        print("  slot <n>             - Set our request slot (default: 1=JSM)")
        print("  target <n>           - Set target slot (default: 0=PM)")
        print("  status               - Show connection status")
        print("  help                 - Show this help")
        print("  quit                 - Exit")
        print()

        while True:
            try:
                cmd = input("obp> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command in ('quit', 'exit', 'q'):
                    break

                elif command == 'help':
                    print("Commands: read, write, scan, monitor, check, slot, target, status, quit")

                elif command == 'read':
                    if len(parts) < 2:
                        print("Usage: read <pointer_hex> [sub_hex]")
                        continue
                    ptr = int(parts[1], 16)
                    sub = int(parts[2], 16) if len(parts) >= 3 else 0x01
                    name = PARAM_NAMES.get((ptr, sub), f"ptr=0x{ptr:02X} sub=0x{sub:02X}")
                    value = self.read_param(ptr, sub)
                    if value is not None:
                        print(f"{name} = {value} (0x{value:04X})")
                    else:
                        print(f"Failed to read {name}")

                elif command == 'write':
                    if len(parts) < 4:
                        print("Usage: write <pointer_hex> <sub_hex> <value_decimal>")
                        continue
                    ptr = int(parts[1], 16)
                    sub = int(parts[2], 16)
                    val = int(parts[3])
                    name = PARAM_NAMES.get((ptr, sub), f"ptr=0x{ptr:02X} sub=0x{sub:02X}")
                    print(f"Writing {name} = {val}...")
                    if self.write_param(ptr, sub, val):
                        print("Write successful")
                    else:
                        print("Write failed")

                elif command == 'scan':
                    self.scan_params()

                elif command == 'monitor':
                    self.monitor()

                elif command == 'check':
                    if len(parts) < 2:
                        print("Usage: check <pointer_hex> [sub_hex]")
                        continue
                    ptr = int(parts[1], 16)
                    sub = int(parts[2], 16) if len(parts) >= 3 else 0x01
                    exists = self.check_pointer(ptr, sub)
                    name = PARAM_NAMES.get((ptr, sub), "")
                    print(f"ptr=0x{ptr:02X} sub=0x{sub:02X}: {'EXISTS' if exists else 'NOT FOUND'}"
                          f"{f' ({name})' if name else ''}")

                elif command == 'enable':
                    self.enable_obp()

                elif command == 'enable-at':
                    if len(parts) < 2:
                        print("Usage: enable-at <eeprom_addr_hex>")
                        print("  Writes 0x01 to the given EEPROM address via POP")
                        print("  to enable OBP Keycode Entry.")
                        continue
                    addr = int(parts[1], 16)
                    self.enable_obp_at_address(addr)

                elif command == 'read-pop':
                    if len(parts) < 2:
                        print("Usage: read-pop <addr_hex> [length]")
                        continue
                    addr = int(parts[1], 16)
                    length = int(parts[2], 16) if len(parts) >= 3 else 4
                    if not self._pop_handshake():
                        print("[-] POP handshake failed")
                        continue
                    result = bytearray()
                    for off in range(0, length, 4):
                        self._pop_heartbeat_once()
                        chunk = self._pop_read(addr + off)
                        if chunk:
                            result.extend(chunk[:min(4, length - off)])
                        else:
                            print(f"[-] Read failed at 0x{addr + off:04X}")
                            break
                    if result:
                        for i in range(0, len(result), 16):
                            chunk = result[i:i + 16]
                            hex_p = ' '.join(f'{b:02X}' for b in chunk)
                            asc_p = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                            print(f"{addr + i:04X}: {hex_p:<48}  {asc_p}")

                elif command == 'write-pop':
                    if len(parts) < 3:
                        print("Usage: write-pop <addr_hex> <hex_data>")
                        continue
                    addr = int(parts[1], 16)
                    data = bytes.fromhex(''.join(parts[2:]))
                    if not self._pop_handshake():
                        print("[-] POP handshake failed")
                        continue
                    for off in range(0, len(data), 4):
                        chunk = data[off:off + 4]
                        if self._pop_write(addr + off, chunk):
                            print(f"[+] Wrote {chunk.hex().upper()} to 0x{addr + off:04X}")
                        else:
                            print(f"[-] Write failed at 0x{addr + off:04X}")
                            break

                elif command == 'slot':
                    if len(parts) < 2:
                        print(f"Current request slot: {self.slot} (0x{self.req_id:03X})")
                        continue
                    self.slot = int(parts[1])
                    print(f"Request slot set to {self.slot} (ID: 0x{self.req_id:03X})")

                elif command == 'target':
                    if len(parts) < 2:
                        print(f"Current target slot: {self.target_slot} (0x{self.rsp_id:03X})")
                        continue
                    self.target_slot = int(parts[1])
                    print(f"Target slot set to {self.target_slot} (response ID: 0x{self.rsp_id:03X})")

                elif command == 'status':
                    print(f"Connected:      {self.state.connected}")
                    print(f"Request slot:   {self.slot} (0x{self.req_id:03X})")
                    print(f"Target slot:    {self.target_slot} (0x{self.rsp_id:03X})")
                    print(f"Params read:    {self.state.params_read}")
                    print(f"Params written: {self.state.params_written}")
                    print(f"Errors:         {self.state.errors}")

                else:
                    print(f"Unknown command: {command}. Type 'help' for options.")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="R-Net OBP (On-Board Programming) Mode Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How to enter OBP mode on the wheelchair:
  1. Hold Horn button, then also hold On/Off button
  2. Wait for short bleep (after normal power-up sound)
  3. Release Horn, keep holding On/Off through two more bleeps
  4. Release On/Off — longer bleep confirms OBP active

  Note: Requires "OBP Keycode Entry" = Yes (OEM-level setting).
  If disabled, use --enable to force it on via CAN bus.

OBP vs Programmer Dongle (rnet_programmer.py):
  OBP:    JSM parameter exchange on 0x781/0x790 (register-based)
  Dongle: POP protocol on 0x78F/0x793 (raw memory addressing)

Examples:
  %(prog)s                            Interactive OBP shell
  %(prog)s --enable                   Force-enable OBP mode
  %(prog)s --enable-obp-addr 0x0450   Enable OBP by writing known EEPROM addr
  %(prog)s --monitor                  Monitor parameter exchange traffic
  %(prog)s --scan                     Scan known OBP parameters
  %(prog)s --read 0x06 0x01           Read Forward Speed parameter
  %(prog)s --write 0x06 0x01 80       Write Forward Speed = 80
        """
    )

    parser.add_argument('interface', nargs='?', default='can0',
                        help='CAN interface (default: can0)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output (show raw frames)')
    parser.add_argument('--slot', type=int, default=SLOT_JSM,
                        help='Our request slot (default: 1=JSM)')
    parser.add_argument('--target', type=int, default=SLOT_PM,
                        help='Target device slot (default: 0=PM)')
    parser.add_argument('--enable', action='store_true',
                        help='Enable OBP mode (safe: backup + guided workflow)')
    parser.add_argument('--enable-obp-addr', metavar='ADDR',
                        help='Enable OBP by writing 0x01 to this EEPROM address (hex)')
    parser.add_argument('--advanced', action='store_true',
                        help='Advanced mode: skip backup and prompts (use with --enable)')
    parser.add_argument('--monitor', action='store_true',
                        help='Monitor parameter exchange traffic')
    parser.add_argument('--scan', action='store_true',
                        help='Scan all known OBP parameters')
    parser.add_argument('--read', nargs='+', metavar='HEX',
                        help='Read parameter: <pointer> [sub] (hex)')
    parser.add_argument('--write', nargs=3, metavar=('PTR', 'SUB', 'VAL'),
                        help='Write parameter: <pointer> <sub> <value>')

    args = parser.parse_args()

    if not HAS_CAN:
        print("Error: python-can library required")
        print("Install with: pip install python-can")
        sys.exit(1)

    obp = RNetOBPMode(interface=args.interface, verbose=args.verbose,
                      slot=args.slot)
    obp.target_slot = args.target

    if not obp.connect():
        sys.exit(1)

    try:
        if args.enable or args.enable_obp_addr:
            addr = int(args.enable_obp_addr, 16) if args.enable_obp_addr else None
            obp.enable_obp(address=addr, advanced=args.advanced)

        elif args.monitor:
            obp.monitor()

        elif args.scan:
            obp.scan_params()

        elif args.read:
            ptr = int(args.read[0], 16)
            sub = int(args.read[1], 16) if len(args.read) > 1 else 0x01
            name = PARAM_NAMES.get((ptr, sub), f"ptr=0x{ptr:02X} sub=0x{sub:02X}")
            value = obp.read_param(ptr, sub)
            if value is not None:
                print(f"{name} = {value} (0x{value:04X})")
            else:
                print(f"Failed to read {name}")
                sys.exit(1)

        elif args.write:
            ptr = int(args.write[0], 16)
            sub = int(args.write[1], 16)
            val = int(args.write[2])
            name = PARAM_NAMES.get((ptr, sub), f"ptr=0x{ptr:02X} sub=0x{sub:02X}")
            print(f"Writing {name} = {val}...")
            if obp.write_param(ptr, sub, val):
                print("Write successful")
            else:
                print("Write failed")
                sys.exit(1)

        else:
            obp.interactive_mode()

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        obp.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
