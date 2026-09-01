# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [('DW.ico', '.'), ('codeline.png', '.'), ('bin', 'bin')]
binaries = []
hiddenimports = [
    'PIL',
    'PIL._tkinter_finder',
    'PIL.Image',
    'darkdetect',
    'customtkinter',
    'core',
    'core.downloader',
    'core.formats',
    'core.history',
    'core.installer',
    'core.settings',
    'ui',
    'ui.main_window',
    'ui.dialogs',
    'ui.settings_window',
    'ui.about_dialog',
    'ui.history_window',
]

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret_dd = collect_all('darkdetect')
datas += tmp_ret_dd[0]
binaries += tmp_ret_dd[1]
hiddenimports += tmp_ret_dd[2]

a = Analysis(
    ['app.py'],
    pathex=['j:\\RickHardBR\\DYTB'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DYTBV2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['DW.ico'],
)
