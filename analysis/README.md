# R-Net Tools

Analysis and utility tools for R-Net protocol research.

## Firmware Analysis Tools

### analyze_ledjsm_config.py
Analyzes LEDJSM plaintext configuration and generates documentation.
```bash
python3 tools/analyze_ledjsm_config.py
# Output: docs/LEDJSM_CONFIG_ANALYSIS.txt
```

### decrypt_btmouse.py
Attempts to decrypt BTMouse configuration using various methods.
```bash
python3 tools/decrypt_btmouse.py
# Output: btmouse_config_decrypted.bin
```

### analyze_encryption.py
Block-by-block encryption analysis comparing BTMouse and LEDJSM.
```bash
python3 tools/analyze_encryption.py
```

### btmouse_deep_analysis.py
Deep analysis of BTMouse firmware structure and patterns.
```bash
python3 tools/btmouse_deep_analysis.py
```

### try_aes_decrypt.py
Attempts AES and advanced XOR decryption schemes.
```bash
pip install pycryptodome  # optional, for AES
python3 tools/try_aes_decrypt.py
```

## Configuration Tools

### rnet_config_parser.py
Parses R-Net Programmer .R-net configuration exports.
```bash
# Parse single config
python3 rnet_config_parser.py "R-Net Configs/R-Net Configs/V6/stock.R-net"

# Compare stock vs modified
python3 rnet_config_parser.py stock.R-net mod.R-net --diff

# Focus on motor settings
python3 rnet_config_parser.py config.R-net --motor

# JSON output
python3 rnet_config_parser.py config.R-net --json

# Show raw hex sections
python3 rnet_config_parser.py config.R-net --raw
```

Extracts:
- Speed profiles (SLOWEST, SLOW, MEDIUM, FAST, custom names)
- Motor current limits (stock 55%, mods up to 100%)
- Seating functions (Tilt, Recline, Seat Lift, etc.)
- Mode profiles (Drive, Seating, Bluetooth, etc.)

### extract_config_data.py
Extracts configuration transfer data from pcap files.
```bash
python3 tools/extract_config_data.py wireshark/ics_write_config.pcapng output.bin
```

## Logic Analyzer Tools

### saleae_csv_parser.py
Parses Saleae logic analyzer CSV exports.

### salea_anlysis3.py / salea_anlysis5.py / salea_anlysis7.py
Legacy Saleae analysis scripts from original research (May-June 2016).

## Main Tools (Root Directory)

### rnet_programmer.py
R-Net Programmer mode tool for reading/writing device configuration.
```bash
# Test programmer handshake
python3 rnet_programmer.py handshake -v

# Enable programmer mode
python3 rnet_programmer.py enable

# Read memory
python3 rnet_programmer.py read 0x0000 0x100 -o dump.bin

# Write data
python3 rnet_programmer.py write 0x0100 --data DEADBEEF

# Dump memory range
python3 rnet_programmer.py dump 0x0000 0x2000 -o config.bin

# Monitor CAN bus
python3 rnet_programmer.py monitor --filter 78F,793,7A0
```

### rnet_utils.py
Protocol analysis utility with multiple commands.
```bash
# Decode serial number with XOR table
python3 rnet_utils.py decode-serial 08901c8a00000000 --xor 002102ccdd127b45

# Decode R-Net frames
python3 rnet_utils.py decode-frame 02000100#0064

# Analyze capture file
python3 rnet_utils.py analyze wireshark/july12_light.log

# Extract authentication info
python3 rnet_utils.py extract-auth capture.log

# Generate auth frames
python3 rnet_utils.py generate-auth 08901c8a00000000 --table standalone_jsm

# Calculate joystick frame
python3 rnet_utils.py joystick 0 100      # full forward
python3 rnet_utils.py joystick 50 50 -c   # continuous send

# Extract cJSM display text
python3 rnet_utils.py extract-display capture.log -v

# List known XOR tables
python3 rnet_utils.py list-tables
```

## Requirements

- Python 3.8+
- python-can (for CAN bus tools)
- pycryptodome (optional, for AES decryption)
- SocketCAN interface (Linux)

```bash
pip install python-can pycryptodome
```
