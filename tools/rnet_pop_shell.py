#!/usr/bin/env python3
"""
R-Net POP Shell — Interactive POP (Parameter Object Protocol) programmer.

Emulates the R-Net Programmer dongle (D50610) over SocketCAN.
Sends the 0x7A0 announce frame, maintains heartbeat on 0x78F/0x793,
and provides raw memory read/write via POP Quick protocol.

NOTE: This is NOT the same as OBP (On-Board Programming) mode, which is
activated by the wheelchair user via a joystick/button combo and uses
the JSM parameter exchange protocol (0x781/0x790). See rnet_obp_mode.py
for that. This tool emulates the external programmer dongle.

Protocol: POP Quick on CAN IDs 0x78F (request) / 0x793 (response)
Transport: REBUS protocol layer
Memory model: ODI classes (EEPROM/RAM/ROM/SLOT)
Source: DongleInterface.dll v3.0.0.0, PG Drives Technology

Usage:
    python3 rnet_pop_shell.py [interface]
    python3 rnet_pop_shell.py can0 --read 0x0000 0x100
    python3 rnet_pop_shell.py can0 --dump config.bin
    python3 rnet_pop_shell.py can0 --interactive

Author: Stephen Chavez & Specter
Based on DEFCON24 R-Net research
"""

import argparse
import sys
import time
import struct
import threading
import os
from typing import Optional, Callable
from dataclasses import dataclass, field

try:
    import can
    HAS_CAN = True
except ImportError:
    HAS_CAN = False
    print("[!] python-can not installed. Install with: pip install python-can")


# =============================================================================
# POP Protocol Constants (from DongleInterface.dll v3.0.0.0)
# =============================================================================

# Frame IDs (POP Quick protocol - standard 11-bit CAN)
PROGRAMMER_ANNOUNCE = 0x7A0    # Presence announcement (empty frame)
PROGRAMMER_REQUEST = 0x78F     # POP Quick request (node 0xF = programmer)
PROGRAMMER_RESPONSE = 0x793    # POP Quick response (node 0x3 = PM)

# POP Command bytes (Request)
CMD_HEARTBEAT = 0x42           # PRESENCE_REQ - heartbeat/polling
CMD_SET_ADDRESS = 0x83         # SET_ADDRESS - set memory pointer
CMD_READ = 0x03                # START_READ - begin read operation
CMD_WRITE = 0x43               # START_WRITE - begin write operation

# POP Command bytes (Response)
RSP_HEARTBEAT_ACK = 0x2F       # PRESENCE_ACK - heartbeat acknowledgment
RSP_READ_DATA = 0x4F           # READ_RESPONSE - read data response
RSP_WRITE_ACK = 0x0F           # WRITE_RESPONSE - write acknowledgment
RSP_COMPLETE = 0x8F            # COMPLETE - operation complete
RSP_ACK = 0x41                 # ACK - general acknowledgment
RSP_ERROR = 0xC1               # ERROR - error response

# ODI Memory Classes (from DongleInterface.dll ODI_CLASS_* constants)
ODI_EEPROM = 0x0100            # Non-volatile configuration storage
ODI_PORT = 0x0110              # I/O port registers
ODI_RAM = 0x0120               # Volatile runtime memory
ODI_ROM = 0x0130               # Read-only firmware/calibration data
ODI_ADC = 0x0140               # Analog-to-digital converter readings
ODI_SLOT = 0x0200              # Device slot/file storage

ODI_CLASS_NAMES = {
    ODI_EEPROM: 'EEPROM', ODI_PORT: 'PORT', ODI_RAM: 'RAM',
    ODI_ROM: 'ROM', ODI_ADC: 'ADC', ODI_SLOT: 'SLOT',
}

# POP error codes (from DongleInterface.dll RB_ERROR enum)
ERR_NONE = 0x00                # Success
ERR_ABORT = 0x01               # Transaction aborted
ERR_COMMS = 0x02               # Communication failure
ERR_NO_CONNECTION = 0x03       # No connection to device
ERR_REP_TAKEN = 0x04           # Repository held by another programmer
ERR_CHKSUM = 0x05              # CRC/checksum mismatch
ERR_INV_NODE = 0x06            # Invalid node number
ERR_INV_PARM = 0x07            # Invalid parameter

