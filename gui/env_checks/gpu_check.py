import subprocess
import json
from .base import BaseCheck, CheckResult

class GPUCheck(BaseCheck):
    """檢查 NVIDIA GPU 及其 VRAM"""
    
    def run(self) -> CheckResult:
        """檢查是否安裝 NVIDIA GPU 且 VRAM >= 4GB"""
        try:
            # 嘗試使用 nvidia-smi 獲取 GPU 資訊
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()
            if output:
                name, vram_str = output.split(', ')
                vram_mb = int(vram_str.replace(' MiB', ''))
                vram_gb = vram_mb / 1024.0
                
                if vram_gb >= 4.0:
                    return CheckResult(
                        name="NVIDIA GPU",
                        status="pass",
                        message=f"偵測到 {name} ({vram_gb:.1f} GB VRAM)"
                    )
                else:
                    return CheckResult(
                        name="NVIDIA GPU",
                        status="warn",
                        message=f"偵測到 {name}，但 VRAM 只有 {vram_gb:.1f} GB (建議 >= 4GB)"
                    )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # nvidia-smi 不存在，嘗試使用 WMI
            try:
                wmi_cmd = ['powershell', '-Command', 'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json']
                result = subprocess.run(wmi_cmd, capture_output=True, text=True, check=True)
                if result.stdout.strip():
                    data = json.loads(result.stdout)
                    
                    if not isinstance(data, list):
                        data = [data]
                        
                    for gpu in data:
                        name = gpu.get('Name', '')
                        if 'NVIDIA' in name.upper():
                            vram_bytes = gpu.get('AdapterRAM', 0)
                            vram_gb = vram_bytes / (1024**3)
                            if vram_gb >= 4.0:
                                return CheckResult(
                                    name="NVIDIA GPU",
                                    status="pass",
                                    message=f"偵測到 {name} ({vram_gb:.1f} GB VRAM)"
                                )
                            else:
                                return CheckResult(
                                    name="NVIDIA GPU",
                                    status="warn",
                                    message=f"偵測到 {name}，但 VRAM 只有 {vram_gb:.1f} GB (建議 >= 4GB)"
                                )
                    
            except Exception as e:
                pass
                
        return CheckResult(
            name="NVIDIA GPU",
            status="fail",
            message="未偵測到 NVIDIA GPU 或 nvidia-smi 執行失敗"
        )
