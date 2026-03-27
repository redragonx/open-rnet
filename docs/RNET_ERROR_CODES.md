# R-Net Error Code Reference

Complete error code reference for R-Net power wheelchair electronics. Error codes are transmitted on the CAN bus as part of device status frames and can be read via on-screen display (system faults), R-Net PC Programmer, On-Board Programming (OBP), or CAN bus monitoring. This document covers PGDT Power Module errors, non-PGDT device errors (input devices, ESP, etc.), and ICS seating system errors.

---

## PGDT Power Module Error Codes

Source: "PGDT R-net Error Code List with Remedies v1" (Rev 1, 2009-06-01)

### Memory/EEPROM Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x0001 | Memory Error | Running Ram Check Error | System fault | Memory Error | 1 |
| 0x0200 | PM Memory Error | EEPROM Check Error | System fault | PM Memory Error | 2 |
| 0x0203 | Calibration Error | EEPROM Calibration Data Check Error | System fault | Cal Error | 3 |
| 0x0204 | Memory Error | EEPROM Programming Data Check Error | System fault | Memory Error | 1 |
| 0x0208 | Memory Error | EEPROM Persistent Data Check Error | System fault | Memory Error | 1 |

### Power/Supply Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x0500 | Reference Hold Error | | Control fault | | TBD |
| 0x0600 | Error Converting 0V Mux 0 Connection | | Control fault | | 3 |
| 0x0601 | Error Converting 0V Mux 1 Connection | | Control fault | | 3 |
| 0x0602 | Error Converting 0V Mux 2 Connection | | Control fault | | 3 |
| 0x0603 | Error Converting 0V Mux 3 Connection | | Control fault | | 3 |
| 0x0703 | Joystick Supply Failure | | Control fault | | TBD |
| 0x0704 | 12V Supply Failure | | Control fault | | 3 |
| 0x0707 | Regulator Supply Failure | | Control fault | | 3 |

### Joystick Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x0808 | Joystick Error | Mid Reference Error | System fault | Joystick Error | 4 |
| 0x080A | Joystick Error | Mid Reference Comparison Error | System fault | Joystick Error | 4 |
| 0x080B | Joystick Error | Mid Reference Comparison Startup Error | System fault | Joystick Error | 4 |
| 0x0905 | SID Detached | OMNI Input Device Disconnected | System fault | SID Disconnected | 5 |
| 0x0A00 | Gone To Sleep | | System fault | Gone to Sleep | 6 |
| 0x0E00 | Joystick Error | Joystick Error Right | System fault | Joystick Error | 4 |
| 0x0E02 | Joystick Error | Joystick Error Forward | System fault | Joystick Error | 4 |
| 0x1200 | Joystick Error | Dual Path Comparison Right Error | System fault | Joystick Error | 4 |
| 0x1202 | Joystick Error | Dual Path Comparison Forward Error | System fault | Joystick Error | 4 |
| 0x2F01 | Center Joystick | | System fault | Center Joystick | 4 |

### EEPROM Operation Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x0B00 | EEPROM | Write Error | Control fault | | TBD |
| 0x0B01 | EEPROM | Not Busy Fault | Control fault | | TBD |
| 0x0B02 | EEPROM | Write Timeout | Control fault | | TBD |
| 0x0B08 | EEPROM | Address Out Of Range | Control fault | | TBD |

### Current Limit Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1302 | Current Limit | Reference Fault | Control fault | | TBD |
| 0x1304 | Current Limit | Failed To Operate When Positive Input | Control fault | | TBD |
| 0x1308 | Current Limit | Left Sense Trip | Control fault | | 3 |
| 0x1309 | Current Limit | Right Sense Trip | Control fault | | 3 |
| 0x130A | Current Limit | Startup Fault | Control fault | | 3 |
| 0x1310 | Current Limit | Sense Trip | Control fault | | 3 |
| 0x1404 | Motors Cross Coupled | | Control fault | | 3 |

### Brake Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1503 | Solenoid Brake | Driver Fault | Control fault | | 3, 7, 8 |
| 0x1504 | Solenoid Brake | Interlock Fault | Control fault | | 3, 7, 8 |
| 0x1505 | M1 Solenoid Brake Fault | | System fault | M1 Brake Error | 7 |
| 0x1506 | M2 Solenoid Brake Fault | | System fault | M2 Brake Error | 8 |

### Battery Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1600 | High Battery Voltage | | System fault | High Battery | 9 |
| 0x1601 | High Battery Voltage | Overvoltage Comparator Tripped | System fault | High Battery | 9 |
| 0x2C00 | Low Battery Voltage | | System fault | Low Battery | 14 |
| 0x2C01 | Low Battery Voltage | Very Low Battery Voltage (<16v) | System fault | Low Battery | 14 |
| 0x2C02 | Low Battery Voltage | Low Battery Lockout (<16v) | System fault | Low Battery | 14 |

### Relay Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1700 | Relay On In Standby | | Control fault | | TBD |
| 0x1701 | Relay Off In Drive | | Control fault | | TBD |
| 0x1703 | Relay Interlock Fault | | Control fault | | 3, 10 |
| 0x1704 | Relay Driver Fault | | Control fault | | TBD |
| 0x1705 | Relay Stuck Closed | | Control fault | | 3, 10 |
| 0x1801 | Watchdog Failed To Trip | | Control fault | | 3, 10 |

### Inhibit Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1E03 | Inhibit Active | Charger Connected | System fault | Charging | 11 |
| 0x1E07 | User Switch Detached | | System fault | Switch Detached | 12 |
| 0x1E20-0x1E3F | Inhibit Active | (32 individual inhibit inputs) | System fault | Inhibit Active | 13 |

