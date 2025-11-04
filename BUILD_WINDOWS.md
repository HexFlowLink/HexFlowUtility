# Building HexFlowUtility for Windows

This guide will walk you through building the HexFlowUtility application for Windows production.

## Prerequisites

1. **Python 3.9 or later** installed on Windows
2. **pip** (Python package manager)
3. All source files in the project directory:
   - `HexFlowUtility.py`
   - `bootloader.bin`
   - `partitions.bin`
   - `HexFlowUtility.spec`

## Step 1: Install Required Packages

Open Command Prompt or PowerShell and navigate to your project directory:

```cmd
cd C:\path\to\HexFlowUtility
```

Install required Python packages:

```cmd
pip install PyInstaller
pip install PySide6
pip install pyserial
pip install requests
pip install esptool
```

## Step 2: Verify Files Are Present

Ensure these files exist in your project directory:
- ✅ `HexFlowUtility.py` (main application)
- ✅ `bootloader.bin` (bootloader file)
- ✅ `partitions.bin` (partitions file)
- ✅ `HexFlowUtility.spec` (PyInstaller spec file)

## Step 3: Build the Application

Run PyInstaller with the spec file:

```cmd
pyinstaller HexFlowUtility.spec
```

This will:
- Analyze dependencies
- Bundle all required libraries
- Include bootloader.bin and partitions.bin
- Create a standalone executable

## Step 4: Find Your Executable

After building, the executable will be located at:

```
dist\HexFlowUtility.exe
```

## Step 5: Test the Build

1. Navigate to the `dist` folder
2. Run `HexFlowUtility.exe`
3. Verify all features work:
   - Serial port connection
   - Firmware loading
   - Flash functionality
   - Erase flash functionality
   - Log export

## Step 6: Distribution

To distribute the application:

1. **Option A: Single Executable**
   - Copy `HexFlowUtility.exe` from the `dist` folder
   - This is a standalone executable (no dependencies needed)
   - Users can run it directly

2. **Option B: Installer Package (Advanced)**
   - Use tools like Inno Setup or NSIS to create an installer
   - Include the .exe and any additional documentation

## Troubleshooting

### Issue: "ModuleNotFoundError" when running exe

**Solution:** Check that all required modules are listed in `hiddenimports` in the spec file.

### Issue: "Stub flasher JSON file for ESP32 not found"

**Solution:** This is already fixed in the current spec file. The esptool stub files are automatically included via the `datas` section which bundles `esptool/targets` directory.

### Issue: "bootloader.bin not found" error

**Solution:** Ensure `bootloader.bin` and `partitions.bin` are in the same directory as `HexFlowUtility.spec` when building.

### Issue: Serial port permission error when flashing

**Solution:** Make sure to disconnect serial monitor before flashing. The app automatically handles this, but if issues persist, try closing and reopening the application.

### Issue: Application opens console window

**Solution:** Verify `console=False` in the spec file under the `EXE` section.

### Issue: Large file size

**Solution:** 
- Remove `upx=True` from spec file (may reduce size but slower compression)
- Or add more exclusions in the `excludes` list

## Build Options

### Clean Build

To start fresh:

```cmd
pyinstaller --clean HexFlowUtility.spec
```

### One-File vs One-Folder

The current spec creates a **one-file** executable. If you prefer a folder distribution:

Change in spec file:
- Remove `a.scripts, a.binaries, a.zipfiles, a.datas, []` from EXE
- Use `COLLECT` instead of bundling everything

### Adding an Icon

1. Create or obtain an `.ico` file (e.g., `icon.ico`)
2. Update spec file line 58:
   ```python
   icon='icon.ico',
   ```
3. Place `icon.ico` in the project directory

## Notes

- The first build may take several minutes
- Subsequent builds are faster due to caching
- The executable includes Python interpreter and all dependencies
- File size will be ~100-200MB (includes Qt libraries)
- Users do NOT need Python installed to run the .exe

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)

