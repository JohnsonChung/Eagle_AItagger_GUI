import os
import subprocess
from pathlib import Path
from .base import BaseCheck, CheckResult

class CUDACheck(BaseCheck):
    """檢查 CUDA 環境"""
    
    def run(self) -> CheckResult:
        """檢查 CUDA_PATH 或 nvcc 是否存在"""
        
        # 1. 檢查 CUDA_PATH 環境變數
        cuda_path = os.environ.get('CUDA_PATH')
        if cuda_path and os.path.exists(cuda_path):
            version = Path(cuda_path).name
            return CheckResult(
                name="CUDA 工具包",
                status="pass",
                message=f"已安裝 CUDA 工具包 ({version})"
            )
            
        # 2. 檢查預設路徑
        default_path = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA')
        if default_path.exists():
            subdirs = [d for d in default_path.iterdir() if d.is_dir()]
            if subdirs:
                version = subdirs[-1].name
                return CheckResult(
                    name="CUDA 工具包",
                    status="pass",
                    message=f"已在預設路徑找到 CUDA 工具包 ({version})"
                )
                
        # 3. 嘗試執行 nvcc --version
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, check=True)
            output = result.stdout
            if 'release' in output:
                # 簡單解析版本號
                lines = output.split('\n')
                for line in lines:
                    if 'release' in line:
                        return CheckResult(
                            name="CUDA 工具包",
                            status="pass",
                            message=f"已安裝 CUDA (nvcc: {line.strip()})"
                        )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        return CheckResult(
            name="CUDA 工具包",
            status="fail",
            message="找不到 CUDA_PATH，且 nvcc 指令無效",
            fix_url="https://developer.download.nvidia.com/compute/cuda/12.9.0/local_installers/cuda_12.9.0_576.02_windows.exe"
        )
