# HexFlowUtility

A cross-platform utility tool for flashing firmware to ESP32 devices via serial connection.

## Features

- **Serial Port Management**: Connect/disconnect to ESP32 devices via serial port
- **Firmware Download**: Fetch firmware from API or browse local firmware files
- **Flash Firmware**: Flash firmware to ESP32 devices with password protection
- **Erase Flash**: Erase flash memory with password protection
- **Serial Monitor**: Real-time serial communication with configurable baud rate
- **Log Export**: Export logs with timestamps
- **Auto-scroll**: Automatic log scrolling option
- **Timestamp**: Optional timestamps for log entries
- **Dynamic Host Configuration**: Configure API host dynamically with persistent storage

## Platforms Supported

- ✅ Windows x64
- ✅ macOS x64 (Intel)
- ✅ macOS ARM64 (Apple Silicon)
- ✅ Linux x64 (Ubuntu/Debian)

## Installation

### Pre-built Binaries

Download the latest release from [GitHub Releases](https://github.com/YOUR_USERNAME/HexFlowUtility/releases).

**Windows:**
1. Download `HexFlowUtility-Windows-x64-vX.X.X.zip`
2. Extract the ZIP file
3. Run `HexFlowUtility.exe`

**macOS:**
1. Download `HexFlowUtility-macOS-x64-vX.X.X.tar.gz` (Intel) or `HexFlowUtility-macOS-arm64-vX.X.X.tar.gz` (Apple Silicon)
2. Extract the TAR.GZ file
3. Run the executable (may need to allow in Security & Privacy settings)

**Linux/Ubuntu:**
1. Download `HexFlowUtility-Linux-x64-vX.X.X.tar.gz`
2. Extract: `tar -xzf HexFlowUtility-Linux-x64-vX.X.X.tar.gz`
3. Make executable: `chmod +x HexFlowUtility`
4. Run: `./HexFlowUtility`

### From Source

**Requirements:**
- Python 3.9 or later
- pip

**Setup Virtual Environment (Recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install dependencies:**
```bash
pip install PyInstaller PySide6 pyserial requests esptool
```

**Run:**
```bash
python HexFlowUtility.py
```

**Build:**
```bash
# Build for current platform
pyinstaller --clean HexFlowUtility.spec
```

## Usage

1. **Connect to Device:**
   - Select a serial port from the dropdown
   - Click "CONNECT" (turns to "DISCONNECT" when connected)

2. **Configure API Host (Optional):**
   - Click the settings button (⚙) next to firmware selector
   - Enter new host with `https://` or `http://`
   - Configuration is saved automatically

3. **Select Firmware:**
   - Choose firmware from the API dropdown, or
   - Click browse button (⋯) to select a local `.bin` file

4. **Flash Firmware:**
   - Click "FLASH" button (red)
   - Enter password when prompted (default: `qwertyuiop`)
   - Monitor progress in the log area

5. **Erase Flash:**
   - Click "ERASE FLASH" button (orange)
   - Confirm the warning
   - Enter password when prompted

6. **Serial Monitor:**
   - Enter commands in the input box
   - Click "SEND" or press Enter
   - Adjust baud rate as needed
   - View output in the log area

7. **Log Management:**
   - Use "Auto Scroll" to automatically scroll to bottom
   - Use "Timestamp" to add timestamps to log entries
   - Use "Export" to save logs to a file
   - Use "Clear" to clear the log output

## Configuration

The application stores configuration in `config.json` (auto-created if not present):
```json
{
  "host": "https://your-api-host.com"
}
```

Default API host: `hadasklugv2-dev.smartguest.ai`

## Password

Default flash/erase password: `qwertyuiop`

You can change this in `HexFlowUtility.py`:
```python
FLASH_PASSWORD = "your-password-here"
```

## File Structure

```
HexFlowUtility/
├── HexFlowUtility.py      # Main application
├── HexFlowUtility.spec    # PyInstaller spec file
├── bootloader.bin         # ESP32 bootloader
├── partitions.bin         # Partition table
├── config.json            # Configuration file (auto-created)
├── VERSION                # Version file (auto-managed)
├── build_windows.bat      # Windows build script
├── BUILD_WINDOWS.md       # Windows build documentation
├── build/                 # PyInstaller build artifacts
├── dist/                  # Compiled executables output
│   ├── HexFlowUtility      # Linux/macOS executable
│   └── HexFlowUtility.app/ # macOS app bundle
├── venv/                  # Python virtual environment (optional)
└── .github/
    └── workflows/
        └── build-release.yml      # CI/CD workflow
```

## CI/CD

This repository includes GitHub Actions workflows that automatically:

- Build for all platforms on push to `main` branch
- Increment version number automatically
- Create GitHub releases with all platform builds
- Tag releases with version number

### Version Management

- Version is stored in `VERSION` file (format: `X.Y.Z`)
- Each build increments the patch version (Z)
- Version is committed back to the repository

## Development

### Local Build

**Windows:**
```cmd
build_windows.bat
```

Or manually:
```cmd
pyinstaller --clean --noconfirm HexFlowUtility.spec
```

**macOS/Linux:**
```bash
pip install PyInstaller PySide6 pyserial requests esptool
pyinstaller --clean HexFlowUtility.spec
```

The executable will be created in the `dist/` directory.

### Building Requirements

Ensure these files are present before building:
- `HexFlowUtility.py` (main application)
- `bootloader.bin` (ESP32 bootloader)
- `partitions.bin` (partition table)
- `HexFlowUtility.spec` (PyInstaller spec file)

### Testing

1. Test serial port connection
2. Test firmware download from API
3. Test local firmware selection
4. Test flash and erase operations
5. Test log export functionality
6. Test serial monitor with different baud rates

## Troubleshooting

### Serial Port Not Found
- Ensure device is connected
- Check USB drivers are installed
- Try refreshing ports (↻ button)
- On Linux, may need to add user to `dialout` group: `sudo usermod -a -G dialout $USER`

### Flash Fails
- Verify `bootloader.bin` and `partitions.bin` are in the same directory as the executable
- Check serial port connection is active
- Ensure password is correct
- Check log output for detailed error messages
- Try disconnecting and reconnecting the device

### "bootloader.bin or partitions.bin not found" Error
- **For one-file executables**: The files should be automatically bundled during build
- **Solution**: Rebuild the application using `pyinstaller --clean HexFlowUtility.spec`
- Verify that `bootloader.bin` and `partitions.bin` exist in the project root directory before building
- Check that the spec file includes these files in the `datas` section:
  ```python
  datas=[
      ('bootloader.bin', '.'),
      ('partitions.bin', '.'),
  ],
  ```

### macOS Security Warning
- Go to System Preferences > Security & Privacy
- Click "Open Anyway" for the application
- Or remove quarantine attribute: `xattr -d com.apple.quarantine HexFlowUtility.app`

### Linux Permission Denied
- Make sure executable has permissions: `chmod +x HexFlowUtility`
- Some distributions may require additional libraries (see workflow file for dependencies)
- Check serial port permissions (add user to `dialout` group)

### Module Not Found Errors
- Ensure all dependencies are installed: `pip install PySide6 pyserial requests esptool`
- If using virtual environment, make sure it's activated
- Check that `hiddenimports` in spec file includes all required modules

### Large Executable Size
- This is normal - the executable includes Python interpreter and Qt libraries
- Typical size: 100-200MB for standalone executable
- Can use `onefile=False` in spec to create folder distribution instead

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

