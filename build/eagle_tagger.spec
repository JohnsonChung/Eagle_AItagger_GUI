# -*- mode: python ; coding: utf-8 -*-
"""
Eagle AI Tagger GUI — PyInstaller 打包規格檔

使用方式:
    cd m:\Github\Eagle_AItagger_byWD1.4
    pyinstaller build/eagle_tagger.spec

輸出目錄: dist/EagleTagger/
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# 專案根目錄
ROOT = Path(SPECPATH).parent

# 收集 onnxruntime 的動態庫
onnxruntime_binaries = collect_dynamic_libs('onnxruntime')

# 收集 customtkinter 的主題資源
customtkinter_data = collect_data_files('customtkinter')

a = Analysis(
    [str(ROOT / 'gui_main.py')],
    pathex=[str(ROOT)],
    binaries=onnxruntime_binaries,
    datas=[
        # 標籤字典
        (str(ROOT / 'csv'), 'csv'),
        # customtkinter 主題和資源
        *customtkinter_data,
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'pillow_heif',
        'cv2',
        'pandas',
        'numpy',
        'onnxruntime',
        'onnxruntime.capi',
        'psutil',
        'pynvml',
        'requests',
        'packaging',
        'packaging.version',
        'configparser',
    ],
    hookspath=[str(ROOT / 'build' / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型套件
        'torch',
        'torchvision',
        'torchaudio',
        'xformers',
        'sympy',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'tensorboard',
        'jinja2',
        'markupsafe',
    ],
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
    exclude_binaries=True,  # onedir 模式
    name='EagleTagger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不顯示命令列視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(ROOT / 'gui' / 'assets' / 'icon.ico'),  # 暫時未提供圖示
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EagleTagger',
)
