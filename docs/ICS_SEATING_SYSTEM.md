# ICS (Intelligent Control System) — Seating System

## Overview

The ICS (Intelligent Control System) controls the Powered Seat Functions and provides Drive Inhibit information to the Driving System. ICS is a **separate system from R-Net** — it uses the **LIN bus internally** for communication between its components, and only interfaces with R-Net via CAN for error reporting and drive inhibit signaling.

**Key distinction:** ICS uses LIN bus, R-Net uses CAN bus. ICS configuration files use `.icscfg` format and are programmed with WheelchairBuilder (WB2/WB4) software, which is separate from the R-Net PC Programmer.

## System Hardware

The ICS consists of the following components (not all used in every configuration):

| Component | Description |
|-----------|-------------|
| **ICS Master Module** | Central controller. Contains firmware, handles all logic. Connected to R-Net CAN bus for drive inhibit communication. |
| **Switchbox** | User interface with 8 buttons and 8 LEDs. Available in Pushbutton or Toggle styles. Connected via LIN bus. |
| **Smart Actuator** | Linear actuator with built-in position feedback and motor driver electronics. Connected via LIN bus. |
| **Standard Actuator** | Linear actuator without smart electronics. Requires General Module for control. |
| **General Module** | Motor driver node for standard actuators. Provides position feedback via external SoftPot sensor. Connected via LIN bus. |
| **SoftPot Position Sensor** | Flexible potentiometer for position feedback on standard actuators. |
| **Connector Block** | Distribution hub for LIN bus wiring. |
| **ICS Bus Cable** | Proprietary cable for LIN bus connections between ICS components. |

## Switchbox Interface

### Button Layout

The switchbox has 8 switches (pushbuttons or toggles) and 8 LEDs. Multiple layouts are available — the layout determines which seat function each button controls.

### LED Indications

Each button has its own LED. The LED provides feedback about the associated seat function:

**Solid Colors (Drive-related information):**
| LED State | Meaning |
|-----------|---------|
| LED Off | Function not available right now |
| Solid Green | All OK — drive at full speed |
| Solid Yellow | Seat OK — drive speed limited |
| Solid Red | Seat OK — drive inhibited |

**Flashing Colors (Actuator-related information):**
| LED State | Meaning |
|-----------|---------|
| Flashing Green | Special mode (Memory/Configuration) |
| Flashing Yellow | Safety limit reached — can only move in safe direction |
| Flashing Red | Error — actuator problem, overcurrent, communication, etc. |

### Switchbox Layouts

13 standard switchbox layouts are available (Layout A through M), each mapping buttons to different combinations of seat functions. Layouts are selected during ICS configuration.

### Icons

Standard icons represent seat functions:
- Seat Elevator (up/down arrows)
- Power Recline (backrest angle)
- Power Anterior Tilt (forward tilt)
- Standing Sequence A and B
- Power Tilt (posterior only)
- Elevating Legrest
- "Swap" (toggle Left/Right functions)
- Memory Mode (floppy disk icon)

## Seat Functions

### Available Functions
- **Seat Elevator** — raise/lower the seat
- **Power Recline** — adjust backrest angle
- **Power Tilt** — adjust seat tilt (anterior and/or posterior)
- **Elevating Legrest** — adjust leg rest angle (left/right independent or combined)
- **Standing Sequence** — automated stand-up/sit-down sequence (VS seats only)
- **Option 1-6** — additional configurable functions (articulation legs, support wheels, etc.)

### Seat Position Memory

The ICS supports storing and recalling up to 3 seat positions:
- **Store:** Enter memory mode (Button 8, hold 2s) → Enable store (Button 4, hold 2s) → Store to position 1/2/3 (Button 5/6/7, hold 2s) → Exit memory mode (Button 8)
- **Recall:** Enter memory mode (Button 8, hold 2s) → Hold recall button (1/2/3) until all actuators stop → Exit memory mode (Button 8)

Only seat functions with precise position feedback (SoftPot, Smart Actuator) can participate in memory positions.

Seat position memory can also be accessed through the R-Net control panel (JSM) via the MODE button → Seating Control Mode → Memory positions M1/M2/M3.

## Standing Function (VS Seat Only)

The VS (VerticalStand) seating system can transition from seated/reclined to fully standing position.

### Standing Sequences

Multiple standing sequences are available, with 4 checkpoints controlling the transition:
- Checkpoint 1-4 define intermediate positions during the stand/sit sequence
- The sequence automatically coordinates multiple actuators (elevator, tilt, recline, legs)

### Standing Drive Restrictions
- **Low speed** when seat is raised 55-250mm or back angle >150°
- **Extra Low speed** when standing and stand+drive is installed
- **Drive Inhibit** when standing and stand+drive is NOT installed, or stand angle >5° from final stand angle when stand+drive is installed

