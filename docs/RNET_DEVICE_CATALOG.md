# R-Net Device Type Catalog and Parameter Reference

Comprehensive reference for R-Net device types, configuration parameters, and system features, reconstructed from reverse engineering of the R-Net Programmer software.

## Overview

- **Source:** Reverse engineering of RNet Programmer5 OEM.exe v5.7.0, IRConfigurator.exe, RNET_G4O_ENG help system
- **Manufacturer:** PG Drives Technology (Penny and Giles Controls Ltd), now Curtiss-Wright
- **Programming dongle:** Part D50610 (FTDI USB-to-CAN bridge)

The R-Net system is a modular CAN bus network used in power wheelchairs. Each module type has a specific role and set of configurable parameters accessible through the R-Net Programmer software. All communication runs over CAN 2.0B at 125 Kbps.

---

## R-Net Device Types

| Device | Full Name | Role |
|--------|-----------|------|
| PM | Power Module | Central hub / motor controller |
| JSM | Joystick Module | Standard joystick input |
| JSM-LED | Joystick Module (LED) | Joystick with LED indicators |
| cJSM / CxSM | Color Joystick Module | Joystick with color display |
| ISM | Intelligent Seating Module | 6-channel actuator control + lighting |
| ISM-8 / CxSM | Extended Seating Module | 8-channel actuator control |
| IOM | Input/Output Module | Generic I/O expansion |
| Omni | Omni Module | Specialty input (sip-and-puff, IR, scanning) |
| Mouse / Mouse 2 | Bluetooth Mouse Module (BTM) | Bluetooth mouse pointer control |
| iDevice | iOS Interface Module | iOS VoiceOver control |
| ASM | Advanced Stability Module | Accelerometer-based stability |
| TM | Tilt Module | Incline/slope sensing |
| Gyro | Gyro Module | Angular velocity sensing |
| Encoder | Encoder Module | Motor encoder feedback |
| DTT | Diagnostic/Programming Tool | Hand-held programmer |

---

## Device Descriptions

### PM (Power Module)

The PM is the central hub and motor controller for the entire R-Net system. All other devices communicate through or are coordinated by the PM.

**Capabilities:**
- Controls 2 drive motors (M1, M2) with independent current monitoring
- Tracks battery level, voltage, and current
- Tracks distance (total + trip odometer) and operating time
- Manages up to 8 profiles (Profile 1-7 + Attendant)
- Manages modes and mode maps (which profiles are available in which modes)
- Maintains a real-time clock (RTC)
- Handles device enumeration and serial number challenge/response authentication
- Enforces safety fences (parameter limits set by OEM)

**Diagnostic Status:**
- Battery Gauge, Battery Voltage, Battery Current
- Motor Voltage (M1, M2), Motor Current (M1, M2)
- Heatsink Temperature
- Inhibit band status

**Key CAN Frames:**
- `0x7B3#` / `0x7B3#R` - Serial number exchange request
- `0x7B1#` / `0x7B0#` - Drop to config mode 1/0
- `0x1C0C0X00#Xx` - Battery level broadcast (every 1000ms)
- `0x14300X00#LlHh` - Drive motor current (every 200ms)

---

### JSM (Joystick Module) / JSM-LED

The standard joystick input device. The JSM-LED variant adds LED indicators for mode/status display.

**Capabilities:**
- Analog joystick with configurable throw range and deadband per direction
- Sends joystick X/Y position frames every 10ms (`0x02000X00`)
- Serial heartbeat every 50ms (`0x00E#XXXXXXXX00000000`)
- Device heartbeat every 100ms (`0x03C30F0F#8787878787878787`)
- Speed paddle buttons for speed adjustment
- Profile button for switching profiles
- Horn button

**Key CAN Frames:**
- `0x02000X00#XxYy` - Joystick position (int8 X, int8 Y), every 10ms
- `0x00E#XXXXXXXX00000000` - Serial number heartbeat, every 50ms
- `0x03C30F0F#8787878787878787` - Device heartbeat, every 100ms
- `0x00C#` - Network connection test (checks for ACK)

---

### cJSM / CxSM (Color Joystick Module)

