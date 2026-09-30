import sys
from .base import BaseCheck, CheckResult

class PythonCheck(BaseCheck):
    """檢查 Python 版本"""
    
    def run(self) -> CheckResult:
        """檢查 Python 版本是否 >= 3.8"""
        major = sys.version_info.major
        minor = sys.version_info.minor
        
        version_str = f"{major}.{minor}.{sys.version_info.micro}"
        
        if major > 3 or (major == 3 and minor >= 8):
            return CheckResult(
                name="Python 版本",
                status="pass",
                message=f"已安裝 Python {version_str}"
            )
        else:
            return CheckResult(
                name="Python 版本",
                status="fail",
                message=f"Python 版本必須 >= 3.8，目前為 {version_str}",
                fix_url="https://www.python.org/downloads/"
            )
