"""共用 pytest fixtures"""
import pytest
from unittest.mock import MagicMock
from gui.env_checks.base import CheckResult
from main.unified_config import UnifiedConfig


@pytest.fixture
def mock_eagle_api():
    """回傳一個模擬的 EagleAPI 實例，不需要真實 Eagle 連線"""
    from gui.eagle_api import EagleAPI
    api = EagleAPI(base_url="http://localhost:41595")
    return api


@pytest.fixture
def sample_config():
    """回傳測試用的 UnifiedConfig（使用預設值）"""
    return UnifiedConfig()


@pytest.fixture
def sample_image_data():
    """回傳用於測試的圖像資料列表"""
    return [
        {"image_path": "C:\\lib.library\\images\\1.info\\1.jpg", "json_path": "C:\\lib.library\\images\\1.info\\metadata.json"},
        {"image_path": "C:\\lib.library\\images\\2.info\\2.png", "json_path": "C:\\lib.library\\images\\2.info\\metadata.json"},
    ]


@pytest.fixture
def sample_check_result():
    """回傳一系列測試用的 CheckResult"""
    return {
        "pass": CheckResult(name="TestPass", status="pass", message="通過測試"),
        "fail": CheckResult(name="TestFail", status="fail", message="失敗測試", fix_url="http://fix"),
        "warn": CheckResult(name="TestWarn", status="warn", message="警告測試"),
    }
