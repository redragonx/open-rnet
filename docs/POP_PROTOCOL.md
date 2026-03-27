# POP (Parameter Object Protocol) Specification

Technical specification for the R-Net Parameter Object Protocol (POP), the official configuration protocol used by the R-Net Programmer to read and write wheelchair device parameters over CAN bus.

## Overview

POP (Parameter Object Protocol) is the native R-Net configuration protocol implemented by all R-Net devices (Power Modules, Joystick Modules, Bluetooth Modules, etc.) for parameter read/write operations. It operates on top of a transport layer internally called **REBUS** (implemented as the `CRebusInterface` class in the DLL).

**Key facts:**
- Used by the R-Net Programmer hardware (USB dongle, part number **D50610**) and RNet Programmer5 OEM software
- Supports both single-frame ("quick") and multi-frame ("segmented") transactions
- Addresses devices by node number (0x0-0xF), supporting up to 16 nodes on one R-Net network
- Internal constant `MAX_NODES = 20`, but POP addressing supports 16 nodes (4-bit node field)
- CAN 2.0B @ 125 Kbps, uses both standard (11-bit) and extended (29-bit) frame IDs
- No encryption or cryptographic authentication at the protocol level

**Source:** Reverse engineering of `DongleInterface.dll` v3.0.0.0 and `RNet Programmer5 OEM.exe` v5.7.0, (C) PG Drives Technology 2008.

---

## POP Quick Protocol (Single-Frame)

The "quick" protocol uses standard 11-bit CAN IDs for single-frame request/response transactions. This is used for reading or writing individual parameters.

### CAN IDs

| Direction | CAN ID | Format |
|-----------|--------|--------|
| Request (Programmer -> Device) | `0x780 + node` | Standard 11-bit |
| Response (Device -> Programmer) | `0x790 + node` | Standard 11-bit |

Where `node` is the device's slot number on the R-Net network (0x0 through 0xF).

**Examples:**
- Request to node 0 (Power Module): `0x780`
- Response from node 0: `0x790`
- Request to node 1 (JSM): `0x781`
- Response from node 1: `0x791`
- Request to node 0xF (R-Net Programmer): `0x78F`
- Response to R-Net Programmer: `0x793` (when programmer is slot 3)

### Frame Data Structure

```
Byte 0:    [TC:2][ODI_CLASS_HI:6]
Byte 1:    [ODI_CLASS_LO:8]
Bytes 2-3: Address (16-bit, big-endian)
Bytes 4-7: Data (up to 4 bytes)
```

**Transfer Code (TC) encoding:**
- The transfer code occupies the top 2 bits of byte 0
- Mask: `0x3F` applied to isolate ODI class bits
- Shift: TC is shifted left by 6 bits into byte 0
- Formula: `byte0 = (tc << 6) | (odi_class >> 8)`

**Quick protocol transfer codes (2-bit, encoded in byte 0):**

| Encoded Value | Meaning |
|---------------|---------|
| `0x00` | Upload request (read from device) |
| `0x01` | Upload response (device returns data) |
| `0x02` | Download request (write to device) |
| `0x03` | Download response (device acknowledges write) |

### Example Transaction: Read Parameter

Read a parameter at ODI class EEPROM (0x0100), address 0x0050, from node 0:

```
TX: 0x780#03 00 00 50 00 00 00 00    ; Upload request: TC=0x00, class=0x0100, addr=0x0050
RX: 0x790#41 00 00 50 XX XX XX XX    ; Upload response: TC=0x01, data in bytes 4-7
```

### Example Transaction: Write Parameter

Write value 0x32 to EEPROM address 0x0050 on node 0:

```
TX: 0x780#83 00 00 50 32 00 00 00    ; Download request: TC=0x02, class=0x0100, addr=0x0050, data=0x32
RX: 0x790#C1 00 00 50 00 00 00 00    ; Download response: TC=0x03, acknowledge
```

---

## POP Segmented Protocol (Multi-Frame)

The segmented protocol uses extended 29-bit CAN IDs for multi-frame bulk transfers. This is the primary mechanism for reading and writing entire device configuration files (repository slots).

