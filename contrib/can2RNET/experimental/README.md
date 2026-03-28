# Experimental Scripts

These are the original experimental scripts from the DEFCON24 wheelchair hacking research (August 2016) by Stephen Chavez and Specter.

They represent the first working prototypes of JSM emulation — spoofing a joystick module on the R-Net CAN bus without a physical joystick connected. These scripts were used to discover and validate the JSM/PM startup handshake protocol.

## Scripts

### jsm_startup_emu.py

The original working EmulateJSM prototype. Performs the full JSM wakeup handshake:

1. Tests CAN connection (`00C#`)
2. Announces serial number heartbeat (`00E#`)
3. Responds to PM serial challenge (XOR-based key exchange)
4. Starts periodic heartbeats (50ms serial, 100ms device)
5. Completes POP parameter exchange (`781`/`790`)
6. Enters drive mode and sends joystick position frames every 10ms

Hardcoded for serial `08901c8a` with the standalone JSM XOR table.

### jsm_startup_emuEXPERIMENTS.py

Experimental variant used for POP parameter enumeration. Same handshake as above but instead of entering drive mode, it iterates through parameter registers to discover what configuration data the PM exposes. This script was used to map out the parameter exchange protocol.

## Dependencies

These scripts use `candump_to_socketcan_defs.py`, the predecessor to `can2RNET.py`. They will not run without that file in the same directory or Python path.

## Modern Version

For a cleaned-up version that uses the current `can2RNET.py` library and supports configurable serial numbers and XOR tables, see [`tools/emulate_jsm.py`](../../../tools/emulate_jsm.py).
