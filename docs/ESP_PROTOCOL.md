# ESP (Enhanced Steering Performance) Protocol

## Overview

The ESP module is Permobil's gyroscope-based course deviation correction system for R-Net wheelchairs. ESP stands for Enhanced Steering Performance.

**Key principle:** The ESP module connects to the wheelchair control system and contains a sensor that measures course deviations. A processor corrects any deviations from the course set by the user's steering device. The ESP uses information from the sensor and steering device to calculate a corrected steering signal, which is passed to the R-Net output stage (Power Module) to control the drive motors.

**Critical safety note:** The ESP module requires access to the full capacity of the output stage (PM). The parameters for the output stage (Power Module) are set by Permobil and **MUST NOT be changed**. If any changes are required to performance, acceleration, course stability, etc., the **ESP module must be reprogrammed** — not the PM.

Product code: 205229-UK-0
Manufacturer: Permobil AB, Sweden

## Physical Description

The ESP module is installed in the wheelchair chassis. It has:
- Two R-Net connectors (4-pin, standard R-Net pinout) for daisy-chaining on the CAN bus
- Two status LEDs (one red, one green) on the front face
- No direct programming interface — must be programmed via Permobil PC Programmer for R-Net (product code 1822585) with dongle

## R-Net Integration

The ESP sits between the JSM (input device) and PM (output stage) on the R-Net CAN bus:

```
JSM ──── ESP ──── PM ──── Motors
         │
    Gyro Sensor
```

### How ESP Overrides PM

The ESP module intercepts and modifies the steering signal before it reaches the PM. Because of this:

1. **PM speed parameters are controlled by the ESP** — the same 18 speed/acceleration/deceleration parameters that normally reside in the PM are instead managed in the ESP
2. **Modifying PM speed parameters directly will NOT work** as expected on ESP-equipped chairs
3. The PM output stage parameters must remain at maximum/predefined values so the ESP has full control authority

### Parameters

The ESP module has **20 programmable parameters** per profile, adjusted using the Permobil PC Programmer for R-Net:

| # | Parameter | Profile 1 (Indoor/fine) | Profile 2 (Normal) | Range |
|---|-----------|------------------------|--------------------| ------|
| 1 | Maximum Forward Speed | 45% | 100% | 0-100% |
| 2 | Minimum Forward Speed | 15% | 25% | 0-100% |
| 3 | Maximum Reverse Speed | 30% | 55% | 0-100% |
| 4 | Minimum Reverse Speed | 15% | 15% | 0-100% |
| 5 | Maximum Turning Speed | 60% | 80% | 0-100% |
| 6 | Minimum Turning Speed | 40% | 55% | 0-100% |
| 7 | Maximum Forward Acceleration | 20% | 22% | 0-100% |
| 8 | Minimum Forward Acceleration | 15% | 20% | 0-100% |
| 9 | Maximum Forward Deceleration | 20% | 30% | 0-100% |
| 10 | Minimum Forward Deceleration | 10% | 20% | 0-100% |
| 11 | Maximum Reverse Acceleration | 10% | 15% | 0-100% |
| 12 | Minimum Reverse Acceleration | 10% | 15% | 0-100% |
| 13 | Maximum Reverse Deceleration | 20% | 22% | 0-100% |
| 14 | Minimum Reverse Deceleration | 10% | 20% | 0-100% |
| 15 | Maximum Turn Acceleration | 30% | 45% | 0-100% |
| 16 | Minimum Turn Acceleration | 30% | 30% | 0-100% |
| 17 | Maximum Turn Deceleration | 40% | 50% | 0-100% |
| 18 | Minimum Turn Deceleration | 25% | 35% | 0-100% |
| 19 | Fast Brake Rate | 60% | 60% | 0-100% |
| 20 | Switched Input | No | No | Yes/No |

**Parameters 1-18** are the same speed, acceleration, and deceleration parameters found in the PM on non-ESP chairs.

