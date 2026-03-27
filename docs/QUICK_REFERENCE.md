# R-Net Quick Reference Card

## Physical Layer
- **Protocol:** CAN 2.0B @ 125Kbps
- **Connector:** Pin1=CAN_L, Pin2=CAN_H, Pin3=+24V, Pin4=GND

## Key Frame IDs

### Control Frames
| Frame | Description |
|-------|-------------|
| `02000100#XxYy` | Joystick position (10ms) |
| `0A040100#Pp` | Speed 0-100% (Pp=00-64) |
| `0C040100#` | Horn on |
| `0C040101#` | Horn off |
| `061#40400000` | Suspend mode |
| `061#00410000` | Select mode 1 |

### Status Frames
| Frame | Description |
|-------|-------------|
| `00E#SSSS...` | Serial heartbeat (50ms) |
| `03C30F0F#87...` | JSM heartbeat (100ms) |
| `1C0C0100#Xx` | Battery % (1000ms) |
| `14300100#LlHh` | Motor current (200ms) |

### Startup Frames
| Frame | Description |
|-------|-------------|
| `00C#` | Test network |
| `7B3#` / `7B3#R` | Serial exchange |
| `7B0#` / `7B1#` | Config mode |
| `1F0X...#` | Serial challenge/response |

## Joystick Values
```
       0x9C (-100)
           ↑
0x9C ←── 0x00 ──→ 0x64
  (-100)   (0)    (+100)
           ↓
       0x64 (+100)
```

## Serial Number Algorithm
```
key[n] = serial[n] XOR xor_table[n]
```

## Common Commands
```bash
# Monitor
candump can0 -L

# Joystick forward
cansend can0 02000100#0064

# Speed 50%
cansend can0 0A040100#32

# Horn beep
cansend can0 0C040100#; sleep .2; cansend can0 0C040101#

# Play tune
cansend can0 181C0D00#2050205120522053
```

## Safety
- Always have physical E-stop
- Test in controlled environment
- Implement software limits