ERR_NAMES = {
    ERR_NONE: 'NONE', ERR_ABORT: 'ABORT', ERR_COMMS: 'COMMS',
    ERR_NO_CONNECTION: 'NO_CONNECTION', ERR_REP_TAKEN: 'REP_TAKEN',
    ERR_CHKSUM: 'CHKSUM', ERR_INV_NODE: 'INV_NODE', ERR_INV_PARM: 'INV_PARM',
}

# Timing (from DongleInterface.dll)
HEARTBEAT_INTERVAL = 0.2       # 200ms heartbeat interval
RESPONSE_TIMEOUT = 0.5         # 500ms response timeout (DONGLE_TIMEOUT)
INTER_FRAME_DELAY = 0.002      # 2ms inter-frame gap
POP_QCK_TIMEOUT = 1.0          # 1000ms quick transaction timeout
SESSION_TIMEOUT = 2.0           # ~2s session timeout without heartbeat
READ_RETRY_COUNT = 3            # Max read retries
RECONNECT_TIMEOUT = 0.2        # 200ms delay between retries

# POP Read Mode byte (byte 4 of START_READ frame)
# Observed in all programmer captures, documented as "read size/mode".
POP_READ_MODE = 0x17


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProgrammerState:
    """State of the programming session."""
    connected: bool = False
    heartbeat_running: bool = False
    last_heartbeat: float = 0
    current_address: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    errors: int = 0


# =============================================================================
# R-Net OBD Programmer Class
# =============================================================================

