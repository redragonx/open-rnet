# R-Net Configuration File Format (.R-net)

Analysis of R-Net Programmer configuration export files.

## Overview

`.R-net` files are binary configuration exports from the R-Net Programmer software. They contain complete wheelchair configuration including:

- Speed profiles and motor limits
- Input mode assignments
- Seating/actuator functions
- Device serial associations

## File Structure

| Offset | Size | Content | Description |
|--------|------|---------|-------------|
| 0x0000 | 32 | Header | Magic `03000000`, version, checksum |
| 0x0020 | 224 | Padding | XOR pattern `9d82c7a3f28db441` repeated |
| 0x0100 | 96 | Metadata | Configuration metadata, timestamps |
| 0x0160 | 240 | Mode Profiles | Input mode assignments |
| 0x0250 | 944 | Speed Profiles | Named speed profiles (5-8 per chair) |
| 0x0600 | 1536 | Motor Params | Current limits, acceleration curves |
| 0x0C00 | 1024 | Seating | Actuator/seating function config |
| 0x1000 | 2048 | Extended | Per-mode detailed settings |
| 0x1800+ | Varies | Additional | Device-specific options |

Typical file sizes: 3,795 - 7,979 bytes

## Header (0x0000-0x001F)

```
03 00 00 00 1f 1c 03 00 00 00 00 00 00 01 03 00
00 00 02 00 00 00 03 00 00 00 [checksum 4 bytes]
```

- Bytes 0-3: Magic `03000000`
- Bytes 24-27: File checksum/timestamp (varies per save)

## Mode Profiles (0x0160-0x024F)

Mode profiles define input device assignments:

```
[16-byte name, padded with spaces] + ">@<" + [control bytes]
```

### Standard Modes

| Mode | Description |
|------|-------------|
| Drive | Primary joystick control |
| Seating | Seat position controls |
| Bluetooth | BT module input |
| Bluetooth2 | Secondary BT |
| iDevice | iOS device input |
| IR Mode | Infrared input |
| Programming | R-Net Programmer mode |
| Mouse Control | Mouse emulation |
| Environmental | ECU control |

## Speed Profiles (0x0250-0x05FF)

Speed profiles define drive behavior presets:

```
[4-byte prefix] + [16-byte name] + [config bytes]
```

### Prefix Pattern

- `64 64 64 64` ('dddd') - Standard prefix
- `00 00 XX XX` - Alternate format

### Profile Names Found

| Chair | Profiles |
|-------|----------|
| V6 | SLOWEST, SLOW, MEDIUM, FAST, V6AT FAST, Profile 6/7 |
| C500/M300 | Indoor, Normal, Profile 3-6 |
| M300 Soccer | Indoor, Normal, **SOCCER**, Profile 4-6 |
| Alltrack | idiot mode, Standard, StandardPWR, DANGEROUS, PWR-Tremor |
| Quickie P6 | idiot mode, Medium, Fast, DIABLO!!! |
| M300 2022 | Indoor, Normal, High Torque, Profile 4-6 |

### Profile Configuration Bytes

Following the name, approximately 8 bytes of configuration:

| Offset | Description | Range |
|--------|-------------|-------|
| +0 | Max forward speed | 0x00-0x64 (0-100%) |
| +1 | Max reverse speed | 0x00-0x64 |
| +2 | Acceleration | 0x00-0x64 |
| +3 | Deceleration | 0x00-0x64 |
| +4-7 | Turning/other | varies |

## Motor Parameters (0x0600-0x0BFF)

Motor current and power settings per profile.

### Key Offsets

| Offset | Description | Stock | 90-amp | 120-amp |
|--------|-------------|-------|--------|---------|
| 0x0B23 | Profile 1 current limit | 55 | 100 | 100 |
| 0x0B30 | Profile 2 current limit | 55 | 100 | 100 |
| 0x0B3D | Profile 3 current limit | 55 | 100 | 100 |
| 0x0B4A | Profile 4 current limit | 55 | 100 | 100 |
| 0x0B57 | Profile 5 current limit | 55 | 100 | 100 |

Values are 0-100 representing percentage of maximum motor current.

### Stock vs Modified

| Parameter | Stock OEM | 90-amp Mod | 120-amp Mod |
|-----------|-----------|------------|-------------|
| Base current | 55% | ~90% | 100% |
| Accel limit | 50% | 80-100% | 100% |
| Speed cap | Profile-specific | Increased | Maximum |
| ESP | Enabled | Varies | Often disabled |

## Seating Functions (0x0C00-0x0FFF)

Actuator/seating function configuration:

```
[20-byte function name] + [control parameters]
```

### Function Names

- Tilt
- Seat Lift
- Recline
- Transfer Tilt
- Leg / Leg Rest
- Layback
- Elevator
- Head Rest
- Backrest

Each function has associated:
- Speed limits
- Range limits
- Safety interlocks
- Timeout values

## Serial Number Format

Serial numbers embedded in filenames:

| Format | Description | Example |
|--------|-------------|---------|
| CS + 8 digits | Chair Serial (legacy) | CS14050871 |
| CR + 8 digits | Chair Registration (new) | CR17122192 |

### Known Serials in Collection

| Serial | Chair Model | Notes |
|--------|-------------|-------|
| CS14050871 | Frontier V6 | Stock + 90-amp configs |
| CR14121385 | V6 | 120-amp test configs |
| CS13093419 | C500 Black | Multiple mod configs |
| CR15070953 | C500 | 2019 backup |
| CS13124566 | M300 2018 | SOCCER profile |
| CR17122192 | M300 2018 | 2022 backup |
| CR14060137 | Amylior Alltrack | DANGEROUS profile |
| CS13061526 | Quickie Pulse 6 | DIABLO!!! profile |
| CR16125104 | M3 Orange 2018 | OEM config |
| CS21054090 | F3 2021 | First mod |

## Modification Analysis

### 90-amp Mod (V6)

Changes from stock OEM:
- Motor current limits: 55% → 100%
- ~70 byte-level differences
- Maintains safety margins

### 120-amp Mod

More aggressive changes:
- All current limits maxed
- ESP (Electronic Stability) often disabled
- Acceleration curves flattened

### no-ESP Mod

Disables:
- Electronic Stability Program
- Anti-tip protection
- Some speed limiting

## XOR Padding Pattern

The repeated pattern `9d82c7a3f28db441` (8 bytes) fills unused space. This may be:
- Default uninitialized value
- Obfuscation pattern
- Checksum seed

Count: ~20 occurrences in typical file

## Creating Custom Configs

1. Export base config from R-Net Programmer
2. Identify relevant offsets for parameters
3. Modify values (stay within safe ranges)
4. Recalculate checksum if required
5. Import back to chair

**WARNING**: Incorrect modifications can cause unsafe behavior. Always test with wheels off ground and maintain physical e-stop access.

## Tools

Use `rnet_utils.py` or custom scripts to:
- Parse config files
- Compare OEM vs modified
- Extract parameter values
- Generate modification patches

## See Also

- [RNET_PROGRAMMER_PROTOCOL.md](RNET_PROGRAMMER_PROTOCOL.md) - Live config read/write
- [RNET_PROTOCOL_SPECIFICATION.md](RNET_PROTOCOL_SPECIFICATION.md) - Full protocol spec
- [CLAUDE.md](../CLAUDE.md) - Project overview