Note: The last 2 hex digits indicate which inhibit is active (e.g., 0x1E20 = Inhibit 2, 0x1E21 = Inhibit 3, 0x1E22 = Inhibit 4, 0x1E23 = Inhibit 5).

### Motor Current Feedback Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1B01 | Right Forward Current Null Bad | | Control fault | | 3 |
| 0x1B02 | Right Reverse Current Null Bad | | Control fault | | 3 |
| 0x1B10 | Positive Current Feedback Null Bad | | Control fault | | 3 |
| 0x1C01 | Left Forward Current Null Bad | | Control fault | | 3 |
| 0x1C02 | Left Reverse Current Null Bad | | Control fault | | 3 |
| 0x1C10 | Negative Current Feedback Null Bad | | Control fault | | 3 |

### Front End / Switch Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x1D00 | Front End Fault | | Control fault | | TBD |
| 0x1D03 | Switch Input | Pullup Circuit Failure | Control fault | | TBD |

### Feedback Voltage Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x2A00 | Feedback Voltage Fault Right | | Control fault | | 3 |
| 0x2A01 | Right Voltage Null Bad | | Control fault | | 3 |
| 0x2B00 | Feedback Voltage Fault Left | | Control fault | | 3 |
| 0x2B01 | Left Voltage Null Bad | | Control fault | | 3 |

### Bridge / Verification Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x3100 | Low Bridge Voltage | | Control fault | | 3, 10 |
| 0x3101 | Bridge To Battery Short | | Control fault | | 3 |
| 0x3203 | Port 2 Verification Error | | Control fault | | TBD |
| 0x3211 | Bad Settings | Parameter Range Error | System fault | Bad Settings | 15 |
| 0x3215 | ADC Storage Error | | Control fault | | TBD |
| 0x3611 | Failed To Arm Trip Latch | | Control fault | | 3 |

### Settings / System Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x3A00 | Bad Settings | | System fault | Bad Settings | 15 |
| 0x3A05 | System Power Cycle Required | | System fault | Cycle Power | 16 |

### Motor Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x3B00 | M1 Motor Open Circuit | | System fault | M1 Motor Error | 17 |
| 0x3C00 | M2 Motor Open Circuit | | System fault | M2 Motor Error | 18 |
| 0x3D00 | M1 Motor Shorted High | | System fault | M1 Motor Error | 19 |
| 0x3D01 | M1 Motor Shorted Low | | System fault | M1 Motor Error | 20 |
| 0x3E00 | M2 Motor Shorted High | | System fault | M2 Motor Error | 21 |
| 0x3E01 | M2 Motor Shorted Low | | System fault | M2 Motor Error | 22 |

### Drive Timeout

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x6401 | Latched Drive Timeout | Latched drive timeout expired | System fault | Latched TO | 23 |

### Temperature

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x7902 | High Temperature | | Control fault | | 24 |

### Actuator/Seating Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x7A08 | Overtemperature (Actuators) | Actuator Driver Over Temperature | System fault | Overtemp. (Acts) | 25 |
| 0x7A09 | Actuator Driver Error | Enabled In Standby | Control fault | | 25 |
| 0x7A0A | Actuator Driver Error | Disabled In Drive | Control fault | | 25 |
| 0x7A0B | Actuator Driver Failure | | Control fault | | 25 |
| 0x7A0C | Over-current Actuator | Channel Current Exceeded | System fault | Over-current | 25 |
| 0x7A0D | Channel Current Amplifier Failure | | Control fault | | 25 |
| 0x7A0E | Over-current Actuator Channel | Actuator Current Sensor Temperature | System fault | Over-current | 25 |
| 0x7A12 | Actuator 1 Shorted High | | Control fault | | 25 |
| 0x7A13 | Actuator 1 Shorted Low | | Control fault | | 25 |
| 0x7A22 | Actuator 2 Shorted High | | Control fault | | 25 |
| 0x7A23 | Actuator 2 Shorted Low | | Control fault | | 25 |
| 0x7A32 | Actuator 3 Shorted High | | Control fault | | 25 |
| 0x7A33 | Actuator 3 Shorted Low | | Control fault | | 25 |
| 0x7A42 | Actuator 4 Shorted High | | Control fault | | 25 |
| 0x7A43 | Actuator 4 Shorted Low | | Control fault | | 25 |
| 0x7A52 | Actuator 5 Shorted High | | Control fault | | 25 |
| 0x7A53 | Actuator 5 Shorted Low | | Control fault | | 25 |
| 0x7A62 | Actuator 6 Shorted High | | Control fault | | 25 |
| 0x7A63 | Actuator 6 Shorted Low | | Control fault | | 25 |
| 0x7A90 | Over-current Actuator Channel | Common Current Exceeded | System fault | Over-current | 25 |
| 0x7A91 | Total Current Amplifier Failure | | Control fault | | 25 |

### Thermistor

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x7C00 | Thermistor Fault | Thermistor measurement is out of range | Control fault | | 3 |

