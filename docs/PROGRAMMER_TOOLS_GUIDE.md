# R-Net Programmer Tools Guide

A guide to using the open-source R-Net wheelchair programming tools. These tools let you read, backup, and modify your chair's configuration via the POP (Parameter Object Protocol) over CAN bus.

## Which Tool Should I Use?

| Tool | For | Protocol | Difficulty |
|------|-----|----------|------------|
| **`rnet_obp_mode.py`** | OBP mode: enable, monitor, read/write named parameters | Parameter exchange (0x781/0x790) | Easy - guided workflow |
| **`rnet_self_program.py`** | Adjusting your chair settings (speed, motor current) | POP (0x78F/0x793) | Easy - interactive menus |
| **`rnet_programmer.py`** | Low-level memory read/write, monitoring, dumping | POP (0x78F/0x793) | Intermediate - CLI |
| **`rnet_pop_shell.py`** | Interactive hex-level POP programming shell | POP (0x78F/0x793) | Advanced - raw hex |

**Two different protocols:**
- **OBP** (`rnet_obp_mode.py`): Uses the chair's built-in programming mode (Mode 8). Activated by Horn+On/Off button combo. Parameters addressed by register name. Dealer-level access.
- **POP** (all other tools): Emulates the R-Net Programmer dongle. Raw EEPROM memory addressing. OEM-level access.

See `docs/OBP_ENABLE_GUIDE.md` for enabling OBP mode.

```
rnet_obp_mode.py          (OBP: button combo, parameter exchange 0x781/0x790)

rnet_self_program.py      (POP: menus, named parameters, safety prompts)
        |
        v  imports
rnet_programmer.py        (POP: protocol, CAN heartbeat, read/write)
  rnet_pop_shell.py       (POP: interactive hex shell)
        |
        v  uses
SocketCAN (can0)          (Linux CAN bus driver)
        |
        v  connects to
R-Net CAN Bus @ 125kbps   (wheelchair)
```

---

## Prerequisites

### Hardware

**Option 1: Raspberry Pi + PiCAN2** (~$115, recommended)
- Raspberry Pi 3 or 4
- PiCAN2 HAT with SMPS (from skpang)
- R-Net 4-pin cable

**Option 2: Any Linux PC + USB CAN adapter**
- USB-to-CAN adapter (CANable, PEAK PCAN-USB, etc.)
- Must support SocketCAN

### R-Net Connector Pinout (Female / Device Side)

```
  +---------+
  | 1  |  2 |    1: CAN Lo
  |----+----|    2: CAN Hi
  | 3  |  4 |    3: +24VDC (do NOT connect unless needed)
  +---------+    4: GND
```

Wire your CAN adapter:
- CAN_H to Pin 2
- CAN_L to Pin 1
- GND to Pin 4

### Software

Python 3.7+ (pre-installed on Raspberry Pi OS).

No pip packages required for `rnet_self_program.py` and `rnet_programmer.py`.

For `rnet_obd_program.py`: `pip install python-can`

### CAN Interface Setup

**Raspberry Pi + PiCAN2:**

Add to `/boot/config.txt`:
```
dtparam=spi=on
dtoverlay=mcp2515-can0-overlay,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

Reboot, then bring up the interface:
```bash
sudo ip link set can0 up type can bitrate 125000
```

**USB CAN adapter:**
```bash
sudo ip link set can0 up type can bitrate 125000
```

**Verify the connection** (wheelchair must be powered on):
```bash
candump can0 -L
```

You should see frames like `00E#...`, `02000100#...`, `1C0C0100#...` scrolling by. If nothing appears, check your wiring and that the chair is on.

---

## Safety

**Power wheelchairs are critical medical devices.** Follow these rules:

1. **Elevate the wheelchair** - wheels must be off the ground during all testing
2. **Have a spotter** present who can cut power
3. **Always backup** before changing anything
4. **Start small** - change one parameter at a time, test between changes
5. **Know your defaults** - stock motor current is 55%, keep a record of what you change
6. **Emergency recovery** - if the chair behaves wrong, restore your backup

### Safety Levels

