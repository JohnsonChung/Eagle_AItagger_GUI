from .base import BaseCheck, CheckResult
from gui.cuda_runtime import find_dll, CUDNN_MARKER_DLL, CUDNN_DOWNLOAD_URL


class CUDNNCheck(BaseCheck):
    """檢查 cuDNN 9 執行環境（發佈版不內附，需使用者自行安裝）"""

    def run(self) -> CheckResult:
        """尋找 cudnn64_9.dll（含 cuDNN 官方安裝程式的預設位置）"""
        dll_dir = find_dll(CUDNN_MARKER_DLL)
        if dll_dir:
            return CheckResult(
                name="cuDNN 9 函式庫",
                status="pass",
                message=f"已找到 cuDNN 9 ({dll_dir})",
            )

        return CheckResult(
            name="cuDNN 9 函式庫",
            status="fail",
            message=f"找不到 {CUDNN_MARKER_DLL}，請安裝 cuDNN 9.x (for CUDA 12)",
            fix_url=CUDNN_DOWNLOAD_URL,
        )