### CAN ID Construction

**Request (Programmer -> Device):**
```
ID = 0x1E400000 | (node << 15) | (tc << 18)
```

**Response (Device -> Programmer):**
```
ID = 0x1E000000 | (node << 15) | (tc << 18)
```

### Bit Field Layout (29-bit Extended ID)

```
Bits 28-24: 0x0F (fixed prefix = 0b01111)
Bit  22:    0x1 for request, 0x0 for response (0x1E4 vs 0x1E0)
Bits 21-18: Transfer code (4 bits)
Bits 17-15: Node number (3 bits in segmented mode)
Bits 14-0:  Reserved / segment addressing
```

### Bitmask Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `POP_SEG_NODE_MASK` | `0x00030000` | Isolate node bits |
| `POP_SEG_NODE_SHIFT` | `15` | Shift to extract node |
| `POP_SEG_TC_MASK` | `0x003C0000` | Isolate transfer code bits |
| `POP_SEG_TC_SHIFT` | `18` | Shift to extract TC |
| `SEGMENT_MASK` | `0x7F` | 7-bit segment number (bits 6-0 of data byte 0) |
| `CRC_BIT` | `0x80` | Bit 7 of segment byte; set = CRC follows |

### Segment Data Structure

```
Byte 0:    [CRC_BIT:1][SEGMENT_NUM:7]
Bytes 1-7: Payload data (7 bytes per segment)
```

- Segment numbers start at 0 and increment
- The `CRC_BIT` flag in the final segment indicates that a CRC-16 value is appended
- Maximum payload per segment: 7 bytes
- Total transfer size is negotiated in the initial handshake frame

### Segmented Transfer Flow

**Upload (Read from device):**
```
1. Programmer sends TC_ULS_REQ (segmented upload request) with ODI class + address + size
2. Device responds with TC_ULS_RES segments (segment 0, 1, 2, ...)
3. Final segment has CRC_BIT set if CRC verification is enabled
4. Programmer sends TC_END to acknowledge completion
```

**Download (Write to device):**
```
1. Programmer sends TC_DLS_REQ (segmented download request) with ODI class + address + size
2. Device acknowledges readiness
3. Programmer sends TC_DLS_RES segments (segment 0, 1, 2, ...)
4. Final segment includes CRC if enabled
5. Device sends TC_END or error code
```

---

## Transfer Codes

Transfer codes identify the type and direction of a POP transaction. In quick protocol they occupy 2 bits; in segmented protocol they occupy 4 bits.

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| `0x01` | `TC_UL_RES` | Device -> Programmer | Upload (read) response, single-frame |
| `0x03` | `TC_UL_REQ` | Programmer -> Device | Upload (read) request, single-frame |
| `0x04` | `TC_DLS_REQ` | Programmer -> Device | Download (write) segmented request |
| `0x05` | `TC_DL_REQ` | Programmer -> Device | Download (write) request, single-frame |
| `0x07` | `TC_DL_RES` | Device -> Programmer | Download (write) response, single-frame |
| `0x08` | `TC_DLS_RES` | Device -> Programmer | Download (write) segmented response |
| `0x09` | `TC_ULS_REQ` | Programmer -> Device | Upload (read) segmented request |
| `0x0A` | `TC_ULS_RES` | Device -> Programmer | Upload (read) segmented response |
| `0x0B` | `TC_ABORT` | Either | Transaction abort (error or cancel) |
| `0x0C` | `TC_END` | Either | Transaction end (successful completion) |
| `0x0F` | `TC_ILLEGAL` | - | Invalid/sentinel transfer code |

**Terminology note:** "Upload" means reading data FROM the device TO the programmer. "Download" means writing data FROM the programmer TO the device. This follows the device's perspective (device uploads its data, device downloads new data).

---

## ODI (Object Dictionary Interface) Classes

ODI classes define the memory region being accessed on the target device. Each class maps to a different type of storage or peripheral.