### PM Memory/Repository Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x7E00 | PM Memory Error | Running Repository Error | System fault | PM Memory Error | 2 |
| 0x7E01 | PM Memory Error | Unable to Open PM Req File | System fault | PM Memory Error | 2 |
| 0x7E02 | Memory Error | Unable to synchronise with Repository | System fault | Memory Error | 1 |
| 0x7E03 | Memory Error | Failed to cancel queued message | System fault | Memory Error | 1 |
| 0x7E04 | Memory Error | Repository aborted transfer | System fault | Memory Error | 1 |
| 0x7E05 | Memory Error | Repository timeout during transfer | System fault | Memory Error | 1 |
| 0x7E06 | Memory Error | Invalid Repository node number detected | System fault | Memory Error | 1 |
| 0x7E07 | Memory Error | Incompatible file format | System fault | Memory Error | 1 |
| 0x7E08 | Memory Error | Bad data in Repository file | System fault | Memory Error | 1 |
| 0x7E09 | Memory Error | Bad descriptor in Repository file | System fault | Memory Error | 1 |
| 0x7E0A | Memory Error | Old file format in Repository cannot restore corrupt file | System fault | Memory Error | 1 |
| 0x7E0B | Memory Error | File Slot CRC does not match | System fault | Memory Error | 1 |
| 0x7E0C | Memory Error | Special File sequence error | System fault | Memory Error | 1 |
| 0x7E0D | Memory Error | Incompatible Special File format | System fault | Memory Error | 1 |
| 0x7E0E | Memory Error | Unable to repair corrupt Special File | System fault | Memory Error | 1 |
| 0x7E0F | Memory Error | Invalid Special File version in Repository | System fault | Memory Error | 1 |
| 0x7E10 | Memory Error | Invalid Special File variant | System fault | Memory Error | 1 |
| 0x7E11 | Memory Error | Upgrade would mix Special File variants | System fault | Memory Error | 1 |
| 0x7E12 | Memory Error | Unable to repair corrupt Special File set | System fault | Memory Error | 1 |
| 0x7E13 | Memory Error | Failed to delete Special File in order to repair set | System fault | Memory Error | 1 |
| 0x7E14 | Memory Error | Repository aborted transfer - Special File | System fault | Memory Error | 1 |
| 0x7E15 | Memory Error | Repository timeout during transfer - Special File | System fault | Memory Error | 1 |
| 0x7E20 | Memory Error | Get Repository Timeout | System fault | Memory Error | 1 |
| 0x7E21 | Memory Error | Release Repository Timeout | System fault | Memory Error | 1 |
| 0x7E22 | Memory Error | Check Repository Timeout | System fault | Memory Error | 1 |
| 0x7E23 | Memory Error | Repository Taken | System fault | Memory Error | 1 |
| 0x7E24 | Memory Error | Repository Not Released | System fault | Memory Error | 1 |
| 0x7E25 | Memory Error | Set Values Get File Slot Error | System fault | Memory Error | 1 |
| 0x7E26 | Memory Error | Set Values Set Slot Location Error | System fault | Memory Error | 1 |
| 0x7E27 | Memory Error | Slot Write Error | System fault | Memory Error | 1 |
| 0x7E28 | Memory Error | Set Values Slot Data Error | System fault | Memory Error | 1 |
| 0x7E29 | Memory Error | Set Values Get File Slot Error | System fault | Memory Error | 1 |
| 0x7E2A | Memory Error | Get Values Get File Slot Error | System fault | Memory Error | 1 |
| 0x7E2B | Memory Error | Get Values Set Slot Location Error | System fault | Memory Error | 1 |
| 0x7E2C | Memory Error | Get Values Slot Data Error | System fault | Memory Error | 1 |
| 0x7E2E | Memory Error | Get Size Get File Slot Error | System fault | Memory Error | 1 |
| 0x7E2F | Memory Error | Get Slot Size Error | System fault | Memory Error | 1 |
| 0x7E30 | Memory Error | Get Operating Time Error | System fault | Memory Error | 1 |
| 0x7E34 | Memory Error | Get Eventlog Event Error | System fault | Memory Error | 1 |
| 0x7E35 | Memory Error | Get Org Number Error | System fault | Memory Error | 1 |
| 0x7E36 | Memory Error | Get Attributes Get File Slot Error | System fault | Memory Error | 1 |
| 0x7E37 | Memory Error | Get Slot Check Error | System fault | Memory Error | 1 |
| 0x7E38 | Memory Error | Set Slot Verify Error | System fault | Memory Error | 1 |
| 0x7E39 | Memory Error | Get File Attributes Error | System fault | Memory Error | 1 |
| 0x7E3A | Memory Error | Repository Data Corrupt | System fault | Memory Error | 1 |

### CAN Bus Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x7F00 | Bad Cable | CAN Transceiver in fault tolerant mode | System fault | Bad Cable | 26 |
| 0x8100 | System Error | CAN Device Off-line | System fault | System Error | 27 |
| 0x8101 | Bus Off | | Control fault | | TBD |
| 0x8102 | CAN Receiver Overrun | | Control fault | | TBD |
| 0x8103 | Memory Error | Rebus Tx Queue Full | System fault | Memory Error | 1 |
| 0x8104 | System Error | Rx DLC Not As Expected | System fault | System Error | 27 |
| 0x8105 | DIME Error | | System fault | DIME Error | 28 |
| 0x8106 | System Error | Config Failure | System fault | System Error | 27 |
| 0x8107 | System Error | Rebus Event Queue Overflow | System fault | System Error | 27 |
| 0x8108 | System Error | Config Data Access Error | System fault | System Error | 27 |
| 0x8109 | System Error | Pre-Op Failure | System fault | System Error | 27 |
| 0x810A | PM Memory Error | SCF File Read Failure | System fault | PM Memory Error | 2 |
| 0x810B | PM Memory Error | DCF File Read Failure | System fault | PM Memory Error | 2 |
| 0x810C | System Error | Failed to Init DCF Tables by Pre-Op End | System fault | System Error | 27 |
| 0x810D | System Error | Config Failure - No Repository Node | System fault | System Error | 27 |
| 0x810E | System Error | Config Failure - Too Many Repository Nodes | System fault | System Error | 27 |
| 0x8110 | SCID Received by Waking Node | | Control fault | | — |
| 0x8140 | Memory Error | Tx Confirm Timeout | System fault | Memory Error | 1 |
| 0x8141 | System Error | Config Failure - No PG Input Device | System fault | System Error | TBD |
| 0x8142 | System Error | Config Failure - Invalid PG Input Devices Param | System fault | System Error | 27 |
| 0x8143 | System Error | Config Failure - Unexpected Non PG Input Device | System fault | System Error | 27 |
| 0x8180 | Bad Settings | Unable to Select Profile | System fault | Bad Settings | 15 |
| 0x8181 | Memory Error | Invalid AIM Indicated | System fault | Memory Error | 1 |
| 0x8182 | Memory Error | Invalid Mode or Profile Message | System fault | Memory Error | 1 |
| 0x8183 | Bad Settings | No Modes Available | System fault | Bad Settings | 15 |
| 0x8184 | Focus Mask Access Error | | Control fault | | TBD |

