"""Eagle AI Tagger GUI 版入口"""
import multiprocessing
import sys
from pathlib import Path

# PyInstaller 打包後多進程必須加這個
multiprocessing.freeze_support()

# 確保專案根目錄在 sys.path 中
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    """啟動 GUI 應用程式"""
    from gui.app import EagleTaggerApp
    app = EagleTaggerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
