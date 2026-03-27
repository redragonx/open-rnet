# Seat Safety Restrictions for Permobil Wheelchairs with R-Net and ICS

## Overview

This document summarizes the restrictions for seat movements and wheelchair speed restrictions related to seat positions. These restrictions fulfill requirements for dynamic and static stability per applicable standards.

Restrictions depend on:
- **Seat position** (tilt angle, back angle, seat lift height, leg angle)
- **User weight** (configured weight range)
- **Wheelchair model** (SeatType + ChassisType combination)

All restrictions described are standard settings. More restrictive settings may be applied for specific users.

Source: Permobil Doc S1832, Rev 15, 2020-09-07

## Restriction Levels

Three drive restriction levels can be applied by the ICS system:

| Level | Effect |
|-------|--------|
| **Low Speed** | Drive speed reduced (typically ~50%) |
| **Extra Low Speed** | Drive speed severely reduced |
| **Drive Inhibit** | Driving completely disabled |

## ICS Switchbox LED Indications

The switchbox LEDs indicate restriction status:

| LED State | Meaning |
|-----------|---------|
| **Dark** | Function inhibited (movement blocked in that direction) |
| **Solid Yellow** | Speed restriction active for this function's position |
| **Solid Red** | Drive inhibit active due to this function's position |

Note: Dark is also indicated when the function is missing from the configuration.

## Seat Angle Definitions

Depending on seat type, different angle measurements are used:

- **Back angle** — Backrest angle to horizontal (typically 85°-180°)
- **Legs angle** — Legrest angle to horizontal or to seat (varies by model)
- **Tilt angle** — Seat tilt from level (0°-50°; negative values = anterior/forward tilt)
- **Stand angle** — Standing position angle (0°-90°, VS seats only)

## Model-Specific Restrictions

### C300 Corpus II (SeatType=3, ChassisType=1)

**Angle ranges:** Back 90°-180°, Legs 80°-190°, Tilt 0°-45°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest position OR Back angle >= 150° |
| Extra Low Speed | Back angle >= 170° |

**Seat Movement Restrictions:**
| Function | Stopped When |
|----------|-------------|
| Seat lift upwards | Tilt > 15° |
| Tilt increase | Back angle >= 170° |
| Recline increase | Back angle >= 170° |

### C300 Corpus 3G (SeatType=8, ChassisType=1)

**Angle ranges:** Back 80°-180°, Legs 80°-240°, Legs-to-seat 80°-180°, Tilt 0°-50°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Back angle >= 150° OR Tilt > 20° and < 30° |
| Extra Low Speed | Back angle >= 140° OR Legs angle < Legs_Angle_Limit OR Tilt > 30° OR (Tilt > 20° AND Back angle > 120°) |

**Seat Movement Restrictions:**
| Function | Stopped When |
|----------|-------------|
| Seat lift upwards | Tilt > 15° |
| Tilt increase | Back angle >= 140° OR seat lift not in lowest position (OR Tilt > 30° only when 30° tilt selected) |
| Recline increase | Back angle >= 140° |

**LegOffset Table (seat-depth dependent):**

| Seat depth | Offset |
|------------|--------|
| 14-18" | 17° |
| 20" | 12° |
| 22" | 7° |

### C350 Corpus II (SeatType=3, ChassisType=2)

**Angle ranges:** Back 90°-150°, Legs 100°-190°, Tilt 0°-45°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Back angle >= 120° OR (Tilt > 20° and < 30°) |
| Extra Low Speed | Back angle >= 140° OR Legs angle < 100° + LegOffset OR Tilt > 30° OR (Tilt > 20° AND Back angle > 120°) |
| Drive Inhibit | Back angle > 155° (not allowed in current release) |

**EU vs US differences:** C350 has separate EU and US (7° incline) restriction tables for seat movement conditions.

### C350 Corpus 3G (SeatType=8, ChassisType=2)