### Lighting Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x8800 | Overtemperature (Lamps) | Lighting Driver Over Temperature | System fault | Overtemp. (Lamps) | 25 |
| 0x8811 | Left Lamp Short Circuit | | System fault | Left Lamp Short | 25 |
| 0x8812 | Right Lamp Short Circuit | | System fault | Right Lamp Short | 25 |
| 0x8819 | Brake Lamp Short Circuit | | System fault | Brake Lamp Short | 25 |
| 0x881D | Left Indicators Short Circuit | | System fault | L Ind Lamp Short | 25 |
| 0x881E | Right Indicators Short Circuit | | System fault | R Ind Lamp Short | 25 |
| 0x882C | Indicators Open Circuit | | System fault | Ind Lamp Failed | 2 |
| 0x883C | Indicators Open Circuit | Indicators Single Bulb Failure | System fault | Ind Lamp Failed | 25 |

### State Machine / Queue Errors

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0x8E00 | Statemachine Queue Overflow | | Control fault | | TBD |
| 0x8E01 | Event Queue Overflow | | Control fault | | TBD |

### Module Error

| Error ID | Error Name | Extended Description | Fault Type | Display Text | Remedy |
|----------|-----------|---------------------|------------|-------------|--------|
| 0xFFFF | Module Error | Module reporting Error may need repair | System fault | Module Error | 1, 29 |

---

## Non-PGDT Device Error Codes

Source: "R-net Error Codes for non-PGDT Devices" (Rev 3, 2016-10-10)

These devices use a common error code suffix pattern (x01-x0A) with device-specific prefixes. Organisation ID indicates the manufacturer.

### Kernel Errors (All Devices)

Common kernel errors shared across non-PGDT modules:

| Error ID | Name | Description | Fault Type | Display | Org |
|----------|------|-------------|------------|---------|-----|
| 0x0001 | KERNEL WATCHDOG TIME OUT | Kernel task stopped responding | System Fault | Module Error | Permobil/HMC |
| 0x0002 | KERNEL APP. TOO SLOW | Application function took too long | System Fault | Module Error | Permobil/HMC |
| 0x0003 | KERNEL BUFFER OVERFLOW | ERB full when trying to add | System Fault | Module Error | Permobil/HMC |
| 0x0004 | KERNEL BUFFER UNDERFLOW | ERB empty when trying to read | System Fault | Module Error | Permobil/HMC |
| 0x0005 | KERNEL MQ OVERFLOW | TMQ full when trying to add | System Fault | Module Error | Permobil/HMC |
| 0x0006 | KERNEL MQ UNDERFLOW | TMQ empty when trying to read | System Fault | Module Error | Permobil/HMC |
| 0x0007 | KERNEL HW MONITOR FAIL | Hardware monitor test failed | System Fault | Module Error | Permobil/HMC |
| 0x0008 | KERNEL UNEXPECTED SCID | Received scid while SCID_ENABLED | System Fault | Module Error | Permobil/HMC |
| 0x0009 | KERNEL PROFILEMODE FAIL | Failed profile/mode transaction | System Fault | Module Error | Permobil/HMC |
| 0x000A | KERNEL DIME FAILED | DIME Error | System Fault | DIME Error | Permobil/HMC |
| 0x000B | KERNEL HW ISOLATE FAIL | Hardware monitor signals isolated | System Fault | Module Error | Permobil/HMC |
| 0x000C | KERNEL WRONG WAKE SOURCE | WAKEUP message with different DIME-ID | System Fault | Module Error | Permobil/HMC |
| 0x000D | KERNEL STAGE MANAGEMENT | Bad sync in stage management | System Fault | Module Error | Permobil/HMC |
| 0x000E | KERNEL NODE IS BUS OFF | CAN controller is bus off | System Fault | Module Error | Permobil/HMC |
| 0x000F | KERNEL PROG OBJECT FAIL | Programming object error | System Fault | Module Error | Permobil/HMC |
| 0x0010 | KERNEL NODE IS DISARMED | Signal 'Armed' transitioned to low | System Fault | Module Error | Permobil/HMC |
| 0x0011 | KERNEL UNKNOWN CAN INT | Unknown CAN interrupt | System Fault | Module Error | Permobil/HMC |
| 0x0012 | KERNEL SERIAL OVERFLOW | Serial port transmit buffers full | System Fault | Module Error | Permobil/HMC |
| 0x0013 | KERNEL REP. FILE FORMAT | Unknown or invalid file format | System Fault | PM Memory Error | Permobil/HMC |
| 0x0014 | KERNEL REP. FILE MISSING | Required file not present | System Fault | PM Memory Error | Permobil/HMC |
| 0x0015 | KERNEL REP. SUPPORT FAIL | Repository support fault | System Fault | PM Memory Error | Permobil/HMC |

