# -*- mode: python ; coding: utf-8 -*-
import os, sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

kiwi_datas, kiwi_binaries, kiwi_hiddenimports = collect_all('kiwipiepy')
curl_datas, curl_binaries, curl_hiddenimports = collect_all('curl_cffi')
kiwi_model_datas, _, _ = collect_all('kiwipiepy_model')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=kiwi_binaries + curl_binaries,
    datas=[
        ('ui', 'ui'),
        ('core', 'core'),
        ('utils', 'utils'),
    ] + kiwi_datas + curl_datas + kiwi_model_datas,
    hiddenimports=[
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
        'bs4', 'lxml', 'lxml.etree', 'lxml._elementpath',
        'requests', 'urllib3',
        'kiwipiepy', 'kiwipiepy.utils',
        'curl_cffi', 'curl_cffi.requests',
    ] + kiwi_hiddenimports + curl_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='타겟키워드분석',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='타겟키워드분석',
)