## R-Net Integration

### Drive Inhibit Communication

ICS communicates drive speed restrictions to the PM via R-Net CAN bus:

| Restriction Level | Effect |
|-------------------|--------|
| **No restriction** | Full drive speed available |
| **Low speed** | Drive speed limited (typically ~50%) |
| **Extra Low speed** | Drive speed severely limited |
| **Drive Inhibit** | Driving completely disabled |

The restriction level depends on the current seat position and the user's weight range setting. See `SAFETY_RESTRICTIONS.md` for detailed per-model restriction tables.

### Inhibit Band System

ICS uses inhibit bands to communicate restrictions to the PM:
- **PM has Inhibit 2/3** — physical inhibit inputs on the Power Module
- **ISM has Inhibit 4/5** — additional inhibit channels for ICS seating
- ICS signals are transmitted over CAN bus, not physical wires

### Seating Mode via R-Net JSM

The seat can also be controlled through the R-Net JSM (Joystick Module):
1. Press MODE button until seating system icon appears on LCD
2. Push joystick left/right to select seat function
3. Push joystick forward/backward to operate the function

## Configuration

### Programming Methods

ICS can be configured through three interfaces:

1. **ICS Switchbox** — Basic settings (weight range, LED indication level, layout selection)
2. **R-Net Control Panel** — Via On-Board Programming (OBP) menu
3. **PC Programmer** — Full configuration via WheelchairBuilder (WB2/WB4) software

### User Weight Ranges

8 weight ranges are available, affecting safety restrictions:

| Range | Weight |
|-------|--------|
| 0 | 0-50 kg |
| 1 | 51-65 kg |
| 2 | 66-80 kg |
| 3 | 81-100 kg |
| 4 | 101-120 kg |
| 5 | 121-135 kg |
| 6 | 136-160 kg |
| 7 | 161-205 kg |

### SeatType and ChassisType Codes

Each wheelchair model has specific SeatType and ChassisType codes that determine the restriction tables:

| SeatType | Description |
|----------|-------------|
| 2 | VS (VerticalStand) |
| 3 | Corpus II |
| 4 | PS-Jr |
| 5 | PS |
| 7 | HD (Heavy Duty) |
| 8 | Corpus 3G |
| 9 | APE |
| 10 | Corpus 3G Lowrider |
| 12 | Corpus APE |
| 13 | Corpus VS |

| ChassisType | Description |
|-------------|-------------|
| 1 | C300 |
| 2 | C350 |
| 3 | C400 |
| 4 | C500 |
| 5 | K300 |
| 7 | Street |
| 8 | M300/M400 |
| 13 | F5 |
| 14 | F3 |
| 15 | K450 MX |
| 16 | M3 |
| 17 | M5 |
| 18 | M3 II |
| 19 | M5 II |
| 20 | F3 II |
| 21 | F5 II |

### Configuration Files

ICS uses `.icscfg` configuration files with naming convention:
```
b_XXXXXX [SeatType] [ChassisType] [variant] vN.icscfg
```

These are managed by WheelchairBuilder (WB2/WB4) software, separate from R-Net `.R-net` configuration files.

### ICS Master Module Information

The ICS Master Module has several trackable versions:
- **Firmware version** — Master module firmware
- **Model version** — Configuration model
- **UI version** — User interface revision
- **URIB version** — USB/R-Net interface board

## Emergency Manual Operation ("Take Me Down")

If the ICS system fails, an emergency manual lowering mode is available:

1. Press and hold buttons 6 and 8 simultaneously for 30 seconds
2. The system enters emergency mode at 50% speed with no position feedback
3. Actuators can be manually driven down to a safe position
4. This mode bypasses all safety restrictions

**Warning:** Emergency mode has no safety checks — use only when the normal system is non-functional.

## Error Codes

ICS error codes use prefix **0x20XX** on the R-Net CAN bus. See `RNET_ERROR_CODES.md` for the complete error code table.

Error codes are generated on the LIN bus and reported to R-Net CAN by the ICS Master Module. The Master aggregates errors from all nodes (switchboxes, actuators, general modules).

### Node Types on LIN Bus

| Node | Description |
|------|-------------|
| ICS Master | Central controller, CAN-LIN gateway |
| V-smart Actuator | Smart linear actuator with built-in electronics |
| General Module | Motor driver for standard actuators |
| Switch Box | User input device (up to 5: main + 4 additional) |

---

*Source: Permobil ICS Onboard Configuration Manual (OM_UK_ICS_Onboard_Configuration.pdf), Edition 8, 2015-09*
*Additional sources: ICS Error Codes v7, ICS Parameter Description, ICS Axis and Function types v2*
*Compiled for accessibility research.*
*Authors: Stephen Chavez & Specter*
