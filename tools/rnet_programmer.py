#!/usr/bin/env python3
"""
R-Net Programmer Mode Tool
===========================
Enables programmer mode on R-Net wheelchair CAN bus and provides
read/write access to device configuration via the POP (Parameter
Object Protocol).

Protocol: POP Quick (0x78F/0x793) and POP Segmented (0x1E4X/0x1E0X)
Transport: REBUS (R-Net bus protocol layer)
Memory model: ODI (Object Dictionary Interface) - primarily EEPROM class
Source: DongleInterface.dll v3.0.0.0, PG Drives Technology

Based on DEFCON24 research by Stephen Chavez & Specter.
Protocol details from reverse engineering of R-Net Programmer software.

Usage:
    python3 rnet_programmer.py --interface can0 read 0x0000 0x100
    python3 rnet_programmer.py --interface can0 write 0x0000 data.bin
    python3 rnet_programmer.py --interface can0 dump output.bin
    python3 rnet_programmer.py --interface can0 monitor
"""

import socket
import struct
import sys
import argparse
import time
import threading
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# CAN Frame Building (from can2RNET.py)
# ============================================================================

def build_frame(canstr: str) -> bytes:
    """Build a SocketCAN frame from cansend format string."""
    if '#' not in canstr:
        raise ValueError(f'build_frame: missing # in {canstr}')

    cansplit = canstr.split('#')
    lcanid = len(cansplit[0])
    RTR = '#R' in canstr

    if lcanid == 3:
        canid = struct.pack('I', int(cansplit[0], 16) + 0x40000000 * RTR)
    elif lcanid == 8:
        canid = struct.pack('I', int(cansplit[0], 16) + 0x80000000 + 0x40000000 * RTR)
    else:
        raise ValueError(f'build_frame: invalid frame id format: {canstr}')

    can_dlc = 0
    len_datstr = len(cansplit[1])

    if not RTR and len_datstr <= 16 and not len_datstr & 1:
        candat = bytes.fromhex(cansplit[1])
        can_dlc = len(candat)
        candat = candat.ljust(8, b'\x00')
    elif not len_datstr or RTR:
        candat = b'\x00\x00\x00\x00\x00\x00\x00\x00'
    else:
        raise ValueError(f'build_frame: invalid data format: {canstr}')

    return canid + struct.pack("B", can_dlc & 0xF) + b'\x00\x00\x00' + candat


def dissect_frame(frame: bytes) -> str:
    """Dissect a SocketCAN frame to cansend format string."""
    can_frame_fmt = "<IB3x8s"
    can_id, can_dlc, data = struct.unpack(can_frame_fmt, frame)

    if can_id & 0x80000000:
        idl = 8
    else:
        idl = 3

    if can_id & 0x40000000:
        rtr = True
    else:
        rtr = False

    can_idtxt = f'{can_id & 0x1FFFFFFF:08X}'[-idl:]
    return can_idtxt + '#' + ''.join([f"{x:02X}" for x in data[:can_dlc]]) + 'R' * rtr


# ============================================================================
# R-Net Programmer Protocol Constants
# ============================================================================

class POPCommand(Enum):
    """POP (Parameter Object Protocol) command bytes.

    Source: DongleInterface.dll v3.0.0.0, PG Drives Technology.
    The POP protocol (internally called REBUS) handles all device
    configuration read/write over the R-Net CAN bus.
    """
    # Request commands
    PRESENCE_REQ = 0x42      # Heartbeat/polling request
    SET_ADDRESS = 0x83       # Set memory address pointer
    START_READ = 0x03        # Begin read operation
    START_WRITE = 0x43       # Begin write operation
    # Response commands
    PRESENCE_ACK = 0x2F      # Heartbeat acknowledgment
    READ_RESPONSE = 0x4F     # Read data response
    WRITE_RESPONSE = 0x0F    # Write acknowledgment
    COMPLETE = 0x8F          # Operation complete
    ACK = 0x41               # General acknowledgment
    ERROR = 0xC1             # Error response