Joystick module with a color LCD display. The display does NOT receive raw bitmap/pixel data over CAN; all graphics are stored in cJSM firmware.

**Capabilities:**
- Color display with text sent as ASCII via register 0x8C in 4-byte chunks
- All icons and graphics built into firmware
- Custom status display support via CxSMStatus.ini
- Uses slot 8+ range (`0x1F8X`) for serial number authentication
- Trip distance reset capability

**Mode Output Types:**
- Drive
- Seating
- Environmental
- Mouse
- Programming
- Output 3-7
- IR Control

**Display Text Transfer Protocol:**
```
Request:  0x78X#208CXXXX...  (X = device slot)
Response: 0x79X#208CXXXX...

Data format:
  Byte 0: 0x20 (command = data)
  Byte 1: 0x8C (register = text display)
  Bytes 2-3: 0x0000
  Bytes 4-7: ASCII text (4 characters per frame)
```

**Authentication Failure Behavior:**
When authentication fails, the cJSM sends a repeated "cry for help" pattern:
```
0x1F800010#, 0x1F800011#, 0x1F800012#, 0x1F800013#  ; Trying slot 8
0x1F810000#, 0x1FA00000#                              ; Retrying/error state
```

---

### ISM (Intelligent Seating Module)

Controls powered seating functions (tilt, recline, elevate, etc.) and manages vehicle lighting.

**Actuator Outputs:**
- 6 actuator output channels with individual current monitoring
- Per-axis configurable: acceleration, deceleration, speed, current limit, endstop detection

**Lighting Outputs:**
- Brake lights
- Horn
- Left/right driving lamps
- Left/right turn indicators

**Indicator Fault Detection:**
- Short circuit detection
- Single bulb failure detection
- Open circuit detection

**Inhibit Inputs:**
- 2 inhibit input channels (Channel 4, Channel 5)
- 4 bands per inhibit input (see Inhibit System section)

**Lamp Voltage:**
- Configurable at 15V, 20V, 25V, 30V, or 35V

**Diagnostic Status:**
- Channel 1-6 Current
- Total Current
- Axis Direction
- Various fault indicators

---

### ISM-8 / CxSM (Extended Seating Module)

Expanded version of the ISM with additional actuator channels.

