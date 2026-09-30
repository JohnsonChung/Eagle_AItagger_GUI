import winreg
from .base import BaseCheck, CheckResult

class VCRedistCheck(BaseCheck):
    """檢查 VC++ 可轉發套件"""
    
    def run(self) -> CheckResult:
        """查詢登錄檔確認是否安裝 VC++ 2015-2022 Runtime"""
        
        try:
            # 開啟登錄檔機碼
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
            )
            
            # 讀取 Installed 值
            installed, _ = winreg.QueryValueEx(key, "Installed")
            winreg.CloseKey(key)
            
            if installed == 1:
                return CheckResult(
                    name="VC++ 執行階段套件",
                    status="pass",
                    message="已安裝 Visual C++ 2015-2022 Redistributable (x64)"
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            return CheckResult(
                name="VC++ 執行階段套件",
                status="fail",
                message=f"讀取登錄檔時發生錯誤: {str(e)}",
                fix_url="https://aka.ms/vs/17/release/vc_redist.x64.exe"
            )
            
        return CheckResult(
            name="VC++ 執行階段套件",
            status="fail",
            message="未安裝 Visual C++ 2015-2022 Redistributable (x64)",
            fix_url="https://aka.ms/vs/17/release/vc_redist.x64.exe"
        )