class RNetOBDProgrammer:
    """
    R-Net On-Board Programming Mode Controller.

    Uses POP (Parameter Object Protocol) Quick transactions on CAN IDs
    0x78F/0x793 to read/write device configuration via the ODI EEPROM
    memory class (0x0100).

    Source: Protocol details from DongleInterface.dll v3.0.0.0
    """

    def __init__(self, interface: str = "can0", verbose: bool = False,
                 odi_class: int = ODI_EEPROM, target_device: int = 0xFF):
        self.interface = interface
        self.verbose = verbose
        self.odi_class = odi_class
        self.target_device = target_device  # 0xFF=broadcast, 0x00=PM, 0x01=JSM
        self.state = ProgrammerState()
        self.bus: Optional[can.Bus] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.stop_heartbeat = threading.Event()
        self.lock = threading.Lock()

    def log(self, msg: str, level: str = "INFO"):
        """Log message if verbose."""
        if self.verbose or level in ("ERROR", "WARN"):
            prefix = {"INFO": "[*]", "OK": "[+]", "ERROR": "[-]", "WARN": "[!]", "DEBUG": "[.]"}
            print(f"{prefix.get(level, '[*]')} {msg}")

    def connect(self) -> bool:
        """Open CAN bus connection."""
        if not HAS_CAN:
            self.log("python-can not available", "ERROR")
            return False

        try:
            self.bus = can.Bus(channel=self.interface, bustype='socketcan')
            self.log(f"Connected to {self.interface}", "OK")
            return True
        except Exception as e:
            self.log(f"Failed to connect: {e}", "ERROR")
            return False

    def disconnect(self):
        """Close CAN bus connection."""
        self.stop_heartbeat_thread()
        if self.bus:
            self.bus.shutdown()
            self.bus = None
        self.state.connected = False
        self.log("Disconnected")

    def send_frame(self, arb_id: int, data: bytes = b'', is_extended: bool = False) -> bool:
        """Send a CAN frame."""
        if not self.bus:
            return False

        try:
            msg = can.Message(
                arbitration_id=arb_id,
                data=data,
                is_extended_id=is_extended
            )
            self.bus.send(msg)
            if self.verbose:
                data_hex = data.hex().upper() if data else "(empty)"
                self.log(f"TX: {arb_id:03X}#{data_hex}", "DEBUG")
            return True
        except Exception as e:
            self.log(f"Send failed: {e}", "ERROR")
            return False

    def recv_frame(self, timeout: float = RESPONSE_TIMEOUT,
                   filter_id: Optional[int] = None) -> Optional[can.Message]:
        """Receive a CAN frame with optional ID filter."""
        if not self.bus:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.bus.recv(timeout=0.05)
                if msg:
                    if filter_id is None or msg.arbitration_id == filter_id:
                        if self.verbose:
                            data_hex = msg.data.hex().upper() if msg.data else "(empty)"
                            self.log(f"RX: {msg.arbitration_id:03X}#{data_hex}", "DEBUG")
                        return msg
            except Exception:
                pass
        return None

    # =========================================================================
    # Programmer Mode Control
    # =========================================================================

    def announce_presence(self) -> bool:
        """Send programmer presence announcement (0x7A0)."""
        return self.send_frame(PROGRAMMER_ANNOUNCE, b'')

    def send_heartbeat(self) -> bool:
        """Send heartbeat and wait for ACK."""
        # Heartbeat frame: 42 20 00 FF 00 00 00 00
        data = bytes([CMD_HEARTBEAT, 0x20, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00])

        with self.lock:
            if not self.send_frame(PROGRAMMER_REQUEST, data):
                return False

            # Wait for ACK
            response = self.recv_frame(timeout=RESPONSE_TIMEOUT, filter_id=PROGRAMMER_RESPONSE)
            if response and len(response.data) >= 1:
                if response.data[0] == RSP_HEARTBEAT_ACK:
                    self.state.last_heartbeat = time.time()
                    return True

        return False

    def heartbeat_loop(self):
        """Background heartbeat thread."""
        self.log("Heartbeat thread started", "DEBUG")
        while not self.stop_heartbeat.is_set():
            if self.state.connected:
                if not self.send_heartbeat():
                    self.log("Heartbeat failed", "WARN")
                    self.state.errors += 1
            self.stop_heartbeat.wait(HEARTBEAT_INTERVAL)
        self.log("Heartbeat thread stopped", "DEBUG")

    def start_heartbeat_thread(self):
        """Start background heartbeat thread."""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return

        self.stop_heartbeat.clear()
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        self.state.heartbeat_running = True

    def stop_heartbeat_thread(self):
        """Stop background heartbeat thread."""
        self.stop_heartbeat.set()
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
        self.state.heartbeat_running = False

    def enable_programming_mode(self) -> bool:
        """
        Enable on-board programming mode.

        Sequence:
        1. Send 0x7A0# (announce presence)
        2. Send heartbeat (0x78F#42...)
        3. Wait for ACK (0x793#2F...)
        4. Start heartbeat thread
        """
        print("=" * 60)
        print("R-Net On-Board Programming Mode")
        print("=" * 60)

        # Step 1: Announce presence
        print("\n[1/3] Announcing programmer presence...")
        self.announce_presence()
        time.sleep(0.1)

        # Step 2: Initial heartbeat
        print("[2/3] Sending initial heartbeat...")
        success = False
        for attempt in range(3):
            if self.send_heartbeat():
                success = True
                break
            print(f"      Attempt {attempt + 1}/3 failed, retrying...")
            time.sleep(0.1)

        if not success:
            print("[-] Failed to establish connection")
            print("    Check that:")
            print("    - CAN interface is up (ip link set can0 up type can bitrate 125000)")
            print("    - R-Net bus is powered")
            print("    - Connections are correct")
            return False

        # Step 3: Start heartbeat thread
        print("[3/3] Starting heartbeat thread...")
        self.state.connected = True
        self.start_heartbeat_thread()

        print()
        print("[+] Programming mode ENABLED")
        print(f"    Interface: {self.interface}")
        print(f"    Heartbeat: every {int(HEARTBEAT_INTERVAL * 1000)}ms")
        print()

        return True

    # =========================================================================
    # Memory Operations
    # =========================================================================

    def _odi_bytes(self):
        """Return (low, high) bytes for current ODI class.

        ODI class encoded little-endian in bytes 1-2 of POP Quick frames:
          EEPROM (0x0100) -> 0x00, 0x01
          RAM    (0x0120) -> 0x20, 0x01
          ROM    (0x0130) -> 0x30, 0x01
        Source: DongleInterface.dll ODI_CLASS encoding.
        """
        return (self.odi_class & 0xFF, (self.odi_class >> 8) & 0xFF)

    def set_address(self, address: int) -> bool:
        """Set memory address pointer.

        Frame: [CMD_SET_ADDRESS][ODI_LO][ODI_HI][DEV_ID][ADDR_LO][ADDR_HI][00][00]
        """
        addr_lo = address & 0xFF
        addr_hi = (address >> 8) & 0xFF
        odi_lo, odi_hi = self._odi_bytes()
        data = bytes([CMD_SET_ADDRESS, odi_lo, odi_hi, self.target_device,
                      addr_lo, addr_hi, 0x00, 0x00])

        with self.lock:
            if not self.send_frame(PROGRAMMER_REQUEST, data):
                return False
            time.sleep(INTER_FRAME_DELAY)

        self.state.current_address = address
        return True

    def _read_chunk(self, address: int, chunk_size: int) -> Optional[bytes]:
        """Read a single 4-byte chunk from device memory.

        Frame format (from DongleInterface.dll POP Quick protocol):
          START_READ: [CMD][ODI_LO][ODI_HI][DEV_ID][POP_READ_MODE][00][00][00]
          Response:   [RSP_READ_DATA][ODI_LO][ODI_HI][DEV_ID][D0][D1][D2][D3]
        """
        odi_lo, odi_hi = self._odi_bytes()
        data = bytes([CMD_READ, odi_lo, odi_hi, self.target_device,
                      POP_READ_MODE, 0x00, 0x00, 0x00])

        with self.lock:
            if not self.send_frame(PROGRAMMER_REQUEST, data):
                return None

            response = self.recv_frame(timeout=RESPONSE_TIMEOUT, filter_id=PROGRAMMER_RESPONSE)
            if not response or len(response.data) < 8:
                return None

            if response.data[0] == RSP_READ_DATA:
                chunk = bytes(response.data[4:4 + chunk_size])
                # Wait for COMPLETE
                complete = self.recv_frame(timeout=RESPONSE_TIMEOUT, filter_id=PROGRAMMER_RESPONSE)
                if complete and complete.data[0] != RSP_COMPLETE:
                    self.log("Missing COMPLETE response", "WARN")
                return chunk
            elif response.data[0] == RSP_ERROR:
                err_code = response.data[4] if len(response.data) > 4 else 0
                err_name = ERR_NAMES.get(err_code, f"0x{err_code:02X}")
                self.log(f"Error reading 0x{address:04X}: {err_name}", "ERROR")
                self.state.errors += 1
                return None

        return None

    def read_bytes(self, address: int, length: int,
                   progress_callback: Optional[Callable] = None) -> Optional[bytes]:
        """
        Read bytes from device memory with retry logic.

        Retries up to READ_RETRY_COUNT (3) times per chunk, matching
        the retry behavior documented in DongleInterface.dll.

        Args:
            address: Start address
            length: Number of bytes to read
            progress_callback: Optional callback(bytes_read, total_bytes)

        Returns:
            bytes read or None on error
        """
        result = bytearray()
        bytes_remaining = length
        current_addr = address

        while bytes_remaining > 0:
            chunk_size = min(4, bytes_remaining)

            # Set address
            if not self.set_address(current_addr):
                self.log(f"Failed to set address 0x{current_addr:04X}", "ERROR")
                return None

            # Read with retries (DongleInterface.dll: READ_RETRY_COUNT=3)
            chunk = None
            for retry in range(READ_RETRY_COUNT):
                chunk = self._read_chunk(current_addr, chunk_size)
                if chunk is not None:
                    break
                if retry < READ_RETRY_COUNT - 1:
                    self.log(f"Retry {retry + 1}/{READ_RETRY_COUNT} at 0x{current_addr:04X}", "WARN")
                    time.sleep(RECONNECT_TIMEOUT)
                    # Re-set address for retry
                    self.set_address(current_addr)

            if chunk is None:
                self.log(f"Read failed at 0x{current_addr:04X} after {READ_RETRY_COUNT} attempts", "ERROR")
                self.state.errors += 1
                return None

            result.extend(chunk)
            current_addr += chunk_size
            bytes_remaining -= chunk_size
            self.state.bytes_read += chunk_size

            if progress_callback:
                progress_callback(len(result), length)

            time.sleep(INTER_FRAME_DELAY)

        return bytes(result)

    def write_bytes(self, address: int, data: bytes,
                    progress_callback: Optional[Callable] = None) -> bool:
        """
        Write bytes to device memory.

        Args:
            address: Start address
            data: Bytes to write
            progress_callback: Optional callback(bytes_written, total_bytes)

        Returns:
            True on success
        """
        total = len(data)
        written = 0

        while written < total:
            chunk_size = min(4, total - written)
            current_addr = address + written
            chunk = data[written:written + chunk_size]

            # Pad to 4 bytes if needed
            while len(chunk) < 4:
                chunk = chunk + b'\x00'

            # Set address
            if not self.set_address(current_addr):
                self.log(f"Failed to set address 0x{current_addr:04X}", "ERROR")
                return False

            # Send write command
            # WRITE: [CMD][ODI_LO][ODI_HI][DEV_ID][D0][D1][D2][D3]
            odi_lo, odi_hi = self._odi_bytes()
            cmd = bytes([CMD_WRITE, odi_lo, odi_hi, self.target_device]) + chunk

            with self.lock:
                if not self.send_frame(PROGRAMMER_REQUEST, cmd):
                    return False

                # Wait for write ACK
                response = self.recv_frame(timeout=RESPONSE_TIMEOUT, filter_id=PROGRAMMER_RESPONSE)
                if not response:
                    self.log(f"No response writing 0x{current_addr:04X}", "ERROR")
                    return False

                if response.data[0] == RSP_WRITE_ACK:
                    if response.data[4] != RSP_ACK:
                        self.log(f"Write rejected at 0x{current_addr:04X}", "ERROR")
                        return False
                elif response.data[0] == RSP_ERROR:
                    self.log(f"Error writing 0x{current_addr:04X}", "ERROR")
                    return False

                # Wait for COMPLETE
                self.recv_frame(timeout=RESPONSE_TIMEOUT, filter_id=PROGRAMMER_RESPONSE)

            written += chunk_size
            self.state.bytes_written += chunk_size

            if progress_callback:
                progress_callback(written, total)

            time.sleep(INTER_FRAME_DELAY)

        return True

    def dump_memory(self, start: int, length: int, filename: str) -> bool:
        """
        Dump memory range to file.

        Args:
            start: Start address
            length: Number of bytes
            filename: Output filename

        Returns:
            True on success
        """
        print(f"Dumping 0x{start:04X} - 0x{start + length:04X} ({length} bytes)")
        print()

        def progress(done, total):
            pct = 100 * done / total
            bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
            print(f"\r[{bar}] {pct:5.1f}% ({done}/{total})", end="", flush=True)

        data = self.read_bytes(start, length, progress_callback=progress)
        print()

        if data:
            with open(filename, 'wb') as f:
                f.write(data)
            print(f"\n[+] Saved to {filename}")
            return True
        else:
            print("\n[-] Dump failed")
            return False

    def hexdump(self, data: bytes, base_addr: int = 0):
        """Print hex dump of data."""
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"{base_addr + i:04X}: {hex_part:<48}  {ascii_part}")

    # =========================================================================
    # Interactive Mode
    # =========================================================================

    def interactive_mode(self):
        """Interactive programming shell."""
        print()
        print("=" * 60)
        print("Interactive Programming Mode")
        print("=" * 60)
        print()
        print("Commands:")
        print("  read <addr> [len]    - Read memory (default 16 bytes)")
        print("  write <addr> <hex>   - Write hex data to address")
        print("  dump <addr> <len> <file> - Dump memory to file")
        print("  odi <class>          - Set ODI class (eeprom/ram/rom/slot)")
        print("  target <id>          - Set target device (0xFF=broadcast, 0x00=PM)")
        print("  status               - Show connection status")
        print("  help                 - Show this help")
        print("  quit / exit          - Exit programming mode")
        print()

        while True:
            try:
                cmd = input("rnet> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command in ('quit', 'exit', 'q'):
                    print("Exiting programming mode...")
                    break

                elif command == 'help':
                    print("Commands: read, write, dump, status, help, quit")

                elif command == 'odi':
                    if len(parts) < 2:
                        name = ODI_CLASS_NAMES.get(self.odi_class, f"0x{self.odi_class:04X}")
                        print(f"Current ODI class: {name} (0x{self.odi_class:04X})")
                        print("Usage: odi <eeprom|ram|rom|slot|port|adc>")
                        continue
                    odi_map = {
                        'eeprom': ODI_EEPROM, 'ram': ODI_RAM, 'rom': ODI_ROM,
                        'slot': ODI_SLOT, 'port': ODI_PORT, 'adc': ODI_ADC,
                    }
                    cls = parts[1].lower()
                    if cls in odi_map:
                        self.odi_class = odi_map[cls]
                        print(f"ODI class set to {cls.upper()} (0x{self.odi_class:04X})")
                    else:
                        print(f"Unknown class: {cls}. Options: {', '.join(odi_map.keys())}")

                elif command == 'target':
                    if len(parts) < 2:
                        print(f"Current target: 0x{self.target_device:02X}"
                              f" ({'broadcast' if self.target_device == 0xFF else 'device'})")
                        print("Usage: target <hex_id> (0xFF=broadcast, 0x00=PM, 0x01=JSM)")
                        continue
                    self.target_device = int(parts[1], 16)
                    print(f"Target device set to 0x{self.target_device:02X}")

                elif command == 'status':
                    odi_name = ODI_CLASS_NAMES.get(self.odi_class, f"0x{self.odi_class:04X}")
                    print(f"Connected: {self.state.connected}")
                    print(f"Heartbeat: {'running' if self.state.heartbeat_running else 'stopped'}")
                    print(f"ODI class: {odi_name} (0x{self.odi_class:04X})")
                    print(f"Target:    0x{self.target_device:02X}")
                    print(f"Bytes read: {self.state.bytes_read}")
                    print(f"Bytes written: {self.state.bytes_written}")
                    print(f"Errors: {self.state.errors}")

                elif command == 'read':
                    if len(parts) < 2:
                        print("Usage: read <addr> [len]")
                        continue
                    addr = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    length = 16
                    if len(parts) >= 3:
                        length = int(parts[2], 16) if parts[2].startswith('0x') else int(parts[2])

                    print(f"Reading {length} bytes from 0x{addr:04X}...")
                    data = self.read_bytes(addr, length)
                    if data:
                        self.hexdump(data, addr)
                    else:
                        print("Read failed")

                elif command == 'write':
                    if len(parts) < 3:
                        print("Usage: write <addr> <hex_data>")
                        continue
                    addr = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    hex_data = ''.join(parts[2:]).replace(' ', '')
                    data = bytes.fromhex(hex_data)

                    print(f"Writing {len(data)} bytes to 0x{addr:04X}...")
                    if self.write_bytes(addr, data):
                        print("Write successful")
                    else:
                        print("Write failed")

                elif command == 'dump':
                    if len(parts) < 4:
                        print("Usage: dump <addr> <len> <filename>")
                        continue
                    addr = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    length = int(parts[2], 16) if parts[2].startswith('0x') else int(parts[2])
                    filename = parts[3]
                    self.dump_memory(addr, length, filename)

                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")

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
        description="R-Net On-Board Programming Mode Tool (POP Quick protocol)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Protocol: POP (Parameter Object Protocol) Quick on CAN 0x78F/0x793
Transport: REBUS protocol layer (DongleInterface.dll v3.0.0.0)

Examples:
  %(prog)s                          Enable programming mode (interactive)
  %(prog)s can0                     Use specific CAN interface
  %(prog)s --read 0x0000 0x100      Read 256 bytes from address 0
  %(prog)s --dump config.bin        Dump entire config (0x0000-0x1000)
  %(prog)s --write 0x0430 32        Write speed=50 to address 0x0430
  %(prog)s -v                       Verbose mode (show all frames)

ODI EEPROM Addresses (0x0100 memory class):
  0x0000-0x00FF   Device header
  0x0160-0x016F   Encryption key
  0x0400-0x0FFF   Configuration
  0x0430          Speed setting
        """
    )

    parser.add_argument('interface', nargs='?', default='can0',
                        help='CAN interface (default: can0)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--odi-class', default='eeprom',
                        choices=['eeprom', 'ram', 'rom', 'slot', 'port', 'adc'],
                        help='ODI memory class (default: eeprom). '
                             'From DongleInterface.dll: eeprom=0x0100, ram=0x0120, '
                             'rom=0x0130, slot=0x0200')
    parser.add_argument('--target', default='0xFF',
                        help='Target device ID hex (default: 0xFF=broadcast). '
                             '0x00=PM, 0x01=JSM, 0xFF=all')
    parser.add_argument('--read', nargs=2, metavar=('ADDR', 'LEN'),
                        help='Read memory (hex addresses)')
    parser.add_argument('--write', nargs=2, metavar=('ADDR', 'DATA'),
                        help='Write data to address')
    parser.add_argument('--dump', metavar='FILE',
                        help='Dump config to file (0x0000-0x1000)')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive mode (default)')

    args = parser.parse_args()

    if not HAS_CAN:
        print("Error: python-can library required")
        print("Install with: pip install python-can")
        sys.exit(1)

    # Parse ODI class and target
    odi_map = {
        'eeprom': ODI_EEPROM, 'ram': ODI_RAM, 'rom': ODI_ROM,
        'slot': ODI_SLOT, 'port': ODI_PORT, 'adc': ODI_ADC,
    }
    odi = odi_map.get(args.odi_class, ODI_EEPROM)
    target = int(args.target, 16)

    # Create programmer
    programmer = RNetOBDProgrammer(interface=args.interface, verbose=args.verbose,
                                    odi_class=odi, target_device=target)

    # Connect to CAN bus
    if not programmer.connect():
        sys.exit(1)

    try:
        # Enable programming mode
        if not programmer.enable_programming_mode():
            programmer.disconnect()
            sys.exit(1)

        # Handle specific operations
        if args.read:
            addr = int(args.read[0], 16) if args.read[0].startswith('0x') else int(args.read[0])
            length = int(args.read[1], 16) if args.read[1].startswith('0x') else int(args.read[1])
            print(f"\nReading {length} bytes from 0x{addr:04X}...\n")
            data = programmer.read_bytes(addr, length)
            if data:
                programmer.hexdump(data, addr)
            else:
                print("Read failed")

        elif args.write:
            addr = int(args.write[0], 16) if args.write[0].startswith('0x') else int(args.write[0])
            hex_data = args.write[1].replace(' ', '')
            data = bytes.fromhex(hex_data)
            print(f"\nWriting {len(data)} bytes to 0x{addr:04X}...\n")
            if programmer.write_bytes(addr, data):
                print("Write successful")
            else:
                print("Write failed")

        elif args.dump:
            programmer.dump_memory(0x0000, 0x1000, args.dump)

        else:
            # Default: interactive mode
            programmer.interactive_mode()

    except KeyboardInterrupt:
        print("\n\nInterrupted")

    finally:
        print("\nDisabling programming mode...")
        programmer.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