class POPTransferCode(Enum):
    """POP transfer codes for segmented (multi-frame) operations.
    Source: DongleInterface.dll TC_* constants."""
    UL_RES = 0x01             # Upload response (device -> programmer)
    UL_REQ = 0x03             # Upload request (programmer -> device)
    DLS_REQ = 0x04            # Download segmented request
    DL_REQ = 0x05             # Download request
    DL_RES = 0x07             # Download response
    DLS_RES = 0x08            # Download segmented response
    ULS_REQ = 0x09            # Upload segmented request
    ULS_RES = 0x0A            # Upload segmented response
    ABORT = 0x0B              # Transaction abort
    END = 0x0C                # Transaction end
    ILLEGAL = 0x0F            # Invalid transfer code


class ODIClass(Enum):
    """ODI (Object Dictionary Interface) memory classes.
    Source: DongleInterface.dll ODI_CLASS_* constants.

    Each R-Net device organizes memory into these classes.
    The programmer primarily reads/writes EEPROM (0x0100).
    """
    EEPROM = 0x0100           # Non-volatile configuration storage
    PORT = 0x0110             # I/O port registers
    RAM = 0x0120              # Volatile runtime memory
    ROM = 0x0130              # Read-only firmware/calibration data
    ADC = 0x0140              # Analog-to-digital converter readings
    SLOT = 0x0200             # Device slot/file storage
    SENTINEL = 0xFFFFFF       # Invalid/sentinel value


class RBError(Enum):
    """POP error codes.
    Source: DongleInterface.dll RB_ERROR enum."""
    NONE = 0x00               # Success
    ABORT = 0x01              # Transaction aborted
    COMMS = 0x02              # Communication failure
    NO_CONNECTION = 0x03      # No connection to device
    REP_TAKEN = 0x04          # Repository held by another programmer
    CHKSUM = 0x05             # CRC/checksum mismatch
    INV_NODE = 0x06           # Invalid node number
    INV_PARM = 0x07           # Invalid parameter


# Frame IDs (POP Quick protocol - standard 11-bit CAN)
PROGRAMMER_REQUEST_ID = 0x78F   # Programmer sends requests (POP node 0xF)
PROGRAMMER_RESPONSE_ID = 0x793  # PM sends responses (POP node 0x3)
PROGRAMMER_ANNOUNCE_ID = 0x7A0  # Programmer presence announcement
STATUS_FRAME_ID = 0x0300        # Extended frame for status

# POP Quick protocol base IDs (node appended: 0x780+node, 0x790+node)
POP_QCK_REQ_BASE = 0x780       # POP Quick request base
POP_QCK_RES_BASE = 0x790       # POP Quick response base

# POP Segmented protocol (extended 29-bit CAN IDs)
POP_SEG_REQ_BASE = 0x1E400000  # Segmented request: base | (node << 15) | (tc << 18)
POP_SEG_RES_BASE = 0x1E000000  # Segmented response: base | (node << 15) | (tc << 18)
POP_SEG_NODE_MASK = 0x00030000
POP_SEG_NODE_SHIFT = 15
POP_SEG_TC_MASK = 0x003C0000
POP_SEG_TC_SHIFT = 18

# Notification frame IDs (from DongleInterface.dll)
SLOT_CHANGED_ID = 0x42D         # Device slot change notification
MODE_CHANGE_ID = 0x431          # Mode change notification
PROFILE_CHANGE_ID = 0x436       # Profile/speed change notification
SLEEP_RESET_ID = 0x0006C01F     # CAN bus sleep/wake reset (extended)

# Timing constants (from DongleInterface.dll)
POP_QCK_TIMEOUT = 1.0           # Quick POP transaction timeout (1000ms)
POP_SEG_TIMEOUT = 0.1           # Segmented timeout per segment (100ms)
HEARTBEAT_INTERVAL = 0.2        # Heartbeat interval (200ms)
DONGLE_TIMEOUT = 0.5            # Dongle response timeout (500ms)
CANMSG_TIMEOUT = 10.0           # Overall CAN message timeout (10000ms)
READ_RETRY_COUNT = 3            # Max read retries
RECONNECT_TIMEOUT = 0.2         # Reconnect delay (200ms)
SESSION_TIMEOUT = 2.0           # Session drops after ~2s without heartbeat
INTER_FRAME_DELAY = 0.002      # 2ms minimum inter-frame gap

# POP Read Mode byte (byte 4 of START_READ frame).
# Observed in all programmer captures: 78F#030001FF17000000
# Documented as "read size/mode" in DongleInterface.dll traffic.
POP_READ_MODE = 0x17


# ============================================================================
# Programmer Mode State Machine
# ============================================================================