**Angle ranges:** Back 80°-180°, Legs 80°-240°, Legs-to-seat 80°-180°, Tilt 0°-50°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Back angle >= 120° OR Tilt > 20° and < 30° |
| Extra Low Speed | Back angle >= 140° OR Legs angle < Legs_Angle_Limit OR Tilt > 30° OR Lift not in lowest and user weight > 120kg |
| Drive Inhibit | Back angle > 155° (not allowed in current release) |

**LegLimits Table (seat-depth dependent):**

| Seat depth | Seat mount | Min Legs angle | Legs_Angle_Limit (speed reduction) |
|------------|-----------|----------------|-----------------------------------|
| 370 mm | 0 | 91° | 115° |
| 420 mm | 25 | 88° | 113° |
| 470 mm | 50 | 83° | 109° |
| 520 mm | 75 | 83° | 105° |
| 570 mm | 100 | 83° | 102° |

### C400/C500 Corpus II (SeatType=3, ChassisType=3/4)

**Angle ranges:** Back 90°-180°, Legs 100°-240°, Legs-to-seat 90°-190°, Tilt 0°-45°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Back angle >= 150° |
| Drive Inhibit | User weight > 120kg AND Lift not in lowest pos |

**Weight-dependent movement restrictions (3 tiers):**

**User weight < 100kg (<220lbs):**
| Function | Seat lift in lowest pos | Seat lift NOT in lowest pos |
|----------|------------------------|---------------------------|
| Seat lift upwards | - | - |
| Tilt increase | Back angle >= 180° | Back angle >= 180° |
| Recline increase | Back angle >= 180° | Back angle >= 180° |

**User weight 100-120kg (220-265lbs):**
| Function | Seat lift in lowest pos | Seat lift NOT in lowest pos |
|----------|------------------------|---------------------------|
| Seat lift upwards | Back angle >= 135° or Tilt >= 30° | Back angle >= 135° or Tilt >= 30° |
| Tilt increase | Back angle >= 180° | Back angle >= 135° or Tilt >= 30° |
| Recline increase | Back angle >= 180° | Back angle >= 135° |

**User weight > 120kg (>265lbs):**
| Function | Seat lift in lowest pos | Seat lift NOT in lowest pos |
|----------|------------------------|---------------------------|
| Seat lift upwards | Back angle >= 120° or Tilt > 5° or Driving | Back angle >= 120° or Tilt > 5° or Driving |
| Tilt increase | Tilt >= 30° or Back angle >= 150° | Back angle > 120° or Tilt > 5° |
| Recline increase | Back angle >= 150° | Back angle > 120° or Tilt > 5° |

Note: Tilt may continue to be increased if "pushed backrest" is selected.

### C400/C500 Corpus 3G (SeatType=8, ChassisType=3/4)

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Back angle >= 150° |
| Extra Low Speed | Lift not in lowest pos AND User weight > 120kg |

**Movement Restrictions:**
| Function | Stopped When |
|----------|-------------|
| Tilt increase | Back angle >= 180° |
| Recline increase | Back angle >= 180° |

### C400/C500 Corpus 3G Lowrider (SeatType=10, ChassisType=3/4)

**Angle ranges:** Back 85°-168°, Legs 85°-240°, Legs-to-seat 85°-190°, Tilt 0°-30°

Same restriction pattern as Corpus 3G but with lower angle limits (168° instead of 180°).

### C400/C500 VS and VS-Jr (SeatType=2, ChassisType=3/4)

**Angle ranges:** Back 90°-180°, Legs 100°-240°, Legs-to-seat 90°-190°, Tilt 0°-45°, Stand 0°-90°

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift raised 55-250mm OR Back angle > 150° |
| Extra Low Speed | Standing AND stand+drive installed |
| Drive Inhibit | Standing AND stand+drive NOT installed OR Stand angle > 5° from final stand angle |

