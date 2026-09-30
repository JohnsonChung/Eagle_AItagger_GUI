import os
import configparser
from pathlib import Path
from .base import BaseCheck, CheckResult

class ModelCheck(BaseCheck):
    """檢查模型檔案"""
    
    def __init__(self, config_path: str = 'config.ini'):
        self.config_path = Path(config_path)
        
    def run(self) -> CheckResult:
        """讀取 config.ini 檢查 model 與 tags 檔案"""
        if not self.config_path.exists():
            return CheckResult(
                name="AI 模型檔案",
                status="warn",
                message=f"找不到設定檔 {self.config_path.name}，無法檢查模型"
            )
            
        try:
            config = configparser.ConfigParser()
            config.read(self.config_path, encoding='utf-8')
            
            if 'Model' not in config:
                return CheckResult(
                    name="AI 模型檔案",
                    status="warn",
                    message="設定檔中沒有 [Model] 區塊"
                )
                
            model_path_str = config['Model'].get('model_path')
            tags_path_str = config['Model'].get('tags_path')
            
            if not model_path_str or not tags_path_str:
                return CheckResult(
                    name="AI 模型檔案",
                    status="fail",
                    message="設定檔中缺少 model_path 或 tags_path"
                )
                
            model_path = Path(model_path_str)
            tags_path = Path(tags_path_str)
            
            missing_files = []
            if not model_path.exists():
                missing_files.append(f"模型檔案 ({model_path.name})")
            if not tags_path.exists():
                missing_files.append(f"標籤檔案 ({tags_path.name})")
                
            if missing_files:
                return CheckResult(
                    name="AI 模型檔案",
                    status="fail",
                    message=f"找不到以下檔案: {', '.join(missing_files)}"
                )
                
            return CheckResult(
                name="AI 模型檔案",
                status="pass",
                message="模型與標籤檔案檢查通過"
            )
            
        except Exception as e:
            return CheckResult(
                name="AI 模型檔案",
                status="fail",
                message=f"讀取設定檔時發生錯誤: {str(e)}"
            )