@dataclass
class ProgrammerState:
    """Current programmer state."""
    connected: bool = False
    last_response_time: float = 0
    pending_read_address: int = 0
    pending_read_size: int = 0
    read_buffer: bytearray = None
    error_message: str = ""

    def __post_init__(self):
        if self.read_buffer is None:
            self.read_buffer = bytearray()


class RNetProgrammer:
    """
    R-Net POP (Parameter Object Protocol) Controller.

    Enables programmer mode on the CAN bus and provides read/write
    access to device configuration memory (ODI class EEPROM, 0x0100).

    Protocol source: DongleInterface.dll v3.0.0.0 (PG Drives Technology).
    Uses POP Quick protocol on standard CAN IDs 0x78F (request) / 0x793 (response).
    """

    def __init__(self, interface: str = 'can0', verbose: bool = False,
                 odi_class: int = None, target_device: int = 0xFF):
        self.interface = interface
        self.verbose = verbose
        self.odi_class = odi_class if odi_class is not None else ODIClass.EEPROM.value
        self.target_device = target_device  # 0xFF=broadcast, 0x00=PM, 0x01=JSM, etc.
        self.socket = None
        self.state = ProgrammerState()
        self._heartbeat_thread = None
        self._heartbeat_stop = threading.Event()
        self._receive_thread = None
        self._receive_stop = threading.Event()
        self._response_event = threading.Event()
        self._response_data = None

    def _log(self, msg: str) -> None:
        """Print verbose log message."""
        if self.verbose:
            print(f"[PROG] {msg}")

    def _odi_bytes(self) -> Tuple[int, int]:
        """Return (low, high) bytes for current ODI class encoding.

        ODI class is encoded little-endian in bytes 1-2 of POP Quick frames:
          EEPROM (0x0100) -> 0x00, 0x01
          RAM    (0x0120) -> 0x20, 0x01
          ROM    (0x0130) -> 0x30, 0x01
          SLOT   (0x0200) -> 0x00, 0x02
        Source: DongleInterface.dll ODI_CLASS encoding.
        """
        return (self.odi_class & 0xFF, (self.odi_class >> 8) & 0xFF)

    def _error_name(self, code: int) -> str:
        """Look up POP error code name from DongleInterface.dll RB_ERROR enum."""
        for e in RBError:
            if e.value == code:
                return e.name
        return f"UNKNOWN(0x{code:02X})"

    def connect(self) -> bool:
        """
        Open CAN socket and connect to the bus.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
            self.socket.bind((self.interface,))
            self.socket.setblocking(False)
            self._log(f"Connected to {self.interface}")
            return True
        except socket.error as e:
            print(f"Error: Failed to open {self.interface}: {e}")
            # Try vcan
            try:
                self.socket.bind((f'v{self.interface}',))
                self._log(f"Connected to v{self.interface}")
                return True
            except:
                return False

    def disconnect(self) -> None:
        """Close CAN socket and stop threads."""
        self._heartbeat_stop.set()
        self._receive_stop.set()

        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1)
        if self._receive_thread:
            self._receive_thread.join(timeout=1)

        if self.socket:
            self.socket.close()
            self.socket = None

        self.state.connected = False
        self._log("Disconnected")

    def _send_frame(self, frame_str: str) -> bool:
        """Send a CAN frame."""
        try:
            frame = build_frame(frame_str)
            self.socket.send(frame)
            self._log(f"TX: {frame_str}")
            return True
        except socket.error as e:
            self._log(f"TX Error: {e}")
            return False

    def _receive_frame(self, timeout: float = 0.1) -> Optional[str]:
        """
        Receive a CAN frame with timeout.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Frame string or None if timeout.
        """
        import select
        ready, _, _ = select.select([self.socket], [], [], timeout)
        if ready:
            try:
                frame, _ = self.socket.recvfrom(16)
                frame_str = dissect_frame(frame)
                self._log(f"RX: {frame_str}")
                return frame_str
            except socket.error:
                return None
        return None

    def _wait_for_response(self, expected_id: int, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for a specific response frame.

        Args:
            expected_id: Expected CAN ID (3 hex digits).
            timeout: Timeout in seconds.

        Returns:
            Frame data bytes or None if timeout.
        """
        start = time.time()
        expected_id_str = f"{expected_id:03X}"

        while time.time() - start < timeout:
            frame_str = self._receive_frame(timeout=0.05)
            if frame_str:
                frame_id = frame_str.split('#')[0]
                if frame_id.upper() == expected_id_str:
                    data_str = frame_str.split('#')[1]
                    if data_str and not data_str.endswith('R'):
                        return bytes.fromhex(data_str)
        return None

    def announce_presence(self) -> bool:
        """
        Announce programmer presence on the bus.

        Sends the 0x7A0 announcement frame.

        Returns:
            True if successful.
        """
        self._log("Announcing programmer presence...")
        return self._send_frame("7A0#")

    def send_heartbeat(self) -> bool:
        """
        Send programmer heartbeat/presence poll.

        Returns:
            True if acknowledgment received.
        """
        # Send presence request: 78F#422000FF00000000
        self._send_frame("78F#422000FF00000000")

        # Wait for acknowledgment: 793#2F2000FF...
        response = self._wait_for_response(0x793, timeout=0.5)
        if response and len(response) >= 1 and response[0] == POPCommand.PRESENCE_ACK.value:
            self.state.last_response_time = time.time()
            return True
        return False

    def _heartbeat_loop(self) -> None:
        """Background heartbeat thread."""
        while not self._heartbeat_stop.is_set():
            if self.state.connected:
                self.send_heartbeat()
            self._heartbeat_stop.wait(0.2)  # 200ms heartbeat interval

    def enable_programmer_mode(self) -> bool:
        """
        Enable programmer mode on the R-Net bus.

        This is the main "handshake" to enter programmer mode:
        1. Announce presence (7A0#)
        2. Establish heartbeat (78F#42.../793#2F...)

        Returns:
            True if programmer mode enabled successfully.
        """
        print("Enabling programmer mode...")

        # Step 1: Announce presence
        self.announce_presence()
        time.sleep(0.1)

        # Step 2: Send initial heartbeat and verify response
        for attempt in range(3):
            if self.send_heartbeat():
                self.state.connected = True
                print("Programmer mode enabled!")

                # Start background heartbeat
                self._heartbeat_stop.clear()
                self._heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop, daemon=True
                )
                self._heartbeat_thread.start()

                return True

            time.sleep(0.2)

        print("Warning: No response to programmer handshake")
        print("Continuing anyway (device may not support programmer mode)")
        self.state.connected = True
        return True  # Continue even without response for passive monitoring

    def _read_chunk(self, address: int) -> Optional[bytes]:
        """
        Read a single 4-byte chunk from a memory address.

        Frame format (from DongleInterface.dll POP Quick protocol):
          SET_ADDRESS: 78F#[CMD][ODI_LO][ODI_HI][DEV_ID][ADDR_LO][ADDR_HI][00][00]
          START_READ:  78F#[CMD][ODI_LO][ODI_HI][DEV_ID][READ_MODE][00][00][00]
          Response:    793#[4F][ODI_LO][ODI_HI][DEV_ID][D0][D1][D2][D3]

        Returns:
            4 bytes of data or None on failure.
        """
        addr_lo = address & 0xFF
        addr_hi = (address >> 8) & 0xFF
        odi_lo, odi_hi = self._odi_bytes()
        dev = self.target_device

        # Step 1: Set read address
        set_addr = f"78F#{POPCommand.SET_ADDRESS.value:02X}{odi_lo:02X}{odi_hi:02X}{dev:02X}{addr_lo:02X}{addr_hi:02X}0000"
        self._send_frame(set_addr)
        time.sleep(INTER_FRAME_DELAY)

        # Step 2: Start read (POP_READ_MODE=0x17 in byte 4)
        read_cmd = f"78F#{POPCommand.START_READ.value:02X}{odi_lo:02X}{odi_hi:02X}{dev:02X}{POP_READ_MODE:02X}000000"
        self._send_frame(read_cmd)

        # Step 3: Wait for response
        response = self._wait_for_response(PROGRAMMER_RESPONSE_ID, timeout=DONGLE_TIMEOUT)

        if response and len(response) >= 8:
            cmd = response[0]
            if cmd == POPCommand.READ_RESPONSE.value:
                # Wait for COMPLETE frame
                self._wait_for_response(PROGRAMMER_RESPONSE_ID, timeout=0.2)
                return bytes(response[4:8])
            elif cmd == POPCommand.ERROR.value:
                err_code = response[4] if len(response) > 4 else 0
                self._log(f"Read error at 0x{address:04X}: {self._error_name(err_code)}")
                return None

        self._log(f"No response for address 0x{address:04X}")
        return None

    def read_address(self, address: int, size: int = 1) -> Optional[bytes]:
        """
        Read data from a memory address with retry logic.

        Retries up to READ_RETRY_COUNT (3) times per chunk, matching
        the retry behavior in DongleInterface.dll.

        Args:
            address: Memory address (16-bit).
            size: Number of bytes to read.

        Returns:
            Data bytes or None if read failed.
        """
        result = bytearray()

        for offset in range(0, size, 4):
            current_addr = address + offset
            bytes_to_take = min(4, size - offset)
            data = None

            for retry in range(READ_RETRY_COUNT):
                data = self._read_chunk(current_addr)
                if data is not None:
                    break
                if retry < READ_RETRY_COUNT - 1:
                    self._log(f"Retry {retry + 1}/{READ_RETRY_COUNT} for 0x{current_addr:04X}")
                    time.sleep(RECONNECT_TIMEOUT)

            if data is None:
                self._log(f"Read failed at 0x{current_addr:04X} after {READ_RETRY_COUNT} attempts")
                return None

            result.extend(data[:bytes_to_take])

        return bytes(result) if result else None

    def write_address(self, address: int, data: bytes) -> bool:
        """
        Write data to a memory address.

        Frame format (from DongleInterface.dll POP Quick protocol):
          SET_ADDRESS:  78F#[CMD][ODI_LO][ODI_HI][DEV_ID][ADDR_LO][ADDR_HI][00][00]
          START_WRITE:  78F#[CMD][ODI_LO][ODI_HI][DEV_ID][D0][D1][D2][D3]
          Response:     793#[0F][ODI_LO][ODI_HI][DEV_ID][STATUS][00][00][00]

        Args:
            address: Memory address (16-bit).
            data: Data bytes to write (max 4 bytes per operation).

        Returns:
            True if write successful.
        """
        addr_lo = address & 0xFF
        addr_hi = (address >> 8) & 0xFF
        odi_lo, odi_hi = self._odi_bytes()
        dev = self.target_device

        write_data = data[:4].ljust(4, b'\x00')
        data_hex = write_data.hex().upper()

        # Step 1: Set write address
        set_addr = f"78F#{POPCommand.SET_ADDRESS.value:02X}{odi_lo:02X}{odi_hi:02X}{dev:02X}{addr_lo:02X}{addr_hi:02X}0000"
        self._send_frame(set_addr)
        time.sleep(INTER_FRAME_DELAY)

        # Step 2: Send write command
        write_frame = f"78F#{POPCommand.START_WRITE.value:02X}{odi_lo:02X}{odi_hi:02X}{dev:02X}{data_hex}"
        self._send_frame(write_frame)

        # Step 3: Wait for acknowledgment
        response = self._wait_for_response(PROGRAMMER_RESPONSE_ID, timeout=DONGLE_TIMEOUT)

        if response and len(response) >= 1:
            cmd = response[0]
            if cmd == POPCommand.WRITE_RESPONSE.value:
                # Wait for COMPLETE
                self._wait_for_response(PROGRAMMER_RESPONSE_ID, timeout=0.2)
                self._log(f"Write successful at 0x{address:04X}")
                return True
            elif cmd == POPCommand.ERROR.value:
                err_code = response[4] if len(response) > 4 else 0
                self._log(f"Write error at 0x{address:04X}: {self._error_name(err_code)}")
                return False

        self._log(f"No response for write at 0x{address:04X}")
        return False

    def dump_memory(self, start: int, end: int,
                    progress_callback: Optional[Callable[[int, int], None]] = None) -> bytes:
        """
        Dump memory range.

        Args:
            start: Start address.
            end: End address.
            progress_callback: Optional callback(current, total) for progress.

        Returns:
            Dumped memory bytes.
        """
        result = bytearray()
        total = end - start

        for addr in range(start, end, 4):
            data = self.read_address(addr, min(4, end - addr))
            if data:
                result.extend(data)
            else:
                # Fill with 0xFF on read failure
                result.extend(b'\xFF' * min(4, end - addr))

            if progress_callback:
                progress_callback(addr - start, total)

        return bytes(result)

    def monitor(self, duration: float = 0, filter_ids: Optional[List[int]] = None) -> None:
        """
        Monitor CAN bus traffic.

        Args:
            duration: Duration in seconds (0 = forever).
            filter_ids: Optional list of frame IDs to filter.
        """
        print("Monitoring CAN bus... (Ctrl+C to stop)")
        start = time.time()

        try:
            while duration == 0 or (time.time() - start) < duration:
                frame_str = self._receive_frame(timeout=0.5)
                if frame_str:
                    frame_id = int(frame_str.split('#')[0], 16)
                    if filter_ids is None or frame_id in filter_ids:
                        timestamp = time.time() - start
                        print(f"[{timestamp:8.3f}] {frame_str}")
        except KeyboardInterrupt:
            print("\nStopped.")


