import os
import glob
from pathlib import Path
from .base import BaseCheck, CheckResult

class CUDNNCheck(BaseCheck):
    """檢查 cuDNN 執行環境"""
    
    def run(self) -> CheckResult:
        """檢查 CUDA_PATH 下是否存在 cudnn*.dll"""
        cuda_path_str = os.environ.get('CUDA_PATH')
        if not cuda_path_str:
            default_path = r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA'
            if os.path.exists(default_path):
                # 找最新的版本
                versions = os.listdir(default_path)
                if versions:
                    cuda_path_str = os.path.join(default_path, versions[-1])
                    
        if not cuda_path_str or not os.path.exists(cuda_path_str):
            return CheckResult(
                name="cuDNN 函式庫",
                status="fail",
                message="找不到 CUDA 安裝路徑，無法檢查 cuDNN",
                fix_url="https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-9.10.1.4_cuda12-archive.zip"
            )
            
        cuda_path = Path(cuda_path_str)
        bin_dir = cuda_path / 'bin'
        
        if bin_dir.exists():
            # 尋找 cudnn*.dll
            dll_files = list(bin_dir.glob('cudnn*.dll'))
            if dll_files:
                return CheckResult(
                    name="cuDNN 函式庫",
                    status="pass",
                    message="已找到 cuDNN 相關檔案"
                )
                
        return CheckResult(
            name="cuDNN 函式庫",
            status="fail",
            message=f"在 {bin_dir} 中找不到 cudnn*.dll",
            fix_url="https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-9.10.1.4_cuda12-archive.zip"
        )
