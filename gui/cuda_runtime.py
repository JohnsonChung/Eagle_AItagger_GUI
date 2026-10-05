"""CUDA / cuDNN 執行環境定位

發佈版不再內附 CUDA DLL，改由使用者自行安裝：
  - CUDA Toolkit 12.x  → cublas64_12.dll / cublasLt64_12.dll / cudart64_12.dll / cufft64_11.dll
  - cuDNN 9.x (CUDA 12) → cudnn64_9.dll 及其子模組

cuDNN 9 官方安裝程式會裝到 C:\\Program Files\\NVIDIA\\CUDNN\\v9.x\\bin\\12.x\\，
預設不會加入 PATH，所以啟動時主動搜尋常見位置並註冊到 DLL 搜尋路徑。
"""
import glob
import os
import sys
from pathlib import Path
from typing import List, Optional

# onnxruntime-gpu 1.2x 所需的關鍵 DLL
CUDA_MARKER_DLL = "cublasLt64_12.dll"
CUDNN_MARKER_DLL = "cudnn64_9.dll"

CUDA_DOWNLOAD_URL = "https://developer.nvidia.com/cuda-12-9-0-download-archive"
CUDNN_DOWNLOAD_URL = "https://developer.nvidia.com/cudnn-downloads"

_PROGRAM_FILES = os.environ.get("ProgramFiles", r"C:\Program Files")


def _candidate_dirs() -> List[Path]:
    """列出可能含有 CUDA / cuDNN DLL 的目錄（依優先序，已去重）"""
    candidates: List[str] = []

    # 1. CUDA_PATH 與 CUDA_PATH_V12_x 環境變數
    for key, value in os.environ.items():
        if key.upper() == "CUDA_PATH" or key.upper().startswith("CUDA_PATH_V12"):
            candidates.append(os.path.join(value, "bin"))

    # 2. CUDA Toolkit 預設安裝位置（新版本優先）
    toolkit = os.path.join(_PROGRAM_FILES, "NVIDIA GPU Computing Toolkit", "CUDA")
    candidates += sorted(glob.glob(os.path.join(toolkit, "v12*", "bin")), reverse=True)

    # 3. cuDNN 9 官方安裝程式位置
    cudnn_root = os.path.join(_PROGRAM_FILES, "NVIDIA", "CUDNN")
    candidates += sorted(glob.glob(os.path.join(cudnn_root, "v9*", "bin", "12*")), reverse=True)
    candidates += sorted(glob.glob(os.path.join(cudnn_root, "v9*", "bin")), reverse=True)

    # 4. 目前 PATH 中的目錄
    candidates += os.environ.get("PATH", "").split(os.pathsep)

    seen, result = set(), []
    for c in candidates:
        if not c:
            continue
        p = Path(c)
        key = str(p).lower().rstrip("\\/")
        if key in seen or not p.is_dir():
            continue
        seen.add(key)
        result.append(p)
    return result


def find_dll(dll_name: str) -> Optional[Path]:
    """在候選目錄中尋找指定 DLL，回傳所在目錄"""
    for d in _candidate_dirs():
        if (d / dll_name).is_file():
            return d
    return None


def register_cuda_dll_dirs() -> List[Path]:
    """把找到的 CUDA / cuDNN 目錄加入 DLL 搜尋路徑

    同時寫入 PATH，確保 multiprocessing 子進程也能載入。
    回傳實際註冊的目錄列表。
    """
    if sys.platform != "win32":
        return []

    registered: List[Path] = []
    for dll in (CUDA_MARKER_DLL, CUDNN_MARKER_DLL):
        d = find_dll(dll)
        if d and d not in registered:
            registered.append(d)

    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    path_lower = {p.lower().rstrip("\\/") for p in path_parts}
    for d in registered:
        try:
            os.add_dll_directory(str(d))
        except (OSError, AttributeError):
            pass
        if str(d).lower().rstrip("\\/") not in path_lower:
            path_parts.insert(0, str(d))
    os.environ["PATH"] = os.pathsep.join(path_parts)
    return registered
