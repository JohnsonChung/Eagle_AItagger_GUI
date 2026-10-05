from .base import BaseCheck, CheckResult
from gui.cuda_runtime import find_dll, CUDA_MARKER_DLL, CUDA_DOWNLOAD_URL


class CUDACheck(BaseCheck):
    """檢查 CUDA 12 執行環境（發佈版不內附，需使用者自行安裝）"""

    def run(self) -> CheckResult:
        """尋找 onnxruntime-gpu 需要的 CUDA 12 DLL"""
        dll_dir = find_dll(CUDA_MARKER_DLL)
        if dll_dir:
            return CheckResult(
                name="CUDA 12 工具包",
                status="pass",
                message=f"已找到 CUDA 12 ({dll_dir})",
            )

        return CheckResult(
            name="CUDA 12 工具包",
            status="fail",
            message=f"找不到 {CUDA_MARKER_DLL}，請安裝 CUDA Toolkit 12.x（未安裝時將以 CPU 執行，速度很慢）",
            fix_url=CUDA_DOWNLOAD_URL,
        )