| Value | Name | Description |
|-------|------|-------------|
| `0x0100` | `EEPROM` | Non-volatile configuration storage. Primary target for parameter read/write. Persists across power cycles. |
| `0x0110` | `PORT` | I/O port registers. Direct hardware port access. |
| `0x0120` | `RAM` | Volatile memory. Runtime variables, lost on power cycle. |
| `0x0130` | `ROM` | Read-only memory. Firmware, calibration data, factory constants. |
| `0x0140` | `ADC` | Analog-to-digital converter registers. Live sensor readings. |
| `0x0200` | `SLOT` | Device slot/file storage. Repository file system access. |
| `0xFFFFFF` | `SENTINEL` | Invalid/uninitialized sentinel value. |

**Access functions (from DLL exports):**

| Function | Purpose |
|----------|---------|
| `ReadDataODI(node, class, address, size)` | Read data bytes from an ODI region |
| `WriteDataODI(node, class, address, data, size)` | Write data bytes to an ODI region |
| `ReadLocationODI(node, class, address)` | Read a single location (4-byte value) |
| `WriteLocationODI(node, class, address, value)` | Write a single location (4-byte value) |

---

## Repository System

R-Net devices organize their configuration data using a **repository** model. The repository is a file-system-like abstraction over device EEPROM, with named slots containing typed configuration files.

### Repository Ownership

Before reading or writing device configuration, the programmer must **acquire** the repository:

1. Programmer sends acquisition request to target node
2. Device grants ownership (or returns `RB_REP_TAKEN` if another programmer holds it)
3. Programmer maintains ownership for the duration of the session
4. Ownership is released explicitly or on timeout

Retry delays are implemented to handle contention when multiple tools attempt access.

### Slot Structure

Each repository slot contains:

| Field | Description |
|-------|-------------|
| Location | Address within device EEPROM |
| Size | Total size of the file in bytes |
| File Version | Version number for compatibility checking |
| File Type | Identifies the data format / schema |
| File Attributes | Read-only, hidden, system flags |

### File Data Transfers

- All file data transfers support **CRC-16 verification** for data integrity
- The CRC covers the payload bytes and is appended to the final segment when `CRC_BIT` is set

### Differential Downloads

For efficiency, the programmer supports **differential downloads** where only changed bytes are transmitted rather than the entire file:

| Constant | Purpose |
|----------|---------|
| `DIFFERENCING_LIMIT_COUNT` | Max number of changed byte ranges before falling back to full download |
| `DIFFERENCING_LIMIT_PERCENT` | If changed bytes exceed this percentage of total, use full download |
| `DIFFERENCING_LIMIT_SIZE` | Minimum file size for differential download to be worthwhile |

The `CFileData` class manages diffing between the current device contents and the desired configuration, computing change regions and deciding whether to use differential or full transfer.

---

## USB Dongle Protocol

The R-Net Programmer USB dongle (part **D50610**) bridges USB to CAN bus. It uses an **FTDI chip** (FT232 family) and appears with the device description `"RNet Dongle"`.

### Physical Layer

- FTDI USB-to-serial chip (FT232 family)
- Device description string: `"RNet Dongle"`
- Latency timer: 1ms (`LATENCY_TIMER`)

### Framing

USB messages use byte-stuffing with control characters:

| Byte | Name | Purpose |
|------|------|---------|
| `0x02` | `STX` | Start of frame |
| `0x03` | `ETX` | End of frame |
| `0x10` | `DLE` | Data Link Escape (stuffing prefix) |

**Byte-stuffing rules:**
- If a data byte equals STX, ETX, or DLE, it is preceded by a DLE byte
- Frame format: `STX [escaped payload] ETX`

### Message Sizes

| Constant | Value | Description |
|----------|-------|-------------|
| `USB_MSG_LEN` | 32 bytes | Maximum USB message length (after framing) |
| V1 raw message | 21 bytes | Protocol version 1 raw payload |
| V2 raw message | 24 bytes | Protocol version 2 raw payload |

The dongle supports both V1 and V2 connection protocols; V2 adds fields for extended CAN ID support and additional status.

### USB Command Categories