# ============================================================================
# CLI Commands
# ============================================================================

def _make_programmer(args) -> RNetProgrammer:
    """Create programmer from CLI args with ODI class and target device."""
    odi_map = {
        'eeprom': ODIClass.EEPROM.value, 'ram': ODIClass.RAM.value,
        'rom': ODIClass.ROM.value, 'slot': ODIClass.SLOT.value,
        'port': ODIClass.PORT.value, 'adc': ODIClass.ADC.value,
    }
    odi = odi_map.get(getattr(args, 'odi_class', 'eeprom'), ODIClass.EEPROM.value)
    target = int(getattr(args, 'target', '0xFF'), 16)
    return RNetProgrammer(args.interface, verbose=args.verbose,
                          odi_class=odi, target_device=target)


def cmd_enable(args):
    """Enable programmer mode."""
    prog = _make_programmer(args)
    if not prog.connect():
        return 1

    try:
        if prog.enable_programmer_mode():
            print("\nProgrammer mode active. Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("Failed to enable programmer mode")
            return 1
    finally:
        prog.disconnect()

    return 0


def cmd_read(args):
    """Read from memory address."""
    prog = _make_programmer(args)
    if not prog.connect():
        return 1

    try:
        if not prog.enable_programmer_mode():
            return 1

        address = int(args.address, 16) if args.address.startswith('0x') else int(args.address)
        size = int(args.size, 16) if args.size.startswith('0x') else int(args.size)

        print(f"Reading {size} bytes from 0x{address:04X}...")
        data = prog.read_address(address, size)

        if data:
            print(f"\nData at 0x{address:04X}:")
            for i in range(0, len(data), 16):
                hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                print(f"  {address+i:04X}: {hex_str:<48} {ascii_str}")

            if args.output:
                with open(args.output, 'wb') as f:
                    f.write(data)
                print(f"\nSaved to {args.output}")
        else:
            print("Read failed")
            return 1

    finally:
        prog.disconnect()

    return 0


def cmd_write(args):
    """Write to memory address."""
    prog = _make_programmer(args)
    if not prog.connect():
        return 1

    try:
        if not prog.enable_programmer_mode():
            return 1

        address = int(args.address, 16) if args.address.startswith('0x') else int(args.address)

        if args.data:
            data = bytes.fromhex(args.data)
        elif args.input:
            with open(args.input, 'rb') as f:
                data = f.read()
        else:
            print("Error: Must specify --data or --input")
            return 1

        print(f"Writing {len(data)} bytes to 0x{address:04X}...")

        for i in range(0, len(data), 4):
            chunk = data[i:i+4]
            if not prog.write_address(address + i, chunk):
                print(f"Write failed at 0x{address+i:04X}")
                return 1

        print("Write complete")

    finally:
        prog.disconnect()

    return 0


def cmd_dump(args):
    """Dump memory range to file."""
    prog = _make_programmer(args)
    if not prog.connect():
        return 1

    try:
        if not prog.enable_programmer_mode():
            return 1

        start = int(args.start, 16) if args.start.startswith('0x') else int(args.start)
        end = int(args.end, 16) if args.end.startswith('0x') else int(args.end)

        print(f"Dumping memory 0x{start:04X} - 0x{end:04X} ({end-start} bytes)...")

        def progress(current, total):
            pct = (current / total) * 100 if total > 0 else 0
            print(f"\r  Progress: {pct:.1f}% ({current}/{total} bytes)", end='', flush=True)

        data = prog.dump_memory(start, end, progress_callback=progress)
        print()

        with open(args.output, 'wb') as f:
            f.write(data)

        print(f"Saved {len(data)} bytes to {args.output}")

    finally:
        prog.disconnect()

    return 0


def cmd_monitor(args):
    """Monitor CAN bus traffic."""
    prog = _make_programmer(args)
    if not prog.connect():
        return 1

    try:
        # Enable programmer mode if requested
        if args.programmer:
            prog.enable_programmer_mode()

        # Parse filter IDs
        filter_ids = None
        if args.filter:
            filter_ids = [int(x, 16) for x in args.filter.split(',')]

        prog.monitor(duration=args.duration, filter_ids=filter_ids)

    finally:
        prog.disconnect()

    return 0


def cmd_handshake(args):
    """Test programmer handshake only."""
    prog = RNetProgrammer(args.interface, verbose=True)
    if not prog.connect():
        return 1

    try:
        print("Testing programmer handshake...")
        print()
        print("Step 1: Announce presence (7A0#)")
        prog.announce_presence()
        time.sleep(0.2)

        print()
        print("Step 2: Send heartbeat (78F#422000FF00000000)")
        if prog.send_heartbeat():
            print("  Response received (793#2F...)")
            print()
            print("Handshake successful!")
        else:
            print("  No response")
            print()
            print("Handshake: No response (device may not support POP protocol)")

    finally:
        prog.disconnect()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="R-Net POP Programmer Mode Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test programmer handshake
  %(prog)s handshake

  # Enable programmer mode and keep alive
  %(prog)s enable

  # Read 256 bytes from address 0x0000
  %(prog)s read 0x0000 0x100

  # Write hex data to address
  %(prog)s write 0x0100 --data DEADBEEF

  # Dump memory range to file
  %(prog)s dump 0x0000 0x1000 -o dump.bin

  # Monitor bus traffic
  %(prog)s monitor

  # Monitor only programmer frames
  %(prog)s monitor --filter 78F,793,7A0

Programmer Handshake:
  1. Send 7A0# (programmer presence announcement)
  2. Send 78F#422000FF00000000 (heartbeat request)
  3. Expect 793#2F2000FF00000000 (heartbeat response)
  4. Repeat heartbeat every ~200ms to maintain connection

Read Protocol:
  1. 78F#830001ffXXXX0000  - Set read address (XXXX little-endian)
  2. 78F#030001ff17000000  - Start read operation
  3. 793#4f0001ff[data]    - Read response
  4. 793#8f0001ff00000000  - Operation complete
"""
    )

    parser.add_argument('-i', '--interface', default='can0',
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

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # handshake command
    p_handshake = subparsers.add_parser('handshake', help='Test programmer handshake')
    p_handshake.set_defaults(func=cmd_handshake)

    # enable command
    p_enable = subparsers.add_parser('enable', help='Enable programmer mode')
    p_enable.set_defaults(func=cmd_enable)

    # read command
    p_read = subparsers.add_parser('read', help='Read from memory address')
    p_read.add_argument('address', help='Start address (hex or decimal)')
    p_read.add_argument('size', help='Number of bytes to read')
    p_read.add_argument('-o', '--output', help='Output file')
    p_read.set_defaults(func=cmd_read)

    # write command
    p_write = subparsers.add_parser('write', help='Write to memory address')
    p_write.add_argument('address', help='Start address (hex or decimal)')
    p_write.add_argument('--data', help='Hex data to write')
    p_write.add_argument('--input', help='Input file')
    p_write.set_defaults(func=cmd_write)

    # dump command
    p_dump = subparsers.add_parser('dump', help='Dump memory range to file')
    p_dump.add_argument('start', help='Start address')
    p_dump.add_argument('end', help='End address')
    p_dump.add_argument('-o', '--output', required=True, help='Output file')
    p_dump.set_defaults(func=cmd_dump)

    # monitor command
    p_monitor = subparsers.add_parser('monitor', help='Monitor CAN bus traffic')
    p_monitor.add_argument('--duration', type=float, default=0,
                           help='Duration in seconds (0=forever)')
    p_monitor.add_argument('--filter', help='Comma-separated frame IDs to filter (hex)')
    p_monitor.add_argument('--programmer', action='store_true',
                           help='Enable programmer mode before monitoring')
    p_monitor.set_defaults(func=cmd_monitor)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