**Capabilities:**
- 8 actuator channels (expanded from ISM's 6)
- Different inhibit handling with separate threshold levels per band
- Compatible with CxSM color display integration
- All ISM features plus extended channel support

---

### IOM (Input/Output Module)

Generic input/output expansion module for the R-Net bus.

**Capabilities:**
- Configurable input types
- Output switching
- Horn operation control
- Extends the I/O capacity of the system

---

### Omni Module

A specialty input device with a color display, designed for users who cannot operate a standard joystick.

**Input Methods:**
- IR transmitter and receiver (learns and sends IR codes)
- Sip-and-puff interface (pneumatic switch input)
- Scan control for switch scanning input
- 9-way switch support
- SID (Switch Input Device) configuration

**Features:**
- Color display
- User menu with 16 configurable positions
- Training mode with directional inhibits
- Trip distance reset capability

**IR Configuration:**
- IR Mode = Mode 7 default
- Input: Raw, Output: IR Control
- File formats: `.RnIR` / `.RnIR2`

---

### Mouse / Mouse 2 (BTM - Bluetooth Mouse Module)

Provides Bluetooth mouse pointer control, allowing the wheelchair joystick to act as a computer mouse.

**Parameters:**
- Nudge parameters (forward/reverse/left/right distance, nudge time)
- Pointer speed and acceleration
- Action/deflection beeps
- Double click time
- External switch inputs
- Screen graphic selection

**CAN Differences:**
- Uses different XOR table for serial number authentication than JSM
- Status frames: `0x0A400002#`, `0x0A400102#`, `0x0A400300#`, `0x0A400301#`

---

### iDevice

Interface module for controlling iOS devices via the wheelchair joystick.

**Capabilities:**
- VoiceOver control mappings
- Short/medium/long press actions per joystick direction
- External switch actions
- Speed up/down controls

---

### ASM (Advanced Stability Module)

Accelerometer-based stability sensing module for enhanced driving safety.

**Capabilities:**
- Accelerometer-based stability sensing
- Anti-spin control
- Orientation sensing with null calibration
- Accelerometer threshold configuration
- Tilt input integration

---

### Tilt Module (TM)

Incline and slope sensing module.

**Capabilities:**
- Incline/slope sensing
- Orientation configuration
- Speed compensation for driving on slopes

---

### Gyro Module

Gyroscope module for angular velocity sensing and closed-loop stability control.

**PID Control Parameters:**
- Proportional gain
- Integral gain
- Dynamic gain
- Low-speed proportional gain
- Low-speed integral gain
- Low-speed dynamic gain

---

### Encoder Module

Motor encoder feedback module for closed-loop speed control.

**Per-Motor Configuration (M1, M2):**
- Error speed limit
- Motor inversion
- Resolution setting
- Motor rated speed

---

### DTT (Diagnostic/Programming Tool)

Hand-held programming device used by dealers for field configuration.

**Capabilities:**
- Read and write configuration parameters
- Write Subset files (`.rnss`)
- Fault code reading and clearing
- Limited compared to full R-Net Programmer software

---

## Configuration Parameter Reference

### Profile System

The R-Net system supports 8 profiles:
- **Profile 1-7:** User-selectable driving profiles
- **Attendant (Profile 8):** Dedicated attendant/caregiver profile

Each profile is independently configurable with its own speed, acceleration, and motor parameters.

**Parameter Groups:**
- GLOBAL - System-wide settings
- PROFILE - Per-profile settings
- EXPANSION 1 - Extended parameter set 1
- EXPANSION 2 - Extended parameter set 2

**Configuration Groups:**
- GENERIC
- GROUP1 through GROUP7

---

### Speed Parameters (per profile)

Each profile has 18 speed-related parameters:

| Parameter | Description |
|-----------|-------------|
| Forward Speed (max) | Maximum forward speed |
| Forward Speed (min) | Minimum forward speed (speed adjust lower limit) |
| Reverse Speed (max) | Maximum reverse speed |
| Reverse Speed (min) | Minimum reverse speed |
| Turn Speed (max) | Maximum turning speed |
| Turn Speed (min) | Minimum turning speed |
| Forward Acceleration (max) | Maximum forward acceleration rate |
| Forward Acceleration (min) | Minimum forward acceleration rate |
| Reverse Acceleration (max) | Maximum reverse acceleration rate |
| Reverse Acceleration (min) | Minimum reverse acceleration rate |
| Turn Acceleration (max) | Maximum turn acceleration rate |
| Turn Acceleration (min) | Minimum turn acceleration rate |
| Forward Deceleration (max) | Maximum forward deceleration rate |
| Forward Deceleration (min) | Minimum forward deceleration rate |
| Reverse Deceleration (max) | Maximum reverse deceleration rate |
| Reverse Deceleration (min) | Minimum reverse deceleration rate |
| Turn Deceleration (max) | Maximum turn deceleration rate |
| Turn Deceleration (min) | Minimum turn deceleration rate |
| Power | Motor power level |
| Torque | Motor torque level |
| Tremor Damping | Input filtering for tremor conditions |
| Fast Brake Rate | Emergency/fast braking rate |

---

### Motor Parameters

| Parameter | Description |
|-----------|-------------|
| Max Current Limit | Maximum motor current |
| Min Current Limit | Minimum motor current |
| Boost Drive Current | Temporary over-current for hill starts |
| Boost Drive Time | Duration of boost current |
| Current Foldback Threshold | Current level that triggers thermal foldback |
| Current Foldback Time | Sustained time before foldback activates |
| Current Foldback Level | Reduced current level during foldback |
| Compensation Factor | Per-profile motor compensation |
| Motor Swap | Swap M1/M2 outputs |
| Invert M1 Direction | Reverse motor 1 direction |
| Invert M2 Direction | Reverse motor 2 direction |
| Steer Correct | Steering correction factor |
| Display Speed | Speed shown on display |
| Max Rated Speed | Maximum rated motor speed |
| Max Displayed Speed | Maximum speed shown on display |
| Joystick Stationary Time | Time joystick must be centered before declaring stationary |
| Joystick Stationary Range | Joystick center deadzone for stationary detection |

---

### Inhibit System

The inhibit system allows external switches or sensors to limit speed or disable functions based on configurable voltage thresholds.

**4 Input Bands Per Inhibit:**

| Band | Condition | Description |
|------|-----------|-------------|
| Band 0 | Closed to 0V | Switch closed / shorted to ground |
| Band 1 | Low threshold | Low voltage range |
| Band 2 | Mid threshold | Mid voltage range |
| Band 3 | Open/disconnected | No connection / high impedance |

Each band can be configured to:
- Limit drive speed to a configurable level (0-3)
- Disable specific functions
- Trigger warnings

**Per-Module Inhibit Inputs:**
- PM: Built-in inhibit inputs
- ISM: Channel 4 and Channel 5
- ISM-8/CxSM: Extended inhibit with separate threshold levels
- ASM/TM: Stability-related inhibit

Drive inhibits and actuator inhibits are configured separately.

---

### Battery Parameters

| Parameter | Description |
|-----------|-------------|
| Low Battery Alarm Level | Battery percentage threshold for audible alarm |
| Low Battery Flash Level | Battery percentage threshold for flashing display |
| Cable Resistance | Battery cable resistance compensation (accounts for voltage drop) |
| Calibration Factor | Battery gauge calibration adjustment |
| Low Voltage Cut-out | Voltage threshold for system shutdown |
| Low Voltage Cut-out Time | Delay before shutdown after threshold reached |

---

### Controls - Global

System-wide control parameters:

| Parameter | Description |
|-----------|-------------|
| Profile Button | Enable/disable profile switching button |
| Speed Adjust | Enable/disable speed adjustment |
| Sounder Volume | System beeper volume level |
| Lock Function | Enable/disable control system lock |
| Reverse Driving Alarm | Audible alarm when driving in reverse |
| Emergency Stop Switch | E-stop switch configuration |
| OBP Keycode Entry | On-Board Programmer keycode for access |
| Power-Up Mode | Which mode activates on power-up |
| Start Up Beep | Enable/disable power-on beep |
| External Profile Jack | External profile selection input |
| Actuator Switches While Driving | Allow/disallow seating adjustment while driving |

---

### Controls - Joystick

Per-direction joystick configuration:

| Parameter | Description |
|-----------|-------------|
| Forward Throw | Forward deflection range |
| Reverse Throw | Reverse deflection range |
| Left Throw | Left deflection range |
| Right Throw | Right deflection range |
| Deadband | Center deadzone size |
| Axis Inversion | Invert joystick axis |
| Axis Swap | Swap X and Y axes |

---

### Controls - Profiled

Per-profile control behavior:

| Parameter | Description |
|-----------|-------------|
| Change Mode While Driving | Allow/disallow mode changes while in motion |
| Sleep Timer | Time before entering sleep mode |
| Standby Operation | Standby behavior configuration |
| Standby Time | Time before entering standby |
| Standby Direction | Which joystick direction triggers standby |
| Standby Mode | Mode to enter during standby |
| Remote Selection | Remote control input selection |

---

### Controls - Speed Paddles

Speed paddle button configuration:

| Parameter | Description |
|-----------|-------------|
| Operation Mode | Speed paddle behavior (momentary, toggle, etc.) |
| Step Size | Speed increment per press |
| Step Rate | Speed change rate when held |
| Wrap Time | Time to wrap from max to min speed |
| Wrap Delay | Delay before wrap activates |
| Wrap Beep | Audible feedback at wrap point |

---

### Latched Control

Latched drive mode allows the wheelchair to maintain speed without continuous joystick input.

| Parameter | Description |
|-----------|-------------|
| Latched Drive Mode | Enable/disable latched driving |
| Latched Drive Speed | Speed setting for latched mode |
| Latched Drive Spin | Turn behavior in latched mode |
| Latched Drive State | Current latch state |
| Latched Drive Flags | Latch mode configuration flags |
| Latched Actuators | Latch behavior for seating actuators |
| Latched Timeout | Time before latch disengages |
| Latched Timeout Beep | Audible warning before timeout |

---

### Seating (ISM/ISM-8)

Per-axis seating actuator parameters:

| Parameter | Description |
|-----------|-------------|
| Acceleration | Actuator acceleration rate |
| Deceleration | Actuator deceleration rate |
| Speed | Actuator movement speed |
| Current Limit | Maximum actuator current |
| Endstop Detect | End-of-travel detection threshold |

- ISM: Up to 6 axes
- ISM-8/CxSM: Up to 8+ axes

---

### Lights

| Parameter | Description |
|-----------|-------------|
| Indicator Fault Detection | Enable/disable turn signal fault monitoring |
| Swap Indicators | Swap left/right turn signal outputs |
| Lamp Voltage | Output voltage: 15V, 20V, 25V, 30V, or 35V |
| Brake Lights | Brake light behavior configuration |
| Horn | Horn output configuration |

---

### Stability (ASM/Gyro/Tilt)

**ASM Parameters:**

| Parameter | Description |
|-----------|-------------|
| ASM Function | Stability function mode |
| ASM Orientation | Mounting orientation |
| ASM Calibration | Null calibration (level reference) |
| Accelerometer Threshold | Trigger threshold for stability intervention |
| Anti-Spin | Anti-spin control configuration |

**Tilt Parameters:**

| Parameter | Description |
|-----------|-------------|
| Tilt Orientation | Mounting orientation |

**Gyro Parameters:**

| Parameter | Description |
|-----------|-------------|
| Proportional Gain | P-gain for PID control |
| Integral Gain | I-gain for PID control |
| Dynamic Gain | D-gain for PID control |
| Low-Speed Proportional Gain | P-gain at low speeds |
| Low-Speed Integral Gain | I-gain at low speeds |
| Low-Speed Dynamic Gain | D-gain at low speeds |

---

### Omni Sip-and-Puff

| Parameter | Description |
|-----------|-------------|
| Puff Threshold | Pressure level to register a puff |
| Sip Threshold | Pressure level to register a sip |
| Deadband | Pressure deadzone between sip and puff |
| Ramp Up Rate | Speed ramp-up rate on sustained input |
| Ramp Down Rate | Speed ramp-down rate on input release |

---

### Engineering Parameters

Low-level tuning parameters (typically OEM-only):

| Parameter | Description |
|-----------|-------------|
| Low Forward | Low-speed forward tuning |
| Soft Forward | Soft-start forward tuning |
| Backlash | Mechanical backlash compensation |
| Spin Parameters | Anti-spin tuning values |

---

### OEM Factory Settings

Parameters restricted to OEM access level:

| Parameter | Description |
|-----------|-------------|
| Safety Fences | Parameter limits to prevent dangerous configurations |
| Latched Drive Enabled | Master enable for latched drive feature |

Safety fences define the maximum and minimum values that dealer-level programmers can set for speed, current, and other safety-critical parameters. Only OEM-level access can modify fence values.

---

## Controller Features

### Controller Personality

An OEM-customizable package containing:
- Language strings (multi-language support)
- OBP (On-Board Programmer) content and menu structure
- Error message definitions and trip code text

Created by PGDT per OEM requirements. Each wheelchair manufacturer (Permobil, Quickie, Quantum, etc.) has their own personality file defining the user-facing text and menu options.

### Controller Locking

The control system can be locked to prevent unauthorized programming. When locked:
- Requires Unlock command via programmer to modify parameters
- Protects against unauthorized configuration changes
- Lock state persists across power cycles

### System Timers

Per-module operational timers are readable via the programmer:
- Total operating time
- Per-module run time
- Useful for maintenance scheduling and warranty tracking

### Distance Tracking

The PM tracks:
- **Total Distance:** Lifetime odometer, non-resettable
- **Trip Distance:** Resettable trip odometer

Trip distance can be reset from:
- cJSM user menu
- Omni module user menu
- Programmer software

### Event/Fault Logging

Per-module error history with trip codes.

**Trip Code Format:** `XXXX` (4-digit hex)

**Example Trip Codes:**

| Code | Description |
|------|-------------|
| 2F01 | Center Joystick |
| 810D | System Error |
| 1506 | M2 Solenoid Brake Fault |

The fault log can be cleared per-node or system-wide via the programmer.

### Real-Time Clock

The PM maintains an RTC (Real-Time Clock):
- Readable via programmer (ReadDateTime command)
- Writable via programmer (SendDateTime command)
- Used for timestamping fault log entries

---

## File Formats

| Extension | Description |
|-----------|-------------|
| `.R-net` | Full programming/configuration file (complete system snapshot) |
| `.rnss` | Subset file (partial parameter set, writable by DTT) |
| `.rnsi` | System log/information export |
| `.lyo` | Screen layout preferences (programmer UI) |
| `.RnIR` | Omni IR configuration (original format) |
| `.RnIR2` | Omni IR configuration (v2 format) |
| `.rnd` | Encrypted device database (Blowfish-ECB encryption) |
| `.PCP` | Auxiliary parameter/configuration page |

See `RNET_CONFIG_FILE_FORMAT.md` for detailed `.R-net` file format specification.

---

## Access Level Hierarchy

| Level | Permissions |
|-------|-------------|
| OEM | Full access: manufacturing mode, safety fence editing, all parameters |
| Dealer | Standard programming: cannot modify safety fences or OEM-only parameters |
| User | Limited access: via cJSM/Omni on-screen menus only |

Access level is enforced by the programming dongle EEPROM. The dongle's stored access level determines what the software allows. Connecting a lower-access dongle demotes the software to that access level for the session.

**Implications:**
- OEM dongles are restricted to authorized manufacturers
- Dealer dongles are distributed to authorized service centers
- Users have no dongle; all user-accessible settings are available through the on-chair display menus

### Programming Dongles

| Part Number | Access Level | Description |
|-------------|-------------|-------------|
| **D50609** | Dealer | Dealer-level R-Net programmer dongle. Cannot modify safety fences, motor voltage, or OEM-only parameters. |
| **D50610** | OEM | OEM-level R-Net programmer dongle. Full access to all parameters including motor compensation and engineering settings. |

**Hardware:** Both dongles use an **FTDI FT232** USB-to-serial chip with CAN interface. Device description string: `"RNet Dongle"`. Latency timer: 1ms.

**Protocol:** POP (Parameter Object Protocol) on CAN IDs 0x78F (request) / 0x793 (response). See `docs/POP_PROTOCOL.md`.

**Network behavior:** When a dongle is inserted and the chair powers on, the R-Net network reconfigures — the dongle is assigned its own slot (0xF) and goes through serial number authentication like any other device. The dongle announces presence with `0x7A0#` (empty frame).

### OBP (On-Board Programming)

OBP is the chair's built-in programming mode, providing **dealer-equivalent** access. Mode 8 is reserved for OBP. Originally designed to require a dongle; button combo is an alternative.

| Method | Activation | Access Level |
|--------|-----------|-------------|
| Hardware dongle | Insert D50609/D50610, power on, press Mode to cycle to Mode 8 | Per dongle (dealer or OEM) |
| Button combo | Horn + On/Off through bleep sequence | Dealer-equivalent (speed, accel, decel, torque, tremor) |

**OBP Keycode Entry:** An OEM-level boolean parameter in PM EEPROM. When disabled (0x00), the button combo is locked out. The dongle method still works. Can be re-enabled via POP protocol — see `docs/OBP_ENABLE_GUIDE.md`.

**Controller Personality:** The OBP menu structure (what parameters appear) is a separate binary blob called "Controller Personality" in the PC Programmer. Two known variants: "Permobil ESP" (ESP speed params) and "PGDT Generic" (normal PM speed params). Changed via `Controller → Set Controller Personality`.

**Related systems:**
- **OBP** = On Board Programming — R-Net drive parameters (CAN bus, POP/parameter exchange)
- **OBC** = On Board Configuring — ICS seating parameters (LIN bus, WheelchairBuilder)
- **PCP** = PC-Programmer — official name for R-Net Programmer desktop software

**Source:** R-Net OBP Manual SK78571/4, R-Net Technical Manual SK77981/12

---

*Reconstructed from reverse engineering of RNet Programmer5 OEM.exe v5.7.0, IRConfigurator.exe, DongleInterface.dll v3.0.0.0, and RNET_G4O_ENG help system. OBP details from R-Net OBP Manual SK78571/4. (C) PG Drives Technology / Curtiss-Wright. For wheelchair accessibility research.*
