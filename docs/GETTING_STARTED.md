# Getting Started with R-Net Hacking

This guide will help you set up your environment for R-Net wheelchair research.

## Safety First

**IMPORTANT:** Power wheelchairs are critical medical devices. Before you begin:

1. **Always have a physical emergency stop** - Unplug the CAN connection or power
2. **Elevate the wheelchair** - Put it on blocks so wheels spin freely
3. **Start with monitoring only** - Don't send frames until you understand the protocol
4. **Have a spotter** - Someone ready to cut power if needed

## Hardware Setup

### Option 1: Raspberry Pi + PiCAN2 (Recommended)

**Cost:** ~$115

**Parts:**
- Raspberry Pi 3/4
- PiCAN2 HAT with SMPS (from SK Pang)
- 4-pin R-Net connector

**Setup:**
```bash
# Edit /boot/config.txt, add:
dtparam=spi=on
dtoverlay=mcp2515-can0-overlay,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay

# Reboot
sudo reboot

# Bring up CAN interface
sudo ip link set can0 up type can bitrate 125000

# Verify
ip link show can0
```

### Option 2: Arduino + CAN Shield

**Cost:** ~$75

**Parts:**
- Arduino UNO
- SparkFun CAN-BUS Shield
- 4-pin R-Net connector

**Setup:**
1. Flash `slcan.ino` from `chair_control/arduino/slcan_sketchbook/`
2. Connect Arduino to PC via USB
3. Create SLCAN interface:
```bash
sudo slcand -o -c -s4 /dev/ttyUSB0 slcan0
sudo ip link set slcan0 up
```

### Wiring

Connect to R-Net bus:
```
CAN Shield/PiCAN2    R-Net Connector
─────────────────    ───────────────
CAN_H           ──── Pin 2 (CAN Hi)
CAN_L           ──── Pin 1 (CAN Lo)
GND             ──── Pin 4 (GND)
```

**DO NOT** connect to Pin 3 (+24V) unless you need power.

## Software Setup

### Install CAN Utilities

```bash
# Debian/Ubuntu/Raspberry Pi
sudo apt-get install can-utils

# Arch Linux
sudo pacman -S can-utils
```

### Install Python Dependencies

```bash
pip install python-can
```

### Clone This Repository

```bash
git clone https://github.com/redragonx/can2RNET.git
cd can2RNET
```

## Your First Session

### Step 1: Monitor the Bus

Power on the wheelchair and monitor traffic:

```bash
candump can0 -L
```

You should see frames scrolling by. Look for:
- `00E#...` - Serial heartbeat (every 50ms)
- `02000100#...` - Joystick position (every 10ms)
- `1C0C0100#...` - Battery level (every 1000ms)

### Step 2: Understand the Traffic

Save a capture for analysis:

```bash
candump can0 -L > capture.log
```

Use Wireshark for detailed analysis:

```bash
# Install Wireshark with CAN support
sudo apt-get install wireshark

# Capture directly
wireshark -i can0
```

### Step 3: Send Test Frames (Safely!)

With wheelchair elevated:

```bash
# Beep the horn
cansend can0 0C040100#
sleep 0.2
cansend can0 0C040101#

# Play a tune
cansend can0 181C0D00#2050205120522053

# Read battery level (trigger update)
# Watch candump output for 1C0C0100#XX
```

### Step 4: Run the Joystick Script

Connect a USB joystick and run:

```bash
cd can2RNET
python3 JoyLocal.py
```

This uses the FollowJSM method to inject joystick commands.

## Understanding the Protocol

### Frame ID Basics

- **3 hex digits** = Standard frame (11-bit ID)
- **8 hex digits** = Extended frame (29-bit ID)

```
Standard:  061#40400000
Extended:  02000100#0064
```

### Key Concepts

1. **Heartbeats** - Devices send periodic "I'm alive" frames
2. **Joystick frames** - Position sent every 10ms
3. **Serial authentication** - XOR-based (weak security)
4. **Parameter exchange** - Configuration via 78X/79X frames

### Read the Documentation

- `docs/RNET_PROTOCOL_GUIDE.md` - Full protocol documentation
- `docs/QUICK_REFERENCE.md` - Cheat sheet
- `RNET_FRAME_DICTIONARY.md` - Complete frame reference
- `CLAUDE.md` - Project overview

## Control Methods

### FollowJSM (Safest)

Sends your frame immediately after the real JSM frame:

```python
# JoyLocal.py does this automatically
```

**Pros:** JSM still works, easy handoff
**Cons:** Timing-sensitive

### JSMerror (More Reliable)

Triggers error on JSM, then takes over:

```python
# JoyLocal_usingJSMexploit.py
```

**Pros:** Reliable control
**Cons:** Disables JSM drive, needs JSM present

## Troubleshooting

### No frames appearing

1. Check wiring (CAN_H and CAN_L not swapped)
2. Verify bitrate is 125000
3. Make sure wheelchair is powered on
4. Check `dmesg` for CAN errors

### "Network is down" error

```bash
sudo ip link set can0 up type can bitrate 125000
```

### Frames appear but control doesn't work

1. Timing may be off - try JSMerror method
2. Check you're using correct device slot (usually 1)
3. Verify joystick frame format: `02000100#XxYy`

### CAN bus errors

```bash
# Check error counters
ip -details link show can0

# Reset interface
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 125000
```

## Next Steps

1. **Analyze startup sequence** - Capture power-on handshake
2. **Extract XOR table** - From serial exchange frames
3. **Map parameters** - Monitor 78X/79X during config changes
4. **Build alternative input** - Xbox controller, sip-and-puff, etc.
5. **Contribute!** - Document new findings

## Resources

- [can-utils documentation](https://github.com/linux-can/can-utils)
- [SocketCAN documentation](https://www.kernel.org/doc/html/latest/networking/can.html)
- [DEFCON24 presentation](chair_control/canPPT.pdf)

## Community

Found something new? Please contribute:
- Document new frame types
- Share captures (anonymized)
- Improve the Python library
- Add support for new input devices

**Remember:** This research helps wheelchair users gain independence through alternative control methods. Always prioritize safety and accessibility.