### Compact Joystick (CJ) -- HMC International (0x11XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1101 | CJ MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1102 | CJ JOYSTICK REFERENCE VOLTAGE | Reference voltage (VCC/2) out of range | Control Fault | Module Error |
| 0x1103 | CJ JOYSTICK CENTER | Joystick out of center | System Fault | Center Joystick |
| 0x1104 | CJ JOYSTICK OUTPUT | Joystick signal Out of Range | Control Fault | Module Error |
| 0x1105 | CJ TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1106 | CJ EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1107 | CJ OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1108 | CJ TIMING | ADC not synchronised | Control Fault | Module Error |
| 0x1109 | CJ CODE | Non existing code entered | Control Fault | Module Error |
| 0x110A | CJ KERNEL | Kernel error | Control Fault | Module Error |

### ESP -- Permobil Design AB (0x12XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1201 | ESP PM LATCHED MODE | Power module entered Latched Drive Mode | System Fault | Bad Settings |
| 0x1202 | ESP REFERENCE VOLTAGE | Reference voltage (VCC/2) out of range | Control Fault | Module Error |
| 0x1203 | ESP OFFSET VOLTAGE | PWM Offset regulation out of range | Control Fault | Module Error |
| 0x1204 | ESP SENSOR OUTPUT | Gyro Sensor Out of Range | Control Fault | Module Error |
| 0x1205 | ESP TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1206 | ESP EEPROM | Calibrate EEPROM section corrupted | System Fault | Recalibrate |
| 0x1207 | ESP OBJ READ | Can not read Programming object in time | System Fault | Cycle Power |
| 0x1208 | ESP TIMING | ADC not synchronised | System Fault | Cycle Power |
| 0x1209 | ESP CODE | Non existing code entered | System Fault | Module Error |
| 0x120A | ESP KERNEL | Kernel error | System Fault | Module Error |

### Compact Joystick Advanced (CJA) -- HMC International (0x14XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1401 | CJA MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1402 | CJA JOYSTICK REFERENCE VOLTAGE | Reference voltage (VCC/2) out of range | Control Fault | Module Error |
| 0x1403 | CJA JOYSTICK CENTER | Joystick out of center | System Fault | Center Joystick |
| 0x1404 | CJA JOYSTICK OUTPUT | Joystick signal Out of Range | Control Fault | Module Error |
| 0x1405 | CJA TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1406 | CJA EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1407 | CJA OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1408 | CJA TIMING | ADC not synchronised | Control Fault | Module Error |
| 0x1409 | CJA CODE | Non existing code entered | Control Fault | Module Error |
| 0x140A | CJA KERNEL | Kernel error | Control Fault | Module Error |

### MagicDrive and MagicDriveTouch -- Permobil Design AB (0x15XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1501 | MD MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1502 | MD COM_OFFLINE | Communication Offline | Control Fault | Module Error |
| 0x1503 | MD COM_DATA | Communication Bad data | Control Fault | Module Error |
| 0x1504 | MD COM VERSION | Communication Incorrect version | Control Fault | Module Error |
| 0x1505 | MD TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1506 | MD EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1507 | MD OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1508 | MD COM_TIMEOUT | Communication timeout | Control Fault | Module Error |
| 0x1509 | MD CODE | Non existing code entered | Control Fault | Module Error |
| 0x150A | MD KERNEL | Kernel error | Control Fault | Module Error |

Note: MagicDrive and MagicDriveTouch share the same error codes.

### Co-pilot -- Permobil Design AB (0x16XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1601 | COP MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1602 | COP JOYSTICK REFERENCE VOLTAGE | Reference voltage (VCC/2) out of range | Control Fault | Module Error |
| 0x1603 | COP JOYSTICK CENTER | Joystick out of center | System Fault | Center Joystick |
| 0x1604 | COP JOYSTICK OUTPUT | Joystick signal Out of Range | Control Fault | Module Error |
| 0x1605 | COP TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1606 | COP EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1607 | COP OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1608 | COP TIMING | ADC not synchronised | Control Fault | Module Error |
| 0x1609 | COP CODE | Non existing code entered | Control Fault | Module Error |
| 0x160A | COP KERNEL | Kernel error | Control Fault | Module Error |

### Co-pilot2 -- Permobil Design AB (0x16XX range)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1680 | COP2 INT VOLTAGE ERROR | Internal voltages out of range | Control Fault | Module Error |
| 0x1681 | COP2 LATCHED ENABLED | Latched drive enabled in configuration | System Fault | Latched drive on |
| 0x1682 | COP2 HIGH FORCE | High force detected | System Fault | Too high force |
| 0x1683 | COP2 LOADCELL ERROR | Load cell signal out of range | Control Fault | Module Error |
| 0x1684 | COP2 DMS TEST ERROR | DMS is activated during test | Control Fault | Safety handle on |
| 0x1685 | COP2 ACCEL ERROR | Accelerometer values out of range | Control Fault | Module Error |
| 0x1686 | COP2 ANGLE ERROR | Incorrect handle angle | System Fault | Bad angle |
| 0x1687 | COP2 SYST FAULT1 | Control fault 1 | Control Fault | Module Error |
| 0x1688 | COP2 SYST FAULT2 | Control fault 2 | Control Fault | Module Error |
| 0x1689 | COP2 SYST FAULT3 | Control fault 3 | Control Fault | Module Error |

