@echo off
REM Build script for HexFlowUtility Windows executable
echo ========================================
echo HexFlowUtility - Windows Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or later
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version

echo.
echo [2/4] Installing/updating required packages...
pip install --upgrade PyInstaller PySide6 pyserial requests esptool

echo.
echo [3/4] Checking required files...
if not exist "HexFlowUtility.py" (
    echo ERROR: HexFlowUtility.py not found!
    pause
    exit /b 1
)
if not exist "bootloader.bin" (
    echo WARNING: bootloader.bin not found!
)
if not exist "partitions.bin" (
    echo WARNING: partitions.bin not found!
)
if not exist "HexFlowUtility.spec" (
    echo ERROR: HexFlowUtility.spec not found!
    pause
    exit /b 1
)

echo.
echo [4/4] Building executable...
python -m PyInstaller --clean --noconfirm HexFlowUtility.spec

echo.
if exist "dist\HexFlowUtility.exe" (
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Executable location: dist\HexFlowUtility.exe
    echo.
) else (
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo Check the error messages above.
    echo.
)

pause