| Level | Meaning | Examples |
|-------|---------|----------|
| **SAFE** | No risk of damage | Viewing settings, reading memory |
| **CAUTION** | Affects driving behavior | Speed, acceleration, turn rate |
| **DANGER** | Can cause damage or injury | Motor current limits, safety fences |

---

## rnet_self_program.py - Self-Programmer

The main tool for wheelchair users. Interactive menus with named parameters, safety warnings, and automatic backup.

### Quick Start

```bash
# Power on wheelchair, elevate wheels off ground
# Connect CAN adapter

# Start the self-programmer
python3 rnet_self_program.py
```

You'll see:
```
========================================================
  R-Net Self-Programmer v1.0
  For wheelchair users - adjust YOUR chair settings
========================================================

  Connecting to CAN bus (can0)...
  CAN bus connected.
  Enabling programmer mode...
  Programmer mode active. Heartbeat running.

  MAIN MENU
  ------------------------------
  1. View Current Settings
  2. Edit Motor Current Limits
  3. View Speed Profiles
  4. Backup Configuration
  5. Restore Configuration
  6. Raw Memory Read
  7. Exit
```

### View Current Settings

Shows all readable parameters at a glance:

```
  MOTOR CURRENT LIMITS
  ----------------------------------------
  Profile         Current      Stock
  ----------------------------------------
  Profile 1           55%       55%  |###########|
  Profile 2           55%       55%  |###########|
  Profile 3           80%       55%  |################| <-- modified
  ...

  SPEED PROFILES (5 found)
  --------------------------------------------------
  Name                   Fwd   Rev   Acc   Dec  Turn
  --------------------------------------------------
  SLOWEST                 20    15    10    12    15
  MEDIUM                  50    40    25    20    35
  FAST                    80    60    30    25    55
  ...
```

### Edit Motor Current Limits

The most common modification. Stock R-Net chairs ship with motor current limited to 55%. Increasing this gives more power for hills, grass, and rough terrain.

```
  MOTOR CURRENT LIMITS
  ----------------------------------------
   1. Profile 1: 55%
   2. Profile 2: 55%
   ...
  13. Set ALL profiles to same value
   0. Back

  Select profile to edit [0-13]: 1

  Current Motor Current Limit (Profile 1): 55%
  Range: 0-100%
  Stock default: 55%

  !! WARNING: This parameter affects safety-critical systems.
  !! Incorrect values can cause motor damage, loss of control, or tipping.
  !! Ensure the chair is on a test stand with wheels off the ground.

  New value (or Enter to cancel): 80

  ==================================================
  PARAMETER CHANGE
  ==================================================
  Parameter:  Motor Current Limit (Profile 1)
  Current:    55 %
  New:        80 %
  Default:    55 %

  !! WARNING: This parameter affects safety-critical systems.

  Apply this change? [y/N]: y

  A backup is required before making any changes.
  Backing up configuration to rnet_backup_20260327_143022.bin...
  Backup saved: rnet_backup_20260327_143022.bin (4096 bytes)
  Writing...
  Success: Profile 1 motor current = 80%
```

The tool:
1. Shows the current value and stock default
2. Warns you about safety implications
3. Creates a backup automatically (first time only)
4. Writes the new value
5. Reads it back to verify it was saved

### Set All Profiles at Once

Choose option 13 from the motor limits menu:

```
  Set ALL profiles to what value? (0-100%, or Enter to cancel): 100

  ==================================================
  SET ALL MOTOR CURRENT LIMITS TO 100%
  ==================================================
  Profile 1:   (55% -> 100%)
  Profile 2:   (55% -> 100%)
  ...

  Apply to ALL profiles? [y/N]: y
  Done: 12 profiles updated, 0 errors
```

### View Speed Profiles

Discovers and displays speed profiles stored in the chair's EEPROM:

```
  SPEED PROFILES (5 found)
  ============================================================

  [1] Normal
      Offset:       0x0268
      Max Forward:  100
      Max Reverse:  50
      Acceleration: 20
      Deceleration: 15
      Turn Speed:   60
      Raw config:   6432140f3c0000

  [2] DANGEROUS
      Offset:       0x029C
      ...
```

Speed profiles are discovered by scanning for the `dddd` prefix pattern in EEPROM region 0x0250-0x0600.

### Backup and Restore