**VS-specific ICS switchbox indications:**
| Function | Dark | Solid Yellow | Solid Red |
|----------|------|-------------|-----------|
| Seat Lift | When standing | Seat lift raised > 55 | - |
| Tilt | When standing | - | - |
| Back Recline | When standing | Back angle > 150° | - |
| Legs | When standing | - | - |
| Stand | - | Driving in standing (enabled) | Driving in standing (not enabled) |

### K300/C400 PS-Jr (SeatType=4, ChassisType=1/3)

Simple restriction model:
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Tilt angle > 20° |

### C300/C350 PS (SeatType=5, ChassisType=1/2)

Simple restriction model:
| Level | Condition |
|-------|-----------|
| Low Speed | Seat lift not in lowest pos OR Tilt angle > 20° |

Movement restriction: Seat lift upwards stopped / Tilt increase when tilt angle > 15° OR Seat lift is not in lowest pos.

### F3 Corpus APE (SeatType=12, ChassisType=14)

**Angle ranges:** Back 85°-180°, Legs 90°-240°, Legs-to-seat 85°-190°, Tilt -45° to 50° (anterior tilt when tilt < 0°)

**Speed Restrictions:**
| Level | Condition |
|-------|-----------|
| Low Speed | Seat elevated 50-150mm OR Back angle >= 150° or < 90° OR Tilt angle -6° to -10° OR Legrest angle > 150° (to horizontal) |
| Extra Low Speed | Seat elevated > 150mm OR Tilt angle -10° to -20° (multiple additional conditions with legrest and seat elevation) |
| Drive Inhibit | Tilt angle -21° to -45° OR Power transfer footplates hit ground (multiple additional conditions) |

**Movement Restrictions:**
| Function | Stopped When |
|----------|-------------|
| Seat lift upwards | Back angle > 130° AND rear of seat raised < 120mm AND user weight > 100kg |
| Tilt backwards | Back angle >= 180° |
| Tilt forward | Back angle > 130° AND rear < 120mm AND weight > 100kg OR Back angle <= 85° (unless Tone/Reach/Transfer option) |
| Recline increase | Back angle >= 180° OR Back angle <= 85° |
| Legrest | Total legrest angle <= 93° when anterior tilt > -10° OR Total legrest angle <= 98° when anterior tilt < -10° |

### F5 Corpus APE (SeatType=12, ChassisType=13)

Similar to F3 Corpus APE but with ChassisType=13 specific limits.

### F5 Corpus VS (SeatType=13, ChassisType=13)

Combines APE anterior tilt capability with VS standing functionality.

**Unique features:**
- Tilt angle can go negative (anterior tilt)
- Stand + drive can be enabled/disabled
- Support wheels deployment affects restrictions

### K450 MX (Unique — "Terra" rotation function)

The K450 MX has a unique "Terra" rotation function not found on other models. It has its own specific restriction set.

### M3/M5 Corpus APE, M3 II/M5 II Corpus APE

Later generation models with updated restriction tables. Follow similar patterns to F3/F5 but with chassis-specific limits.

### M300/M400 Corpus 3G (ChassisType=8)

Uses the standard Corpus 3G restriction pattern with M300/M400 chassis-specific adjustments.

### Street Corpus II

Simplified restriction set for the Street chassis platform.

## "Pushed Backrest" Override

Several models support a "pushed backrest" option. When enabled, tilt may continue to increase past the normal restriction angle. This is used when the backrest is being pushed by an attendant or external force.

## Regional Differences

Some models (notably C350 Corpus) have different restriction tables for:
- **EU** — Standard stability requirements
- **US (7° incline)** — Modified for US incline testing requirements

The US tables are generally more restrictive for seat lift upwards and tilt operations.

---

*Source: Permobil "Seat Restrictions for Wheelchairs with Rnet and ICS v15" (Doc S1832)*
*52 pages covering 26+ wheelchair models*
*Compiled for accessibility research.*
*Authors: Stephen Chavez & Specter*
