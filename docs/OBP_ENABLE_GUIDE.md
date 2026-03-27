# OBP (On-Board Programming) Enable Guide

How to enable and use OBP mode on R-Net wheelchairs.

## What is OBP?

OBP (On-Board Programming) is the R-Net wheelchair's built-in configuration mode. It lets you adjust speed, acceleration, deceleration, and other drive parameters using the JSM (Joystick Module) display and buttons.

**Important:** OBP was originally designed to require a physical R-Net dongle (programming key) connected to the bus. The Horn+On/Off button combo is an alternative entry method gated by the "OBP Keycode Entry" parameter — an OEM-level setting that may be disabled by the manufacturer. See "Enabling OBP" below if the button combo doesn't work.

**Related systems (don't confuse these):**
- **OBP** = On Board Programming — R-Net drive parameters (CAN bus)
- **OBC** = On Board Configuring — ICS seating parameters (LIN bus, separate system)
- **PCP** = PC-Programmer — the official R-Net Programmer desktop software

**OBP is NOT the same as the R-Net Programmer dongle.** They use different protocols:

| | OBP Mode | Programmer Dongle |
|---|---|---|
| **Activated by** | Button combo on the chair | Physical dongle + PC software |
| **CAN protocol** | Parameter exchange (0x781/0x790) | POP protocol (0x78F/0x793) |
| **Addressing** | Named parameters by register | Raw EEPROM memory addresses |
| **Access level** | Dealer-equivalent | Dealer or OEM (dongle-dependent) |
| **Tool** | `rnet_obp_mode.py` | `rnet_programmer.py` / `rnet_pop_shell.py` |

---

## How to Enter OBP Mode

### Method 1: Hardware Dongle (original method, always works)

1. Power off the chair
2. Connect an R-Net programming dongle (D50609 dealer / D50610 OEM) to any R-Net bus connector
3. Power on — the dongle is detected and the network reconfigures
4. Press the **Mode button** to cycle through modes until you reach Mode 8 (OBP)

### Method 2: Button Combo (requires "OBP Keycode Entry" = Yes)

1. **Hold the Horn button**, then **also hold the On/Off button**
2. Wait for a **short bleep** (after the normal power-up sound)
3. **Release the Horn button**, but **keep holding On/Off**
4. Wait through **two more short bleeps**
5. **Release On/Off** — a **longer bleep** confirms OBP is active

If nothing happens, OBP Keycode Entry is probably disabled. See "Enabling OBP" below.

### Verifying OBP is Available

Press the **Mode button twice** on the JSM. If OBP is configured, the display should show "Speeds" (or "Speeds with ESP" if ESP personality is loaded).

### Navigating OBP

| Input | Action |
|---|---|
| Joystick forward | Select parameter above |
| Joystick backward | Select parameter below |
| Joystick left (1st) | Show full parameter name |
| Joystick left (2nd) | Go back to previous screen |
| Speed Up / Down buttons | Adjust parameter value |

**Timeout:** If you don't touch anything for 5 minutes, OBP exits automatically.

**Driving is disabled** while in OBP — the joystick is used for menu navigation.

---

## Enabling OBP When It's Disabled

If the button combo doesn't work, the "OBP Keycode Entry" parameter is set to "No" in the PM's EEPROM. This is an OEM-level setting that wheelchair manufacturers sometimes disable.

### Safe Mode (Recommended)

```bash
python3 rnet_obp_mode.py --enable
```

This runs a guided workflow:

1. **Mode change attempt** (non-destructive) — sends CAN frames to switch to Mode 8 (OBP). No EEPROM writes. If your chair supports direct mode switching, this is all you need.

2. **If mode change fails** — enters POP programmer mode (emulates the dongle):
   - **Creates a full backup** of your config (0x0000-0x1000) to a timestamped file
   - **Dumps the system config region** (0x0400-0x0600) for inspection
   - **Guides you** through finding the OBP Keycode Entry byte
   - Shows how to compare configs, try known offsets, and restore if needed

### With a Known Address

If you already know the EEPROM address for your firmware version:

```bash
# Safe mode — backs up first, writes, verifies
python3 rnet_obp_mode.py --enable-obp-addr 0x0450

# Advanced mode — no backup, no prompts
python3 rnet_obp_mode.py --enable-obp-addr 0x0450 --advanced
```

### Interactive Mode

```bash
python3 rnet_obp_mode.py
```

Then at the `obp>` prompt:

```
obp> enable              # Run the safe enable workflow
obp> enable-at 0x0450    # Write a known address (with backup)
obp> read-pop 0x0400 0x100  # Dump system config via POP
obp> write-pop 0x0450 01    # Write directly via POP
```

---

## Finding the OBP Keycode Entry Address

The exact EEPROM address varies by PM firmware version. Here's how to find it:

### Option A: Compare Two Chairs

If you have access to a chair with OBP enabled and one without:

```bash
# On the working chair (OBP enabled):
python3 rnet_programmer.py dump 0x0400 0x0600 -o working.bin

# On the locked chair (OBP disabled):
python3 rnet_programmer.py dump 0x0400 0x0600 -o locked.bin

# Compare:
xxd working.bin > a.hex
xxd locked.bin > b.hex
diff a.hex b.hex
```

The differing byte (likely 0x00 vs 0x01) is your OBP Keycode Entry address.

### Option B: Compare .R-net Config Files

If you have config exports from the ICS Programmer:

```bash
python3 rnet_config_parser.py working.R-net locked.R-net --diff
```

### Option C: Try Common Offsets

Some PM firmware versions use these addresses (try one at a time, power cycle between):

```
obp> write-pop 0x0420 01
obp> write-pop 0x0440 01
obp> write-pop 0x0450 01
obp> write-pop 0x0460 01
```

After each write, power cycle the chair and try the OBP button combo.

### Option D: Scan With Verbose Mode

```bash
python3 rnet_obp_mode.py --enable -v
```

Verbose mode shows every EEPROM read. Look for bytes that are 0x00 in a region of mostly non-zero values — boolean flags in the config.

---

## Restoring a Backup

If something goes wrong, restore your backup:

```bash
# The backup file is named obp_backup_YYYYMMDD_HHMMSS.bin
python3 rnet_programmer.py write 0x0000 --input obp_backup_20260327_150000.bin
```

Then power cycle the chair.

---

## Safety Notes

- **Always have a backup** before writing to EEPROM. Safe mode creates one automatically.
- **Power cycle after EEPROM writes.** Changes may not take effect until the PM reboots.
- **One change at a time.** If trying common offsets, only change one byte, test, then revert if it didn't work.
- **The mode change approach (Step 1) is always safe.** It sends CAN frames but doesn't modify EEPROM.
- **OBP parameters are dealer-level.** You can adjust speed, acceleration, and deceleration, but not motor voltage or engineering parameters (those require OEM access via the dongle).

---

## OBP Parameter Reference

Parameters accessible in OBP mode (pointer, sub-pointer):

### Speeds
| Pointer | Sub | Parameter |
|---------|-----|-----------|
| 0x06 | 0x01 | Forward Speed |
| 0x06 | 0x02 | Forward Speed Minimum |
| 0x07 | 0x01 | Reverse Speed |
| 0x07 | 0x02 | Reverse Speed Minimum |
| 0x08 | 0x01 | Turn Speed |
| 0x08 | 0x02 | Turn Speed Minimum |

### Acceleration/Deceleration
| Pointer | Sub | Parameter |
|---------|-----|-----------|
| 0x09 | 0x01 | Forward Acceleration |
| 0x09 | 0x02 | Forward Acceleration Minimum |
| 0x0A | 0x01 | Forward Deceleration |
| 0x0A | 0x02 | Forward Deceleration Minimum |
| 0x0B | 0x01 | Reverse Acceleration |
| 0x0B | 0x02 | Reverse Acceleration Minimum |
| 0x0C | 0x01 | Reverse Deceleration |
| 0x0C | 0x02 | Reverse Deceleration Minimum |
| 0x0D | 0x01 | Turn Acceleration |
| 0x0D | 0x02 | Turn Acceleration Minimum |
| 0x0E | 0x01 | Turn Deceleration |
| 0x0E | 0x02 | Turn Deceleration Minimum |

### Drive
| Pointer | Sub | Parameter |
|---------|-----|-----------|
| 0x10 | 0x01 | Power |
| 0x11 | 0x01 | Torque |
| 0x12 | 0x01 | Tremor Damping |

### Controls
| Pointer | Sub | Parameter |
|---------|-----|-----------|
| 0x14 | 0x01 | Short Throw |
| 0x15 | 0x01 | Deadband |

### System
| Pointer | Sub | Parameter |
|---------|-----|-----------|
| 0x20 | 0x01 | Sleep Timer |

### Reading/Writing Parameters

```bash
# Read Forward Speed
python3 rnet_obp_mode.py --read 0x06 0x01

# Set Forward Speed to 80
python3 rnet_obp_mode.py --write 0x06 0x01 80

# Scan all known parameters
python3 rnet_obp_mode.py --scan
```

---

## Technical Details

### Protocol: JSM Parameter Exchange

OBP uses the standard R-Net parameter exchange, not POP:

```
Frame IDs:
  0x780 + slot = Request (JSM slot 1 = 0x781)
  0x790 + slot = Response (PM slot 0 = 0x790)

Frame data (8 bytes):
  Byte 0: Command (0x20=open, 0x40=request, 0x41=ack, 0x21=data, 0xC1=error)
  Byte 1: Register (0x81=pointer, 0x8F=data, 0x8C=text)
  Bytes 2-3: 0x0000
  Bytes 4-7: Parameter ID or value (little-endian)
```

### Example Exchange: Read Forward Speed

```
TX 781: 20 81 0000 06000100   ; OPEN pointer 0x06, sub 0x01
RX 790: 41 81 0000 00000000   ; ACK — pointer exists
TX 781: 40 8F 0000 00000000   ; REQUEST data
RX 790: 21 8F 0000 50000000   ; DATA = 80 (0x50)
```

### Mode 8

OBP reserves Mode 8 in the R-Net mode system. The chair has up to 8 modes (0-7 for user modes, 8 for OBP). The mode change frame sequence:

```
TX 061: 40 40 0000   ; Request mode change (from mode 0)
TX 061: 00 48 0000   ; Switch to mode 8 (OBP)
```

### OBP Keycode Entry

This is a boolean parameter (0x00=No, 0x01=Yes) stored in the PM's EEPROM system configuration region (typically 0x0400-0x0600). When set to No, the button combo is ignored. It can be re-enabled via the POP programmer protocol or an OEM dongle.

---

## Controller Personality (OBP Menu Configuration)

The OBP menu — what parameters appear and how they're presented on the JSM display — is defined by a **Controller Personality** file. This is a separate binary blob stored in the PM, distinct from the OBP Keycode Entry parameter.

**Key facts:**
- In the R-Net PC Programmer: `Controller → Set Controller Personality`
- Two known personalities: **"Permobil ESP"** and **"PGDT Generic"** (with language variants)
- If the chair has an **ESP module**, select the ESP personality — this makes ESP speed parameters appear in OBP instead of normal PM speed parameters
- Personality is flashed via the **segmented POP protocol** (bulk transfer, not single-frame)
- After changing personality, power cycle is required ("Rnet configuration has changed. Please turn control system off and on again.")
- Source: "Reprogramming OBP menu v2.pdf" (Permobil internal doc, 2010)

**If OBP shows wrong parameters** (e.g., normal speed params on an ESP chair), the wrong personality may be loaded. This requires a dongle + PC Programmer to fix — the personality is too large for the POP Quick protocol and requires segmented transfers.

## OBP Keycode Entry: Finding the Address

The exact EEPROM address for "OBP Keycode Entry" varies by PM firmware version. None of the Permobil internal documents we've analyzed contain the specific address. It's stored in the PM's system configuration region (typically 0x0400-0x0600).

**Best approaches to find it:**

1. **Capture a POP session** where the R-Net PC Programmer toggles the OBP Keycode Entry parameter. The EEPROM address will appear in the CAN traffic on 0x78F/0x793.

2. **Diff two config dumps** — one from a chair with OBP enabled and one with it disabled:
   ```bash
   # On each chair:
   python3 rnet_programmer.py dump 0x0400 0x0600 -o config.bin
   # Then diff:
   xxd enabled.bin > a.hex && xxd disabled.bin > b.hex && diff a.hex b.hex
   ```

3. **Community knowledge** — if you find the address for your firmware version, please share it so we can add it to the tool's known offsets.

**Known PM firmware versions** (from R-Net revision log):
- PM80 (D50945): FW 1.86, 1.103
- PM90-EL (D51109): FW 1.104
- PM120 (D50946): FW 1.86, 1.103

---

## Sources

- R-Net OBP Manual SK78571/4 (PG Drives Technology / Curtiss-Wright)
- R-Net Technical Manual SK77981/12
- DongleInterface.dll v3.0.0.0 (reverse engineering)
- DEFCON24 wheelchair hacking research (Stephen Chavez & Specter)
- Permobil R-Net OBP Guide (Tolt Technologies)
