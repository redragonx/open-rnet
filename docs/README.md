# R-Net Documentation Index

Complete documentation for R-Net protocol research and reverse engineering.

## Core Protocol Documentation

| Document | Description |
|----------|-------------|
| [RNET_PROTOCOL_SPECIFICATION.md](RNET_PROTOCOL_SPECIFICATION.md) | **Full protocol specification** - Complete reference |
| [RNET_PROTOCOL_GUIDE.md](RNET_PROTOCOL_GUIDE.md) | Protocol overview and quick reference |
| [RNET_ERROR_CODES.md](RNET_ERROR_CODES.md) | Complete error code reference (PGDT, non-PGDT, ICS) |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Cheat sheet for common operations |

## Device-Specific Documentation

| Document | Description |
|----------|-------------|
| [POP_PROTOCOL.md](POP_PROTOCOL.md) | **POP (Parameter Object Protocol)** - Official config protocol from DLL RE |
| [RNET_DEVICE_CATALOG.md](RNET_DEVICE_CATALOG.md) | **Device catalog** - All R-Net device types and parameters |
| [RNET_PROGRAMMER_PROTOCOL.md](RNET_PROGRAMMER_PROTOCOL.md) | R-Net Programmer handshake and read/write |
| [CJSM_DISPLAY_PROTOCOL.md](CJSM_DISPLAY_PROTOCOL.md) | Color JSM display protocol |
| [ESP_PROTOCOL.md](ESP_PROTOCOL.md) | ESP gyroscope module protocol |
| [ICS_SEATING_SYSTEM.md](ICS_SEATING_SYSTEM.md) | ICS seating system (LIN bus) |
| [DEVICE_SERIALS.md](DEVICE_SERIALS.md) | Known device serial numbers |
| [SERIAL_NUMBERS.md](SERIAL_NUMBERS.md) | Serial format and authentication |

## Safety & Restrictions

| Document | Description |
|----------|-------------|
| [SAFETY_RESTRICTIONS.md](SAFETY_RESTRICTIONS.md) | Weight-dependent seat safety restrictions |

## Firmware Analysis

| Document | Description |
|----------|-------------|
| [FIRMWARE_DUMP_ANALYSIS.md](FIRMWARE_DUMP_ANALYSIS.md) | BTMouse and LEDJSM dump analysis |
| [FIRMWARE_REVERSE_ENGINEERING.md](FIRMWARE_REVERSE_ENGINEERING.md) | HCS08 code analysis |
| [LEDJSM_CONFIG_ANALYSIS.txt](LEDJSM_CONFIG_ANALYSIS.txt) | Detailed config structure |

## Configuration Files

| Document | Description |
|----------|-------------|
| [RNET_CONFIG_FILE_FORMAT.md](RNET_CONFIG_FILE_FORMAT.md) | R-Net Programmer .R-net file format analysis |

## Getting Started

| Document | Description |
|----------|-------------|
| [PROGRAMMER_TOOLS_GUIDE.md](PROGRAMMER_TOOLS_GUIDE.md) | **Programmer tools guide** - How to use the self-programming tools |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Hardware setup for new users |
| [EXTRACTED_TEXT.md](EXTRACTED_TEXT.md) | Text strings from captures |

---

## Document Map