### Easy Rider (ER) -- HMC International (0x17XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1701 | ER MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1702 | ER COM_OFFLINE | Communication Offline | Control Fault | Module Error |
| 0x1703 | ER COM_DATA | Communication Bad data | Control Fault | Module Error |
| 0x1704 | ER COM VERSION | Communication Incorrect version | Control Fault | Module Error |
| 0x1705 | ER TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1706 | ER EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1707 | ER OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1708 | ER COM_TIMEOUT | Communication timeout | Control Fault | Module Error |
| 0x1709 | ER CODE | Non existing code entered | Control Fault | Module Error |
| 0x170A | ER KERNEL | Kernel error | Control Fault | Module Error |

### Remote Button Interface (RBI) -- HMC International (0x18XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1801 | RBI MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1802 | RBI 12V WRONG OUTPUT | 12Volt Regulator defect | Control Fault | Module Error |
| 0x1803 | RBI 12V ON/OFF PROBLEM | 12Volt on/off switch circuit problem | Control Fault | Module Error |
| 0x1805 | RBI TEST FAILED | Module test flag not set in EEPROM | Control Fault | Module Error |
| 0x1806 | RBI EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1807 | RBI OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1809 | RBI CODE | Non existing code entered | Control Fault | Module Error |
| 0x180A | RBI KERNEL | Kernel error | Control Fault | Module Error |

### Mini-Joystick (MJ) -- HMC International (0x19XX)

| Error ID | Name | Description | Fault Type | Display |
|----------|------|-------------|------------|---------|
| 0x1901 | MJ MODULE ERROR | Unrecoverable error (watchdog timeout) | Control Fault | Module Error |
| 0x1902 | MJ JOYSTICK REFERENCE VOLTAGE | Reference voltage (VCC/2) out of range | Control Fault | Module Error |
| 0x1903 | MJ JOYSTICK CENTER | Joystick out of center | System Fault | Center Joystick |
| 0x1904 | MJ JOYSTICK OUTPUT | Joystick signal Out of Range | Control Fault | Module Error |
| 0x1905 | MJ TEST FAILED | Module Tested Flag not set in EEPROM | Control Fault | Module Error |
| 0x1906 | MJ EEPROM | Calibrate EEPROM section corrupted | Control Fault | Module Error |
| 0x1907 | MJ OBJ READ | Can not read Programming object in time | Control Fault | Module Error |
| 0x1908 | MJ TIMING | ADC not synchronised | Control Fault | Module Error |
| 0x1909 | MJ CODE | Non existing code entered | Control Fault | Module Error |
| 0x190A | MJ KERNEL | Kernel error | Control Fault | Module Error |
| 0x1911 | MJ DEVICE FAILURE | Mini Joystick Failure | Control Fault | Module Error |
| 0x1912 | MJ DEVICE CONNECTION | Communication problems URIB - Mini-JS | Control Fault | Module Error |
| 0x1915 | MJ DEVICE NOT TESTED | Not Calibrated | Control Fault | Module Error |

---

## ICS Seating Error Codes

Source: "ICS 3x Active Error codes on Rnet" (v7, 2014-11-27)

ICS error codes use prefix 0x20XX. The error suffix pattern (x1-xD) repeats for each seating function. Error codes are reported via R-Net CAN bus but originate from the ICS LIN bus system.

### ICS Master Errors (0x201X)

| Error ID | Function | Description | Display | Remedy |
|----------|----------|-------------|---------|--------|
| 0x2011 | Master | Model or UI has incorrect checksum or firmware mismatch | Master Error | 1 |
| 0x2012 | Master | Over current in idle mode | Master Error | 2 |
| 0x2013 | Master | Problems with internal SPI communication | Master Error | 3 |
| 0x2014 | Master | Cannot write to internal flash | Master Error | 4 |
| 0x2015 | Master | Cannot update node parameters | Master Error | 5 |
| 0x2017 | Master | ICS needs restart, cycle wheelchair power | Master Error | 6 |
| 0x201D | Master | Unused actuator or module attached to ICS | Master Error | 7 |

### Switchbox Errors (0x202X - 0x205X)

Repeating suffix pattern for Main, Second, Third, and Fourth switchboxes:

| Suffix | Description | Remedy |
|--------|-------------|--------|
| x1 | Switches are activated at start up | 8 |
| x9 | Cannot communicate on the LIN bus | 9 |
| xA | Node is required but not present | 10 |
| xD | Flash parameters have been updated in the node | 11 |

| Range | Switchbox | Example IDs |
|-------|-----------|-------------|
| 0x2021-0x202D | Main switchbox | 0x2021, 0x2029, 0x202A, 0x202D |
| 0x2031-0x203D | Second switchbox | 0x2031, 0x2039, 0x203A, 0x203D |
| 0x2041-0x204D | Third switchbox | 0x2041, 0x2049, 0x204A, 0x204D |
| 0x2051-0x205D | Fourth switchbox | 0x2051, 0x2059, 0x205A, 0x205D |

### Seating Function Errors (0x207X - 0x217D)

Each seating function uses the same suffix pattern:

| Suffix | Description | Remedy |
|--------|-------------|--------|
| x1 | Sensor/cable between sensor and General Module or GM not working | 12 |
| x2 | No motor can be detected, check motor and cable | 13 |
| x3 | Over current when operating function, might be overload | 14 |
| x4 | Pinch protection activated | 15 |
| x5 | Actuator is not moving or moving too slow | 16 |
| x6 | Too high speed detected on actuator, check sensor | 17 |
| x7 | Drive electronics for the actuator overheated | 22 |
| x8 | Fault mode has triggered | 18 |
| x9 | Cannot communicate on the LIN bus | 19 |
| xA | Node is required but not present | 20 |
| xD | Flash parameters have been updated in the node | 21 |

