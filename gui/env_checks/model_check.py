import os
import configparser
from pathlib import Path
from .base import BaseCheck, CheckResult


class ModelCheck(BaseCheck):
    """檢查模型檔案

    支援兩種模式:
    1. 傳入 model_path / tags_path → 直接檢查（GUI 即時路徑）
    2. 僅傳入 config_path → 從 config.ini 讀取路徑
    """

    def __init__(
        self,
        config_path: str = 'config.ini',
        model_path: str = None,
        tags_path: str = None,
    ):
        self.config_path = Path(config_path)
        self._model_path = model_path
        self._tags_path = tags_path

    def run(self) -> CheckResult:
        """檢查模型與標籤檔案是否存在"""

        # 優先使用直接傳入的路徑（來自 GUI 設定面板）
        model_path_str = self._model_path
        tags_path_str = self._tags_path

        # 若沒有直接傳入，從 config.ini 讀取
        if not model_path_str or not tags_path_str:
            result = self._read_from_config()
            if isinstance(result, CheckResult):
                return result  # config 讀取失敗
            model_path_str = model_path_str or result[0]
            tags_path_str = tags_path_str or result[1]

        model_path = Path(model_path_str)
        tags_path = Path(tags_path_str)

        missing_files = []
        if not model_path.exists():
            missing_files.append(f"模型檔案 ({model_path})")
        if not tags_path.exists():
            missing_files.append(f"標籤檔案 ({tags_path})")

        if missing_files:
            return CheckResult(
                name="AI 模型檔案",
                status="fail",
                message=f"找不到以下檔案: {', '.join(missing_files)}"
            )

        return CheckResult(
            name="AI 模型檔案",
            status="pass",
            message=f"模型檢查通過 ({model_path.name})"
        )

    def _read_from_config(self):
        """從 config.ini 讀取模型路徑，回傳 (model_path, tags_path) 或 CheckResult"""
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

            model_path = config['Model'].get('model_path')
            tags_path = config['Model'].get('tags_path')

            if not model_path or not tags_path:
                return CheckResult(
                    name="AI 模型檔案",
                    status="fail",
                    message="設定檔中缺少 model_path 或 tags_path"
                )

            return (model_path, tags_path)

        except Exception as e:
            return CheckResult(
                name="AI 模型檔案",
                status="fail",
                message=f"讀取設定檔時發生錯誤: {str(e)}"
            )
