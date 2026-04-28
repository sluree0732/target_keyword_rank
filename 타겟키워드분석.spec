# -*- mode: python ; coding: utf-8 -*-
import os, sys
from PyInstaller.utils.hooks import collect_all

# curl_cffi 및 google-generativeai 데이터 수집
curl_datas, curl_binaries, curl_hiddenimports = collect_all('curl_cffi')
genai_datas, genai_binaries, genai_hiddenimports = collect_all('google.generativeai')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=curl_binaries + genai_binaries,
    datas=[
        ('ui', 'ui'),
        ('core', 'core'),
        ('utils', 'utils'),
        ('splash.png', '.'),
    ] + curl_datas + genai_datas,
    hiddenimports=[
        'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'openpyxl', 'bs4', 'lxml', 'curl_cffi',
        'google.generativeai',
        'google.ai.generativelanguage',
        'google.api_core',
        'google.auth',
        'grpc',
    ] + curl_hiddenimports + genai_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash,
    splash.binaries,
    name='타겟키워드분석',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # 여기에 .ico 파일 경로를 넣으면 아이콘이 바뀝니다
)
