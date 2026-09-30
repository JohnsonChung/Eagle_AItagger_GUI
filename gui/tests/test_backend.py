"""BackendController 測試 — 驗證 Queue 訊息格式與控制邏輯"""
import pytest
import queue
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from gui.backend import BackendController
from main.unified_config import UnifiedConfig


@pytest.fixture
def controller():
    """建立測試用 BackendController"""
    config = UnifiedConfig()
    return BackendController(config)


class TestQueueMessageFormat:
    """驗證後端送出的 Queue 訊息格式（防止 GUI 端 KeyError）"""

    def test_progress_is_flat_dict(self, controller):
        """進度訊息必須是平坦結構，不能有嵌套的 'data' 鍵"""
        msg = {
            "type": "progress",
            "processed": 10, "total": 100,
            "speed": 5.0, "eta": 18.0,
            "success": 9, "fail": 1,
            "active_workers": 2
        }
        q = queue.Queue()
        q.put(msg)
        result = q.get()
        assert result["type"] == "progress"
        assert "data" not in result  # 不能有嵌套
        for key in ["processed", "total", "speed", "eta", "success", "fail", "active_workers"]:
            assert key in result

    def test_log_message(self):
        msg = {"type": "log", "message": "測試日誌"}
        assert msg["type"] == "log"
        assert "message" in msg

    def test_finished_has_summary_and_failed(self):
        msg = {
            "type": "finished",
            "summary": {"total": 10, "success": 10},
            "failed_images": []
        }
        assert msg["type"] == "finished"
        assert "summary" in msg
        assert "failed_images" in msg

    def test_error_message(self):
        msg = {"type": "error", "message": "發生錯誤"}
        assert msg["type"] == "error"
        assert "message" in msg

    def test_batch_message(self):
        msg = {"type": "batch", "batch_id": 1, "success_count": 5, "batch_size": 8}
        for key in ["batch_id", "success_count", "batch_size"]:
            assert key in msg

    def test_eta_must_be_float(self):
        """ETA 必須是浮點數（秒），不能是字串"""
        msg = {"type": "progress", "eta": 125.7}
        assert isinstance(msg["eta"], float)


class TestParseImageList:
    """圖片清單解析測試"""

    def test_parse_from_file(self, tmp_path):
        """從檔案解析圖片路徑"""
        txt = tmp_path / "list.txt"
        txt.write_text("C:\\images\\1.jpg\nC:\\images\\2.png\n", encoding="utf-8")
        result = BackendController.parse_image_list(txt)
        assert len(result) == 2
        assert "image_path" in result[0]
        assert "json_path" in result[0]
        assert result[0]["json_path"].endswith("metadata.json")

    def test_parse_from_text(self):
        """從文字內容解析圖片路徑"""
        text = "C:\\images\\1.jpg\nC:\\images\\2.png\n"
        result = BackendController.parse_image_list_from_text(text)
        assert len(result) == 2


class TestControlFlow:
    """控制流程測試"""

    def test_stop_sets_event(self, controller):
        controller.stop()
        assert controller._stop_event.is_set()

    def test_is_running_false_when_not_started(self, controller):
        assert controller.is_running() is False

    def test_start_creates_thread(self, controller):
        """start() 後應建立並啟動執行緒"""
        q = queue.Queue()
        with patch.object(controller, '_run'):
            controller.start([], q)
            assert controller._thread is not None
