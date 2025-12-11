# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
import site

# 获取vosk库的DLL路径
vosk_path = None
for site_dir in site.getsitepackages():
    potential_path = os.path.join(site_dir, 'vosk')
    if os.path.exists(potential_path):
        vosk_path = potential_path
        break

# 收集vosk的二进制文件
vosk_binaries = []
if vosk_path:
    for file in os.listdir(vosk_path):
        if file.endswith('.dll') or file.endswith('.so'):
            vosk_binaries.append((os.path.join(vosk_path, file), 'vosk'))

a = Analysis(
    ['main_qt.py'],
    pathex=[],
    binaries=vosk_binaries,
    datas=[
        ('vosk-model-small-cn-0.22', 'vosk-model-small-cn-0.22'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        # TTS相关
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'win32com.client',
        'pythoncom',
        # Office文档处理
        'openpyxl.cell._writer',
        'openpyxl.styles.stylesheet',
        'openpyxl.styles.colors',
        'openpyxl.styles.fills',
        'openpyxl.styles.fonts',
        'openpyxl.styles.borders',
        'openpyxl.styles.alignment',
        'openpyxl.worksheet._writer',
        'openpyxl.worksheet._read_only',
        'openpyxl.worksheet.table',
        'pptx',
        'pptx.util',
        'pptx.enum.text',
        'docx',
        'docx.shared',
        'PyPDF2',
        'PyPDF2._reader',
        'PyPDF2._writer',
        'PyPDF2._merger',
        # 网页处理
        'bs4',
        'bs4.builder._htmlparser',
        'bs4.builder._lxml',
        # 图像处理
        'PIL',
        'PIL._imaging',
        # 音频处理
        'pyaudio',
        'wave',
        'numpy',
        'numpy.core._multiarray_umath',
        # 语音识别
        'vosk',
        # 其他
        'markdown',
        'pyperclip',
        'keyboard',
        'keyboard._winkeyboard',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AIDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AIDesk',
)