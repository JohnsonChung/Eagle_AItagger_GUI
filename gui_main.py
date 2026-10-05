"""Eagle AI Tagger GUI 版入口"""
import multiprocessing
import os
import sys
from pathlib import Path

# PyInstaller 打包後多進程必須加這個
multiprocessing.freeze_support()

# 確保專案根目錄在 sys.path 中
# PyInstaller 打包後 __file__ 在 _internal/ 內，需切到 exe 所在目錄
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

os.chdir(ROOT_DIR)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 發佈版不內附 CUDA DLL，需在載入 onnxruntime 前定位使用者安裝的 CUDA / cuDNN
from gui.cuda_runtime import register_cuda_dll_dirs
register_cuda_dll_dirs()


def main():
    """啟動 GUI 應用程式"""
    from gui.app import EagleTaggerApp
    app = EagleTaggerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