| Category | Code | Purpose | Sub-commands |
|----------|------|---------|--------------|
| `USBCMD_POP` | - | POP protocol relay | `CLIENT_R`, `CLIENT_W`, `SERVER_R`, `SERVER_W` |
| `USBCMD_SERVICE` | - | Device status polling | `PARAM_R`, `PARAM_W`, `FAULT_R`, `FAULT_W`, `KEYS_R`, `RTC_R`, `XY_CNT_R`, `XY_CNT_W` |
| `USBCMD_FILTER` | - | CAN bus filtering | `MODE_R`, `MODE_W`, `FLT_R`, `FLT_W` |
| `USBCMD_MODES` | - | Operating modes | `AUTOTX_R`, `AUTOTX_W`, `ERRS_R`, `ERRS_W`, `PING` |
| `USBCMD_CONDUIT` | - | Raw CAN passthrough | `R` (read), `W` (write) |
| `USBCMD_CPU` | - | Dongle CPU control | `STATUS_R`, `FWVER_R`, `RESET_W`, `CANSLP_R`, `CANSLP_W`, `FLASH_R`, `FLASH_W`, `PASSTHRU_R`, `PASSTHRU_W`, `SLP_DISABLE_R`, `SLP_DISABLE_W` |
| `USBCMD_E2` | - | Dongle EEPROM | `ACCESS_R`, `ACCESS_W` |
| `USBCMD_LED` | - | Dongle LED control | `TIMEOUT_R`, `TIMEOUT_W` |

**Command flow:**
1. Host builds a USB command frame with category + sub-command + payload
2. Frame is byte-stuffed and sent over USB serial
3. Dongle processes command (CAN send, CAN receive, internal operation)
4. Dongle returns response in same framing format

### Key Command Details

**USBCMD_POP:** The core protocol relay. `CLIENT_W` sends a POP request frame onto CAN; `CLIENT_R` reads a POP response from CAN. `SERVER_R/W` are used when the dongle acts as a POP server (rare).

**USBCMD_CONDUIT:** Raw CAN frame passthrough. `W` sends an arbitrary CAN frame; `R` receives the next CAN frame matching current filters. Used for non-POP communication (heartbeats, diagnostics).

**USBCMD_FILTER:** Configures the dongle's CAN acceptance filters so only relevant frames are forwarded over USB, reducing USB bandwidth.

**USBCMD_CPU:** Dongle management. `FWVER_R` reads dongle firmware version. `RESET_W` resets the dongle. `CANSLP_R/W` controls CAN transceiver sleep. `FLASH_R/W` is used for dongle firmware updates. `PASSTHRU_R/W` configures transparent CAN-to-USB bridging.

---

## Timing Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `QCK_TIMEOUT` | 1000 ms | Quick (single-frame) POP transaction timeout |
| `SEG_TIMEOUT` | 100 ms | Segmented POP timeout per segment |
| `RECONNECT_TIMEOUT` | 200 ms | Delay before dongle reconnect attempt |
| `READ_RETRY_COUNT` | 3 | Maximum retries for failed read operations |
| `DONGLE_TIMEOUT` | 500 ms | Dongle USB response timeout |
| `DONGLE_CXTN_TIMEOUT` | 900 ms | Dongle initial connection timeout |
| `CANMSG_TIMEOUT` | 10000 ms | CAN message timeout (overall transaction) |
| `FILTER_RESET_TIMEOUT` | 2500 ms | Timeout for CAN filter reset operation |
| `USB_READ_TIMEOUT` | 250 ms | USB serial read timeout |
| `SLEEP_TIMEOUT_DELTA` | 50 ms | Granularity of internal sleep timers |
| `LATENCY_TIMER` | 1 ms | FTDI USB latency timer setting |

**Timing notes:**
- Segmented transfers use the per-segment timeout (`SEG_TIMEOUT`), not the quick timeout
- Failed reads are retried up to `READ_RETRY_COUNT` times before reporting error
- The `CANMSG_TIMEOUT` (10 seconds) is the overall watchdog for any CAN transaction

---

## Connection State Machine

The DLL maintains a connection state machine tracking the lifecycle from USB detection through active R-Net communication.