```
docs/
├── Protocol Specifications
│   ├── RNET_PROTOCOL_SPECIFICATION.md   <- FULL SPEC (start here)
│   ├── RNET_PROTOCOL_GUIDE.md           <- Overview
│   ├── RNET_ERROR_CODES.md              <- Error code reference
│   └── QUICK_REFERENCE.md               <- Cheat sheet
│
├── Device Protocols
│   ├── RNET_PROGRAMMER_PROTOCOL.md      <- Programmer mode
│   ├── CJSM_DISPLAY_PROTOCOL.md        <- Color JSM display
│   ├── ESP_PROTOCOL.md                  <- ESP gyroscope module
│   └── ICS_SEATING_SYSTEM.md            <- ICS seating (LIN bus)
│
├── Authentication
│   ├── DEVICE_SERIALS.md                <- Serial numbers
│   └── SERIAL_NUMBERS.md                <- Auth protocol
│
├── Firmware Analysis
│   ├── FIRMWARE_DUMP_ANALYSIS.md        <- Dump overview
│   ├── FIRMWARE_REVERSE_ENGINEERING.md  <- Code analysis
│   └── LEDJSM_CONFIG_ANALYSIS.txt      <- Config structure
│
├── Configuration Files
│   └── RNET_CONFIG_FILE_FORMAT.md       <- .R-net file format
│
├── Safety & Restrictions
│   └── SAFETY_RESTRICTIONS.md           <- Weight-dependent seat safety
│
└── Getting Started
    └── GETTING_STARTED.md               <- Setup guide
```

---

## Quick Links

### I want to...

- **Understand the full protocol** → [RNET_PROTOCOL_SPECIFICATION.md](RNET_PROTOCOL_SPECIFICATION.md)
- **Set up my hardware** → [Getting Started](GETTING_STARTED.md#hardware-setup)
- **Look up a frame ID** → [Frame Dictionary](../RNET_FRAME_DICTIONARY.md)
- **Look up an error code** → [Error Codes](RNET_ERROR_CODES.md)
- **Use programmer mode** → [R-Net Programmer Protocol](RNET_PROGRAMMER_PROTOCOL.md)
- **Understand authentication** → [Serial Numbers](SERIAL_NUMBERS.md)
- **Understand ESP gyroscope** → [ESP Protocol](ESP_PROTOCOL.md)
- **Understand ICS seating** → [ICS Seating System](ICS_SEATING_SYSTEM.md)
- **Check safety restrictions** → [Safety Restrictions](SAFETY_RESTRICTIONS.md)
- **Analyze firmware** → [Firmware RE](FIRMWARE_REVERSE_ENGINEERING.md)
- **Parse .R-net config files** → [Config File Format](RNET_CONFIG_FILE_FORMAT.md)

---

## Protocol Overview

```
┌─────────────────────────────────────────────────┐
│                  R-Net Protocol                  │
├─────────────────────────────────────────────────┤
│ Layer 4: Application                            │
│   Joystick, Speed, Parameters, Heartbeats       │
├─────────────────────────────────────────────────┤
│ Layer 3: Session                                │
│   Serial Authentication, Slot Assignment        │
├─────────────────────────────────────────────────┤
│ Layer 2: Addressing                             │
│   Standard Frames (11-bit), Extended (29-bit)   │
├─────────────────────────────────────────────────┤
│ Layer 1: Physical                               │
│   CAN 2.0B @ 125Kbps                           │
└─────────────────────────────────────────────────┘
```

## Key Findings

| Finding | Details |
|---------|---------|
| **MCU** | Freescale HCS08 (MC9S08DZ) |
| **XOR Tables** | Found at 0x0706 in firmware |
| **Sentinel** | 0x18A7 marks uninitialized slots |
| **No encryption** | All traffic plaintext |
| **Weak auth** | XOR-based, predictable |
| **Config format** | .R-net files are binary, reversible |
| **Motor limits** | Stock 55%, mods up to 100% |

---

## Also See

| File | Location | Description |
|------|----------|-------------|
| CLAUDE.md | `../CLAUDE.md` | Project overview |
| RNET_FRAME_DICTIONARY.md | `../` | Frame reference (590+ entries) |
| R-Net Configs/ | `../R-Net Configs/` | 25+ .R-net configuration exports |
| tools/README.md | `../tools/` | Analysis tools |
| canPPT.pdf | `../chair_control/` | DEFCON24 presentation |

---

## Safety

**Always prioritize safety when working with mobility equipment:**
- Physical emergency stop available
- Wheels off the ground during testing
- Spotter present
- Software safety limits implemented

## Authors

- Stephen Chavez
- Specter

*Research presented at DEFCON24 (August 2016)*
*Documentation updated March 2026*
