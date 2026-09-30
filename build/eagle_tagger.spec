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

# --- 後處理：複製 config.ini 和建立 model/ 目錄 ---
import shutil

dist_dir = os.path.join(SPECPATH, '..', 'dist', 'EagleTagger')

# 複製 config.ini 到 exe 旁邊（讓使用者可以編輯）
config_src = os.path.join(str(ROOT), 'config.ini')
if os.path.exists(config_src):
    shutil.copy2(config_src, dist_dir)

# 建立 model/ 目錄和說明檔
model_dir = os.path.join(dist_dir, 'model')
os.makedirs(model_dir, exist_ok=True)
readme = os.path.join(model_dir, '請將模型放到這裡.txt')
if not os.path.exists(readme):
    with open(readme, 'w', encoding='utf-8') as f:
        f.write('請將 .onnx 模型檔案放到此目錄\n')
        f.write('預設使用: eva02.onnx\n')
        f.write('可在 config.ini 中修改 model_path 設定\n')

# 複製 csv/ 標籤字典到 exe 旁邊（如果不在 _internal 中）
csv_dst = os.path.join(dist_dir, 'csv')
csv_src = os.path.join(str(ROOT), 'csv')
if not os.path.exists(csv_dst) and os.path.exists(csv_src):
    shutil.copytree(csv_src, csv_dst)