| State | Name | Description |
|-------|------|-------------|
| 0 | `CXTN_NONE` | No connection. Dongle not detected. |
| 1 | `CXTN_INIT` | Initializing. USB enumeration in progress. |
| 2 | `CXTN_DONGLE` | USB dongle detected and opened. FTDI communication established. |
| 3 | `CXTN_CAN` | CAN bus connection verified. Dongle can send/receive CAN frames. |
| 4 | `CXTN_RNET` | R-Net network active. At least one R-Net device responding. |
| 5 | `CXTN_UPLOAD` | Upload (read) operation in progress. |
| 6 | `CXTN_DOWNLOAD` | Download (write) operation in progress. |
| 7 | `CXTN_BAD_FW` | Dongle firmware version mismatch. Update required. |

**Typical progression:**
```
CXTN_NONE -> CXTN_INIT -> CXTN_DONGLE -> CXTN_CAN -> CXTN_RNET -> CXTN_UPLOAD/DOWNLOAD
```

**Error transitions:**
- Any state can transition to `CXTN_NONE` on USB disconnect
- `CXTN_BAD_FW` is entered from `CXTN_DONGLE` when firmware version check fails
- Upload/download states return to `CXTN_RNET` on completion or error

---

## Error Codes (RB_ERROR)

POP operations return error codes from the `RB_ERROR` enumeration:

| Code | Name | Description |
|------|------|-------------|
| `0x00` | `RB_NONE` | Success. No error. |
| - | `RB_ABORT` | Transaction was aborted by either side. |
| - | `RB_CANCELLED` | Operation cancelled by user or software. |
| - | `RB_COMMS` | Communication failure (USB or CAN). |
| - | `RB_NO_CONNECTION` | No connection to dongle or device. |
| - | `RB_REP_TAKEN` | Repository already acquired by another programmer. |
| - | `RB_CHKSUM` | CRC/checksum mismatch on received data. |
| - | `RB_SEG_BUSY` | Segmented transfer engine busy (previous transfer not complete). |
| - | `RB_SEG_ERR` | Segmented transfer error (segment out of order, missing). |
| - | `RB_SEG_REJ` | Segmented transfer rejected by device. |
| - | `RB_SEG_SIZE` | Segmented transfer size mismatch. |
| - | `RB_INV_NODE` | Invalid node number (out of range 0-15). |
| - | `RB_INV_PARM` | Invalid parameter (ODI class/address not recognized). |
| - | `RB_PRODID` | Product ID mismatch (wrong device type for this configuration). |

**Error handling behavior:**
- On `RB_COMMS`, the DLL attempts reconnection after `RECONNECT_TIMEOUT`
- On `RB_REP_TAKEN`, the software retries with exponential backoff
- On `RB_CHKSUM`, the segment or transaction is retried up to `READ_RETRY_COUNT` times
- On `RB_SEG_*` errors, the segmented transfer is aborted and may be retried from the beginning

---

## Notification CAN IDs

R-Net devices broadcast notifications on specific CAN IDs when state changes occur. The programmer monitors these to keep its view of the network current.

| CAN ID | Name | Type | Purpose |
|--------|------|------|---------|
| `0x42D` | `SLOT_CHANGED_STD_ID` | Standard 11-bit | Device slot assignment changed on network |
| `0x431` | `MODE_CHANGE_ID` | Standard 11-bit | Operating mode changed (e.g., Drive -> Seating) |
| `0x436` | `PROFILE_CHANGE_ID` | Standard 11-bit | Speed profile changed (e.g., Indoor -> Outdoor) |
| `0x0006C01F` | `CAN_ID_SLEEP_RESET` | Extended 29-bit | Sent periodically to prevent CAN bus sleep/shutdown |

**Usage:**
- The programmer monitors `SLOT_CHANGED_STD_ID` to detect when devices join or leave the network
- `MODE_CHANGE_ID` and `PROFILE_CHANGE_ID` trigger re-read of active configuration
- `CAN_ID_SLEEP_RESET` must be sent periodically during long programming sessions to prevent the R-Net network from entering sleep mode

---

## Flash-Over-CAN

The POP protocol supports firmware updates to R-Net devices delivered over the CAN bus, mediated by the USB dongle.

