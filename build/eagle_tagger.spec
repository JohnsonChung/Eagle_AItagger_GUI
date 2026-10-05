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

# --- 排除 CUDA / cuDNN / TensorRT 執行庫（約 1 GB）---
# 改由使用者自行安裝 CUDA 12 + cuDNN 9，啟動時由 gui/cuda_runtime.py 定位。
# 注意：onnxruntime_providers_cuda.dll 屬於 onnxruntime 本體，必須保留。
_CUDA_DLL_PREFIXES = (
    'cublas', 'cudart', 'cudnn', 'cufft', 'curand', 'cusolver', 'cusparse',
    'nvrtc', 'nvjitlink', 'nvinfer', 'nvonnxparser', 'nvblas',
)
a.binaries = [
    b for b in a.binaries
    if not os.path.basename(b[0]).lower().startswith(_CUDA_DLL_PREFIXES)
]

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

# 複製「預設設定」到 exe 旁邊（使用相對路徑，不帶入開發者本機的 config.ini）
config_src = os.path.join(str(ROOT), 'build', 'config.default.ini')
shutil.copy2(config_src, os.path.join(dist_dir, 'config.ini'))

# 建立 model/ 目錄和說明檔
model_dir = os.path.join(dist_dir, 'model')
os.makedirs(model_dir, exist_ok=True)
readme = os.path.join(model_dir, '請將模型放到這裡.txt')
with open(readme, 'w', encoding='utf-8') as f:
    f.write('請將 .onnx 模型檔案放到此目錄\n')
    f.write('預設檔名: model.onnx\n')
    f.write('推薦模型: https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3\n')
    f.write('其他檔名或模型可在 GUI 設定面板 / config.ini 中修改 model_path\n')

# 複製 csv/ 標籤字典到 exe 旁邊（如果不在 _internal 中）
csv_dst = os.path.join(dist_dir, 'csv')
csv_src = os.path.join(str(ROOT), 'csv')
if not os.path.exists(csv_dst) and os.path.exists(csv_src):
    shutil.copytree(csv_src, csv_dst)

# 安裝說明（CUDA / cuDNN 已不內附）
with open(os.path.join(dist_dir, '安裝說明.txt'), 'w', encoding='utf-8') as f:
    f.write(
        'Eagle AI Tagger — 安裝說明\n'
        '==========================\n\n'
        '1. 安裝 NVIDIA 顯示卡驅動（建議最新版）\n'
        '   https://www.nvidia.com/Download/index.aspx\n\n'
        '2. 安裝 CUDA Toolkit 12.x（必須是 12 版，13 版不相容）\n'
        '   https://developer.nvidia.com/cuda-12-9-0-download-archive\n\n'
        '3. 安裝 cuDNN 9.x for CUDA 12\n'
        '   https://developer.nvidia.com/cudnn-downloads\n'
        '   （使用官方安裝程式即可，程式啟動時會自動搜尋安裝位置）\n\n'
        '4. 下載模型 model.onnx 放到 model/ 資料夾\n'
        '   https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3\n\n'
        '5. 開啟 Eagle，執行 EagleTagger.exe\n'
        '   第一次啟動可先按「環境檢查」確認上述項目都通過。\n\n'
        '未安裝 CUDA / cuDNN 時仍可執行，但會以 CPU 運算，速度非常慢。\n'
    )