**Create a backup** (always do this before making changes):
```bash
# Interactive
python3 rnet_self_program.py
# Choose option 4, enter filename

# Or via CLI
python3 rnet_self_program.py backup -o my_chair_backup.bin
```

**Restore from backup** (if something goes wrong):
```bash
python3 rnet_self_program.py restore my_chair_backup.bin

# You must type 'RESTORE' to confirm:
# This will OVERWRITE the current device configuration.
# Are you sure? Type 'RESTORE' to confirm: RESTORE
```

The backup file is 4096 bytes (0x0000-0x1000) containing the full EEPROM configuration region.

### CLI Commands

For scripting or quick operations without the interactive menu:

```bash
# View settings
python3 rnet_self_program.py view
python3 rnet_self_program.py view --json > config.json

# List available parameters
python3 rnet_self_program.py params

# Set a specific parameter
python3 rnet_self_program.py set motor_current_limit_p1 80
python3 rnet_self_program.py set motor_current_limit_p1 80 --force  # skip confirmation

# Backup/restore
python3 rnet_self_program.py backup -o save.bin
python3 rnet_self_program.py restore save.bin

# Use a different CAN interface
python3 rnet_self_program.py -i can1 view
```

---

## rnet_programmer.py - Low-Level Programmer

For developers and researchers who need direct memory access. Provides raw read/write to any EEPROM address.

### Commands

**Test the connection:**
```bash
python3 rnet_programmer.py handshake -v
```

**Read memory:**
```bash
# Read 256 bytes from address 0x0000
python3 rnet_programmer.py read 0x0000 0x100

# Save to file
python3 rnet_programmer.py read 0x0000 0x100 -o header.bin
```

**Write memory:**
```bash
# Write hex data to an address
python3 rnet_programmer.py write 0x0100 --data DEADBEEF

# Write from file
python3 rnet_programmer.py write 0x0100 --input data.bin
```

**Dump full configuration:**
```bash
python3 rnet_programmer.py dump 0x0000 0x1000 -o config.bin
python3 rnet_programmer.py dump 0x0000 0x2000 -o full_dump.bin
```

**Monitor CAN traffic:**
```bash
# Monitor all traffic for 30 seconds
python3 rnet_programmer.py monitor --duration 30

# Monitor only programmer frames
python3 rnet_programmer.py monitor --filter 78F,793,7A0

# Monitor with programmer handshake active
python3 rnet_programmer.py monitor --programmer
```

### EEPROM Memory Map

| Address Range | Content |
|---------------|---------|
| 0x0000-0x00FF | Device header / identification |
| 0x0100-0x015F | Serial number / keys |
| 0x0160-0x016F | Encryption key (if present) |
| 0x0250-0x0600 | Speed profiles (`dddd` + name + config) |
| 0x0400-0x0FFF | Device configuration tables |
| 0x0B00-0x0BC0 | Motor current limits (per-profile) |

---

## rnet_obd_program.py - Interactive Shell

An interactive hex-level programming shell using the python-can library.

```bash
pip install python-can  # required
python3 rnet_obd_program.py
```

### Interactive Commands

```
R-Net OBD Programmer> read 0x0B23 1
0B23: 37                                                  7

R-Net OBD Programmer> write 0x0B23 50

R-Net OBD Programmer> dump config_backup.bin
Dumping 0x0000-0x1000...
[100.0%] Complete
Saved to config_backup.bin

R-Net OBD Programmer> status
Connected: yes
Heartbeat: running
Bytes read: 4096
Bytes written: 1
Errors: 0

R-Net OBD Programmer> quit
```

---

## POP Protocol Reference

The tools communicate using the POP (Parameter Object Protocol), officially named in DongleInterface.dll from PG Drives Technology.

### How It Works

1. **Announce** - Send empty frame on `0x7A0` to announce programmer presence
2. **Heartbeat** - Exchange `0x78F#42...` / `0x793#2F...` every 200ms to maintain session
3. **Read** - Set address (`0x83`), start read (`0x03`), receive data (`0x4F`), complete (`0x8F`)
4. **Write** - Set address (`0x83`), send data (`0x43`), receive ACK (`0x0F`), complete (`0x8F`)

### Timing