**Mechanism:**
- Firmware data is transferred from the host PC to the dongle via USB (`USBCMD_CPU` category, `FLASH_R/W` sub-commands)
- The dongle relays firmware data to the target device using segmented POP transfers to the `ROM` ODI class
- The target device's bootloader receives and programs the flash memory

**Functions:**

| Function | Direction | Purpose |
|----------|-----------|---------|
| `DongleWriteFlashOverCAN` | Host -> Dongle -> Device | Write firmware data to device flash |
| `DongleReadFlashOverCAN` | Device -> Dongle -> Host | Read firmware data from device flash |

**Notes:**
- Flash operations use the segmented protocol with CRC verification mandatory
- The target device must be in bootloader mode (entered via a separate command sequence)
- Flash-over-CAN is used for updating Power Modules, Joystick Modules, and other R-Net devices in the field without removing them from the wheelchair

---

## Access Levels

The R-Net Programmer implements a multi-tier access control system that restricts which parameters and operations are available.

### Hierarchy

```
OEM (highest)
  |
  v
Dealer
  |
  v
Lower levels (user-facing tools)
```

### Implementation

- Access level credentials are stored in the **dongle's EEPROM** (via `USBCMD_E2` commands)
- The RNet Programmer software reads the dongle's access level at connection time
- If a lower-access dongle is connected, the software **demotes** its own access level to match
- Higher-tier access unlocks additional parameters, speed limits, motor current limits, and diagnostic functions

### Controller Lock/Unlock

- R-Net controllers can be **locked** to prevent configuration changes
- The `SendUnlock` command is used to unlock a controller for programming
- Lock state is stored in the controller's EEPROM
- A locked controller will reject POP write operations with an error

### Security Observations

- Access levels are enforced by software and dongle firmware, **not** by the CAN protocol itself
- A device on the CAN bus sending raw POP frames is not subject to access level restrictions
- The dongle's EEPROM can potentially be modified to change access level
- No challenge-response authentication exists between dongle and device

---

## Security Notes

### Blowfish-ECB Device Database

The `.rnd` device database files (used by RNet Programmer software to store device information) are encrypted with **Blowfish in ECB mode**.

**Weakness:** ECB (Electronic Codebook) mode encrypts each block independently, meaning identical plaintext blocks produce identical ciphertext blocks. This reveals patterns in the data structure and enables known-plaintext attacks.

### Protocol-Level Security

| Aspect | Status |
|--------|--------|
| CAN frame authentication | None. Any device on the bus can send POP frames. |
| POP encryption | None. All parameters transmitted in cleartext. |
| Replay protection | None. Captured POP transactions can be replayed. |
| Access level enforcement | Software/dongle only. Not enforced at CAN level. |
| Repository ownership | Advisory only. Not cryptographically enforced. |
| CRC verification | Integrity only (CRC-16). Not a security mechanism. |

### Practical Implications

- An attacker with CAN bus access can read all device configuration using POP
- Configuration can be modified without the official R-Net Programmer hardware
- Firmware can potentially be modified via flash-over-CAN with a custom CAN interface
- The `.rnd` database encryption provides minimal protection due to ECB mode

---

## Appendix: Protocol Relationship to Observed Frames

The POP protocol corresponds to previously documented R-Net Programmer behavior as follows:

| Observed Behavior | POP Mechanism |
|-------------------|---------------|
| `0x78F#42...` heartbeat | `USBCMD_SERVICE` polling relayed as POP quick frame |
| `0x78F#83...` set address | Quick POP download to set ODI address pointer |
| `0x78F#03...` start read | Quick POP upload request |
| `0x793#4F...` read response | Quick POP upload response |
| `0x793#8F...` complete | POP `TC_END` acknowledgment |
| `0x7A0#` presence | CAN conduit frame (not POP, but part of session setup) |
| Extended frames `0x1E4.../0x1E0...` | POP segmented protocol for bulk config transfer |

---

*Reconstructed from reverse engineering of DongleInterface.dll v3.0.0.0 and RNet Programmer5 OEM.exe v5.7.0, (C) PG Drives Technology / Curtiss-Wright*
