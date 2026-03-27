# R-Net Extracted Text Strings

**All text strings extracted from R-Net CAN bus captures**

## Profile/Mode Names

### cJSM (Color Joystick Module) Profiles

**Standard Drive Profiles (8 slots):**
1. Drive
2. Seating
3. L33tBT
4. Mouse Control 1
5. Mouse Control 2
6. Output Mode
7. IR Control
8. Programming

**Named Profiles (with mode prefix indicators):**
| Prefix | Profile Name |
|--------|-------------|
| dddN | Noob Mode |
| dddG | Godly Mode |
| dddP | Profile 3 |
| dddP | Profile 4 |
| dddP | Profile 5 |
| dddP | Profile 6 |
| dddP | Profile 7 |
| dddA | Attendant |

### LED JSM Profiles

**Additional Mode Indicators:**
| Prefix | Meaning |
|--------|---------|
| dddI | Indoor |
| dddO | Outdoor |
| dddS | Speed |

**Profile Names Found:**
- Drive
- Seating
- BlueTooth
- Environmental
- Output Mode
- Programming
- Attendant

## Mode Prefix Codes (Hex)

```
64646450 = dddP (Profile)
64646441 = dddA (Attendant)
64646447 = dddG (Godly)
6464644e = dddN (Noob)
64646449 = dddI (Indoor)
6464644f = dddO (Outdoor)
64646453 = dddS (Speed)
```

## R-Net Programmer Data

**Device/Model Information:**
- M300, M400 (wheelchair models)
- G basic (configuration type)
- SuperBlueTooth (BTM module name)
- USD1299 (device value/serial)

**Identifiers:**
- src_b_32 (source/build identifier)
- stephen-d, stephen@s (username fragments)
- sername@ (username field)

**Date Stamps (YYMMDD format):**
- 160127 (January 27, 2016)
- 170713 (July 13, 2017)

## 4-Byte Text Chunks

Text is transferred in 4-byte chunks via register 0x8C:

| Hex | ASCII | | Hex | ASCII |
|-----|-------|-|-----|-------|
| 44726976 | "Driv" | | 65202020 | "e   " |
| 53656174 | "Seat" | | 696e6720 | "ing " |
| 4c333374 | "L33t" | | 42542020 | "BT  " |
| 4d6f7573 | "Mous" | | 6520436f | "e Co" |
| 6e74726f | "ntro" | | 6c203120 | "l 1 " |
| 6c203220 | "l 2 " | | 4f757470 | "Outp" |
| 7574204d | "ut M" | | 6f646520 | "ode " |
| 49522043 | "IR C" | | 6f6e7472 | "ontr" |
| 6f6c2020 | "ol  " | | 50726f67 | "Prog" |
| 72616d6d | "ramm" | | 6f6f6220 | "oob " |
| 4d6f6465 | "Mode" | | 6f646c79 | "odly" |
| 204d6f64 | " Mod" | | 726f6669 | "rofi" |
| 6c652033 | "le 3" | | 6c652034 | "le 4" |
| 6c652035 | "le 5" | | 6c652036 | "le 6" |
| 6c652037 | "le 7" | | 7474656e | "tten" |
| 64616e74 | "dant" | | 426c7565 | "Blue" |
| 546f6f74 | "Toot" | | 68202020 | "h   " |
| 456e7669 | "Envi" | | 726f6e6d | "ronm" |
| 656e7461 | "enta" | | 6c202020 | "l   " |
| 496e646f | "Indo" | | 6f722020 | "or  " |
| 4f757464 | "Outd" | | 6f6f7220 | "oor " |
| 53706565 | "Spee" | | 64202020 | "d   " |

## Reconstructed Full Profile Names

From register 0x8C 4-byte chunks:

```
"Driv" + "e   " → "Drive"
"Seat" + "ing " → "Seating"
"L33t" + "BT  " → "L33tBT"
"Mous" + "e Co" + "ntro" + "l 1 " → "Mouse Control 1"
"Mous" + "e Co" + "ntro" + "l 2 " → "Mouse Control 2"
"Outp" + "ut M" + "ode " → "Output Mode"
"IR C" + "ontr" + "ol  " → "IR Control"
"Prog" + "ramm" + "ing " → "Programming"
"dddN" + "oob " + "Mode" → "Noob Mode"
"dddG" + "odly" + " Mod" + "e   " → "Godly Mode"
"dddP" + "rofi" + "le 3" → "Profile 3"
"dddA" + "tten" + "dant" → "Attendant"
"Blue" + "Toot" + "h   " → "BlueTooth"
"Envi" + "ronm" + "enta" + "l   " → "Environmental"
"Indo" + "or  " → "Indoor"
"Outd" + "oor " → "Outdoor"
"Spee" + "d   " → "Speed"
"Supe" + "rBlu" + "eToo" + "th  " → "SuperBlueTooth"
```

## Source Files

Text extracted from:
- `wireshark/aug19th_hotplug_cjsm.pcapng` - cJSM profile names
- `wireshark/cJSM+lJSM+dualcan.pcapng` - cJSM profiles
- `wireshark/ledJSM_afterconnectingtootherchair_dualcan.pcapng` - LED JSM profiles
- `wireshark/programmer_dump_file_july2017.pcapng` - Full profile dump
- `wireshark/programmer_write_file_july2017.pcapng` - Config write
- `wireshark/ics_write_config.pcapng` - R-Net Programmer data

## Extraction Command

```bash
# Extract display text from pcap
tshark -r capture.pcapng -T fields -e data 2>/dev/null | \
  grep "^208c" | cut -c9-16 | xxd -r -p

# Extract all strings from pcap data
tshark -r capture.pcapng -T fields -e data 2>/dev/null | \
  xxd -r -p | strings -n 5
```
