# -*- mode: python ; coding: utf-8 -*-
import os
import esptool

block_cipher = None

# Get the directory where the spec file is located
spec_dir = os.path.dirname(SPECPATH)

# Get esptool directory and include its stub files
esptool_dir = os.path.dirname(esptool.__file__)
esptool_targets = os.path.join(esptool_dir, 'targets')

a = Analysis(
    ['HexFlowUtility.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        ('bootloader.bin', '.'),
        ('partitions.bin', '.'),
        (esptool_targets, 'esptool/targets'),  # Include esptool stub files
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'serial',
        'serial.tools.list_ports',
        'requests',
        'esptool',
        'esptool.__main__',
        'esptool.cmds',
        'esptool.loader',
        'esptool.util',
        'esptool.targets',
        'esptool.targets.esp32',
        'esptool.targets.esp32c2',
        'esptool.targets.esp32c3',
        'esptool.targets.esp32c6',
        'esptool.targets.esp32h2',
        'esptool.targets.esp32s2',
        'esptool.targets.esp32s3',
        'esptool.reset',
        'esptool.bin_image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HexFlowUtility',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# For macOS, create an APP bundle (comment out if you just want executable)
# app = BUNDLE(
#     exe,
#     name='HexFlowUtility.app',
#     icon=None,
#     bundle_identifier='com.hexflow.utility',
# )
