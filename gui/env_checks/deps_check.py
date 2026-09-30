import importlib
from .base import BaseCheck, CheckResult

class DepsCheck(BaseCheck):
    """檢查依賴套件"""
    
    def run(self) -> CheckResult:
        """嘗試載入需要的套件"""
        critical_deps = ['onnxruntime', 'cv2', 'PIL', 'pandas', 'numpy', 'pillow_heif']
        missing = []
        
        for dep in critical_deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)
                
        if not missing:
            return CheckResult(
                name="Python 依賴套件",
                status="pass",
                message="所有必要的 Python 套件皆已安裝"
            )
        else:
            return CheckResult(
                name="Python 依賴套件",
                status="fail",
                message=f"缺少必要的 Python 套件: {', '.join(missing)}。請執行 pip install -r requirements.txt"
            )
