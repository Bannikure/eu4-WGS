# eu4_wgs.spec — PyInstaller build spec for EU4 World Generator Studio.
#
# PyInstaller does NOT cross-compile: run this ON WINDOWS (with Python +
# `pip install -r requirements.txt pyinstaller`) to get a Windows .exe.
# Build with:
#     pyinstaller eu4_wgs.spec
# Output:
#     dist/eu4-wgs/eu4-wgs.exe

import os
block_cipher = None
repo_root = os.path.abspath(os.getcwd())

a = Analysis(
    ['main.py'],
    pathex=[repo_root],
    binaries=[],
    datas=[
        ('eu4_wgs_v8/assets', 'eu4_wgs_v8/assets'),
        ('eu4_wgs_v8/templates', 'eu4_wgs_v8/templates'),
    ],
    hiddenimports=['customtkinter'],
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False, cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='eu4-wgs',
          debug=False, strip=False, upx=True, console=True)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name='eu4-wgs')