| Range | Function | Display Text |
|-------|----------|-------------|
| 0x2071-0x207D | Left Leg | Legs Error |
| 0x2081-0x208D | Right Leg | Legs Error |
| 0x2091-0x209D | Legs | Legs Error |
| 0x20A1-0x20AD | Tilt | Tilt Error |
| 0x20B1-0x20BD | Back | Back Error |
| 0x20C1-0x20CD | Seat lift | Seat Lift Error |
| 0x20D1-0x20DD | Stand | Seat Stand Error |
| 0x20F1-0x20FD | Alt switchbox | Alt Switchbox Error |
| 0x2101-0x210D | Option1 | Extra Function Error |
| 0x2111-0x211D | Option2 | Extra Function Error |
| 0x2121-0x212D | Option3 | Extra Function Error |
| 0x2131-0x213D | Option4 | Extra Function Error |
| 0x2141-0x214D | Option5 | Extra Function Error |
| 0x2151-0x215D | Option6 | Extra Function Error |
| 0x2161-0x216D | Articulation legs | Articul. Legs Error |
| 0x2171-0x217D | Support Wheels | Support Wheels Error |

---

## PGDT Remedies

The remedy numbers in the PGDT error code tables refer to these suggested actions:

| # | Suggested Actions |
|---|-------------------|
| 1 | Memory error from any R-Net module. Check cables/connections. Cycle power. If trip persists with non-PGDT modules (ESP, ICS, etc.), disconnect them and reconnect one at a time to isolate. |
| 2 | PM-specific memory error. Check cables. Re-write program file using R-Net PC Programmer with the correct file for the wheelchair model. |
| 3 | Check battery condition/charge. Ensure battery-to-PM and motor-to-PM connections are tight and undamaged. Cycle power via Circuit Breaker or Main Fuse. |
| 4 | Joystick was not centered at power-on. Ensure joystick is centered and power up again. If displaced screen shows for 5 seconds without release, error is registered. |
| 5 | OMNI SID (Specialty Input Device) disconnected. Check cables between OMNI and SID. Verify *9-Way Detect* parameter matches the SID type (e.g., set to *Off* if SID has no detect-link). |
| 6 | System inactive longer than *Sleep Timer* parameter. Entry is logged each time. |
| 7 | M1 solenoid brake problem. Follow cabling to verify correct brake on M1 port. Check brake, cables, and connections. |
| 8 | M2 solenoid brake problem. Follow cabling to verify correct brake on M2 port. Check brake, cables, and connections. |
| 9 | Battery voltage above 35V. Check charge level/condition. Ensure battery connections are tight and undamaged. Check circuit breaker/main fuse connection. |
| 10 | Low battery voltage or worn/defective battery. Check charge level/condition. Ensure connections are tight. |
| 11 | Charger connected to JSM/OMNI or chassis-mounted connector. Battery charging screen displays. Disconnect charger. If trip persists, Joystick Module may be defective. |
| 12 | User Switch disconnected from U1 or U2 port. Check cables/connectors. If trip persists, try replacing switch. To use OMNI without User Switch, set *Switch Detect* to *Off*. |
| 13 | Inhibit inputs are active AND latched. Last 2 hex digits indicate which inhibit (e.g., 1E20=Inhibit 2, 1E21=Inhibit 3). Cycle power to clear latch. Check wiring/switches on indicated inhibits. |
| 14 | Battery voltage below 16V. Check charge level/condition. Ensure connections are tight. |
| 15 | Incorrect or invalid program settings. Read and check current parameters. Re-program using R-Net PC Programmer. If persistent, use *Return to Defaults* and re-program in small groups, cycling power after each. |
| 16 | System or program settings changed, requiring power cycle. Not a trip condition -- just an indication that Cycle Power function was activated. Cycle power via JSM or other input device. |
| 17 | M1 motor disconnected. Follow cabling to verify correct motor. Check cables/connections. Test motor with voltmeter/external power. |
| 18 | M2 motor disconnected. Follow cabling to verify correct motor. Check cables/connections. Test motor with voltmeter/external power. |
| 19 | M1 motor shorted to battery positive. Follow cabling. Check cables/connections. Check for voltage between M1 connections and positive battery terminal when motors are not driving. Test motor with voltmeter/external power. |
| 20 | M1 motor shorted to battery negative. Follow cabling. Check cables/connections. Check for voltage between M1 connections and negative battery terminal when motors are not driving. Test motor with voltmeter/external power. |
| 21 | M2 motor shorted to battery positive. Follow cabling. Check cables/connections. Check for voltage between M2 connections and positive battery terminal when motors are not driving. Test motor with voltmeter/external power. |
| 22 | M2 motor shorted to battery negative. Follow cabling. Check cables/connections. Check for voltage between M2 connections and negative battery terminal when motors are not driving. Test motor with voltmeter/external power. |
| 23 | Latched Drive Timeout period exceeded. Not a trip condition. Adjust the *Latched Timeout* parameter if needed. |
| 24 | Controller reached Temperature Threshold. Goes to standby to cool down. Logged each time. |
| 25 | Problem with PGDT Seating Module (SM) or Intelligent Seating Module (ISM). Permobil does not use these modules -- this error should not appear on Permobil products. |
| 26 | CAN bus wiring fault. Confirm all cables are securely connected (no yellow showing). Check cable continuity with ohmmeter. Replace damaged cables. Disconnect one cable at a time, cycling power after each, to isolate the faulty cable/module. |
| 27 | System error not attributable to a specific module. Check cables/connections. Cycle power. If non-PGDT modules present, disconnect and reconnect one at a time to isolate. |
| 28 | DIME identification conflict between modules. If new module added: disconnect, cycle power, reconnect, cycle power. If no additions: disconnect modules one at a time, cycling power, reconnecting in reverse order to identify conflict. |
| 29 | Unknown module error. Access System Fault Log via OBP or R-Net PC Programmer. Find the module with *FFFF* in its error log. That module needs investigation/replacement. |

