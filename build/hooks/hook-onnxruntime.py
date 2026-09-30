"""
PyInstaller hook for onnxruntime-gpu

收集 onnxruntime 的所有 CUDA 相關動態庫，
確保打包後 CUDAExecutionProvider 能正常載入。
"""
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# 收集 onnxruntime 的動態連結庫（包含 CUDA provider DLL）
binaries = collect_dynamic_libs('onnxruntime')

# 收集 onnxruntime 的資料檔案
datas = collect_data_files('onnxruntime')