**Parameter 19 (Fast Brake Rate)** controls emergency braking response.

**Parameter 20 (Switched Input)** selects the drive device for each profile:
- **No** = Analog joystick or attendant control
- **Yes** = Button control (digital input)

### Profile Configuration

Up to 8 profiles can be configured (Profile 1 through Profile 8, plus Attendant). Each profile contains:
- Configuration: Mode assignment (Mode 1-7)
- Speeds: The 20 parameters listed above
- Controls: Latched drive settings

The ESP personality must be set to "Permobil ESP [English]" in the PC Programmer. If ICS seating is also installed, use "Permobil ICS [English]" personality instead.

## Error Codes

The ESP module uses error code prefix **0x12XX** on the R-Net CAN bus (see `RNET_ERROR_CODES.md` for full list).

### LED Error Indications

The ESP has two LEDs (red on left, green on right):

| Status | Red LED | Green LED |
|--------|---------|-----------|
| Before start | Off | Off |
| Module is not active | On | Off |
| Normal mode (functioning) | Off | On |
| Calibration mode | On | On |
| Error indication | Flashes | Off |

### Flash Code Error Table

When the red LED flashes, the number of flashes indicates the error:

| Flashes | Description | LCD Text | Check/Replace |
|---------|-------------|----------|---------------|
| 1 | Power Module in Latched Drive Mode | Bad Settings | Programming |
| 2 | Incorrect reference voltage, VCC/2 | Module Error | ESP module |
| 3 | PWM Offset adjustment outside working range | Module Error | ESP module |
| 4 | Gyro sensor value outside specified limits | Module Error | ESP module |
| 5 | Module Test Flag not set in EEPROM | Module Error | ESP module |
| 6 | Incorrect calibration value in EEPROM | Recalibrate | ESP module |
| 7 | Cannot read program object in time, time limit reached | Cycle Power | Switch off/on, check cabling and R-Net units |
| 8 | AD/DA Controller not synchronized | Cycle Power | Switch off/on, check cabling and R-Net units |
| 9 | Non-existent instruction | Module Error | ESP module |
| 10 | Program/system error | Module Error | Switch off/on, check cabling and R-Net units |

## Safety Rules

From the official Permobil ESP User Manual:

1. **No changes to output stage parameters** — PM parameters must not be modified
2. **Only qualified technicians** should program the ESP module
3. **Document all changes** — record parameter values before and after changes
4. **Decrease, don't increase** — raising parameter values can make the wheelchair unstable and difficult to maneuver
5. **Test-drive required** — wheelchair must be test-driven before returning to user after any changes
6. **Disconnecting ESP for testing** — when ESP is disconnected, steering characteristics are set to very high values, making the wheelchair very difficult to maneuver. Ensure plenty of space.

## Implications for R-Net Hacking

### What This Means for Alternative Control

1. **Check for ESP first** — Before modifying PM speed parameters via CAN, verify whether an ESP module is present on the bus. If ESP is installed, speed parameter changes must go to the ESP, not the PM.

2. **ESP detection** — The ESP module announces itself on the R-Net bus during startup. Its error codes use prefix 0x12XX. Look for ESP-related frames in the startup handshake.

3. **ESP as control point** — The ESP is effectively the "speed controller" on equipped chairs. Any alternative control system needs to either:
   - Work through the ESP (preferred)
   - Replace the ESP's function entirely (requires full understanding of gyro correction)

4. **FollowJSM/JSMerror still work** — The joystick spoofing methods (FollowJSM, JSMerror) operate at the joystick frame level (0x02000X00), which is upstream of the ESP. The ESP processes whatever joystick input it receives, so these exploits remain effective.

---

*Source: Permobil ESP R-Net User Manual (OM_UK_ESP_R-Net.pdf), Edition 1, 2008-04*
*Compiled for accessibility research.*
*Authors: Stephen Chavez & Specter*