---

## ICS Remedies

| # | Suggested Actions |
|---|-------------------|
| 1 | ICS master not correctly updated or memory/checksum error. Try reprogramming. If persistent, replace ICS Master Module. |
| 2 | LIN-bus current unexpectedly high when no movement ordered. Output transistor in actuator node (GM or Smart actuator) may be stuck. Cycle power; if actuator moves briefly before error, the faulty unit is trying to hard stop. |
| 3 | Internal SPI communication failure between URIB and Master Main-PCB. Update Master Firmware and/or URIB-software. If persistent, replace Master Module. |
| 4 | CPU cannot write to internal flash memory. If persistent, replace Master Module. |
| 5 | Cannot update node parameters. Read data doesn't match written data. Replace the node. If that doesn't help, replace ICS Master Module. |
| 6 | Restart system by cycling power (R-Net ON/OFF button). |
| 7 | Smart actuator or General Module with no defined function connected. May occur with special adaptation reprogrammed using standard config. Use factory backup file or contact Permobil. |
| 8 | Switch activated during startup. System will ignore the button until released. Not reported on display or in log. |
| 9 | Switchbox detected on LIN-bus but messages have wrong checksum. Replace the Switchbox. |
| 10 | Not implemented. This error code will never occur. |
| 11 | Restart is required. Switch OFF/ON system. |
| 12 | Check cables and connectors between General Module and sensor. |
| 13 | Check cables and connector between motor and General Module or Smart Actuator Electronics. |
| 14 | Overcurrent detected. Could be from actuator hitting hard end stop, overload from user weight, or obstruction. Find where overcurrent occurs. Check that actuator doesn't move into hard stop. Check that seat function moves as expected without user. Replace actuator if no other reason found. |
| 15 | Pinch Protection switch activated. Check if switch is activated. Check cable between switch and General Module. Check switch function with meter. Replace switch or General Module. |
| 16 | Movement of actuator is monitored. Node detects no/slow position feedback changes. For external feedback (SoftPot): check wiring. Check that actuator position in WB matches physical position. Change feedback sensor/Smart Actuator if no other reason. |
| 17 | Node detects too-fast position feedback changes. For external feedback (SoftPot): check wiring. Check actuator position in WB matches physical. Change feedback sensor/Smart Actuator if no other reason. |
| 18 | Node has internal fault (e.g., faulty voltage level). Replace node. When actuator with REAC DigPot is used, check for short-circuit on DigPot output (motor connections). |
| 19 | Node on LIN-bus has wrong checksum. Replace General Module or Smart Actuator. |
| 20 | Master can't detect the node. Check connections to General Module or Smart Actuator. Replace if connections are OK. |
| 21 | Restart is required. Switch OFF/ON system. |
| 22 | Smart Actuator or General Module detected too high PCB temperature. Probably caused by heavy load during extended use. Wait for unit to cool down. |

---

## Fault Types

| Fault Type | Description |
|-----------|-------------|
| **System fault** | Displayed on JSM/OMNI/cJSM screen. Error persists until power cycled or condition clears. |
| **Control fault** | Internal error logged but may not display on screen. Usually requires technician access to read via programmer. |

---

## Error Code Patterns

### Non-PGDT Device Suffix Pattern

Most non-PGDT devices follow a common x01-x0A suffix pattern:

| Suffix | Typical Meaning |
|--------|----------------|
| x01 | Module error (watchdog timeout) |
| x02 | Reference voltage / communication offline |
| x03 | Joystick center / communication bad data |
| x04 | Joystick output / communication version |
| x05 | Test failed (EEPROM flag) |
| x06 | EEPROM corruption |
| x07 | Object read timeout |
| x08 | Timing / ADC sync / communication timeout |
| x09 | Non-existing code entered |
| x0A | Kernel error |

### ICS Seating Suffix Pattern

All ICS seating functions use a consistent suffix:

| Suffix | Meaning |
|--------|---------|
| x1 | Sensor/cable/GM not working |
| x2 | Motor not detected |
| x3 | Overcurrent |
| x4 | Pinch protection |
| x5 | Not moving / too slow |
| x6 | Too high speed |
| x7 | Electronics overheated |
| x8 | Fault mode triggered |
| x9 | LIN bus communication failure |
| xA | Node required but missing |
| xD | Flash parameters updated |

---

## CAN Bus Error Reporting

Error codes are transmitted on the R-Net CAN bus as part of the device status frames. The PM aggregates errors from all connected modules and can display them on the JSM/OMNI/cJSM screen.

Error codes can be read through:
- **On-screen display** (System faults only) -- shows abbreviated text on JSM/OMNI/cJSM
- **R-Net PC Programmer** -- full error log with timestamps
- **On-Board Programming (OBP)** -- system fault log access
- **CAN bus monitoring** -- error frames visible in captures

---

*Source: Official Permobil/PGDT documentation. Compiled for accessibility research.*
*Authors: Stephen Chavez & Specter*