| Constant | Value | Purpose |
|----------|-------|---------|
| Heartbeat interval | 200ms | Keep session alive |
| Session timeout | ~2s | Connection drops without heartbeat |
| Quick transaction timeout | 1000ms | Single read/write timeout |
| Read retry count | 3 | Max retries on failure |
| Response timeout | 500ms | Wait for device response |

### Frame Format

```
Read example:
  TX: 78F#83 00 01 FF 23 0B 00 00   Set address to 0x0B23
  TX: 78F#03 00 01 FF 17 00 00 00   Start read
  RX: 793#4F 00 01 FF 37 00 00 00   Data: 0x37 (55%)
  RX: 793#8F 00 01 FF 00 00 00 00   Complete

Write example:
  TX: 78F#83 00 01 FF 23 0B 00 00   Set address to 0x0B23
  TX: 78F#43 00 01 FF 64 00 00 00   Write 0x64 (100%)
  RX: 793#0F 00 01 FF 41 00 00 00   Write ACK
  RX: 793#8F 00 01 FF 00 00 00 00   Complete
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Failed to connect to CAN bus" | Interface not up | `sudo ip link set can0 up type can bitrate 125000` |
| "Failed to enable programmer mode" | Chair not powered on | Turn on the wheelchair |
| No frames in `candump` | Wiring wrong | Check CAN_H/CAN_L/GND connections |
| "Write verification failed" | EEPROM didn't save | Retry; check battery level |
| "Repository held by another programmer" | Another tool is connected | Close other programmer tools |
| Tool hangs on connect | Wrong bitrate | Must be 125000 (125kbps) |
| Permission denied on socket | Need root for raw CAN | `sudo python3 rnet_self_program.py` or add user to `can` group |

### Virtual CAN for Testing (No Hardware)

You can test the tools without a wheelchair using Linux virtual CAN:

```bash
# Create virtual CAN interface
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Run the tool on vcan0
python3 rnet_self_program.py -i vcan0

# In another terminal, simulate responses:
# Heartbeat ACK
cansend vcan0 793#2F2000FF00000000

# Read response (value=55 at any address)
cansend vcan0 793#4F0001FF37000000
cansend vcan0 793#8F0001FF00000000
```

---

## Common Modifications

### Increase Motor Current (Most Popular)

Stock R-Net chairs limit motor current to 55%. This is conservative. Many users increase it for better hill climbing and off-road performance.

| Setting | Motor Current | Use Case |
|---------|--------------|----------|
| Stock | 55% | Factory default, gentle driving |
| Moderate | 70-80% | Better hills, some rough terrain |
| High | 90% | Aggressive driving, outdoor use |
| Maximum | 100% | Racing, extreme terrain (monitor motor temp) |

```bash
# Set all profiles to 80%
python3 rnet_self_program.py set motor_current_limit_p1 80
# ... repeat for each profile, or use interactive menu option 13
```

**Risks at high current:**
- Motors run hotter - monitor for overheating on long drives
- Motor brushes wear faster
- Gearbox stress increases
- Battery drains faster

### Backup Before Any Modification

**Always** create a backup before your first change:

```bash
python3 rnet_self_program.py backup -o factory_settings.bin
```

Keep this file safe. If anything goes wrong, you can restore:

```bash
python3 rnet_self_program.py restore factory_settings.bin
```

---

## Further Reading

| Document | Description |
|----------|-------------|
| [POP Protocol](POP_PROTOCOL.md) | Full POP specification from DLL reverse engineering |
| [Device Catalog](RNET_DEVICE_CATALOG.md) | All R-Net device types and 100+ parameters |
| [Programmer Protocol](RNET_PROGRAMMER_PROTOCOL.md) | Programmer handshake and read/write details |
| [Protocol Specification](RNET_PROTOCOL_SPECIFICATION.md) | Full R-Net protocol spec |
| [Frame Dictionary](../RNET_FRAME_DICTIONARY.md) | 590+ CAN frame reference |
| [Config File Format](RNET_CONFIG_FILE_FORMAT.md) | .R-net binary file format |

---

*For wheelchair accessibility research. Always prioritize safety.*
*"Hacking wheelchairs for accessibility, not mayhem."*
