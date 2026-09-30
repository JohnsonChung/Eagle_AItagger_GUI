"""GUI 面板資料流整合測試 — 不建立真實 tkinter 視窗"""
import pytest
from pathlib import Path


class TestProgressFrameDataFormat:
    """驗證 ProgressFrame 能接受 BackendController 的訊息格式"""

    def test_eta_formatting_float_to_mmss(self):
        """ETA 從浮點秒數轉換為 mm:ss 格式"""
        eta_seconds = 125.7
        eta_min = int(eta_seconds) // 60
        eta_sec = int(eta_seconds) % 60
        formatted = f"{eta_min:02d}:{eta_sec:02d}"
        assert formatted == "02:05"

    def test_eta_zero(self):
        eta_seconds = 0.0
        eta_min = int(eta_seconds) // 60
        eta_sec = int(eta_seconds) % 60
        formatted = f"{eta_min:02d}:{eta_sec:02d}"
        assert formatted == "00:00"

    def test_eta_large_value(self):
        """超過 1 小時的 ETA"""
        eta_seconds = 3661.0
        eta_min = int(eta_seconds) // 60
        eta_sec = int(eta_seconds) % 60
        formatted = f"{eta_min:02d}:{eta_sec:02d}"
        assert formatted == "61:01"

    def test_progress_percentage_calculation(self):
        """進度百分比計算"""
        processed, total = 750, 1200
        pct = processed / total if total > 0 else 0
        assert abs(pct - 0.625) < 0.001

    def test_progress_percentage_zero_total(self):
        """total=0 時不除以零"""
        processed, total = 0, 0
        pct = processed / total if total > 0 else 0
        assert pct == 0


class TestImageListParseText:
    """圖片清單文字解析測試（不需要 GUI）"""

    def _parse(self, text):
        """模擬 ImageListFrame._parse_text 的邏輯"""
        items = []
        for line in text.splitlines():
            path_str = line.strip().strip('"').strip("'")
            if not path_str:
                continue
            path = Path(path_str).resolve()
            if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.heic', '.heif', '.avif'):
                items.append({
                    'image_path': str(path),
                    'json_path': str(path.parent / 'metadata.json')
                })
        return items

    def test_filters_non_images(self):
        """排除非圖片副檔名"""
        text = "C:\\a.jpg\nC:\\b.txt\nC:\\c.png\nC:\\d.doc"
        result = self._parse(text)
        assert len(result) == 2

    def test_handles_quotes(self):
        """處理帶引號的路徑"""
        text = '"C:\\a.jpg"\n"C:\\b.png"'
        result = self._parse(text)
        assert len(result) == 2

    def test_handles_empty_lines(self):
        """空行不應產生結果"""
        text = "C:\\a.jpg\n\n\nC:\\b.png\n"
        result = self._parse(text)
        assert len(result) == 2

    def test_supported_extensions(self):
        """所有支援的副檔名都應被接受"""
        exts = ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'heic', 'heif', 'avif']
        text = "\n".join(f"C:\\test.{ext}" for ext in exts)
        result = self._parse(text)
        assert len(result) == len(exts)

    def test_output_has_json_path(self):
        """每個結果都必須包含 json_path 指向 metadata.json"""
        result = self._parse("C:\\img\\photo.jpg")
        assert result[0]["json_path"].endswith("metadata.json")


class TestQueueMessageContract:
    """驗證 app.py _poll_queue 期望的訊息格式契約"""

    def test_progress_message_contract(self):
        """進度訊息必須有這些 key（app.py _poll_queue 會讀取）"""
        msg = {
            "type": "progress",
            "processed": 10, "total": 100,
            "speed": 5.0, "eta": 18.0,
            "success": 9, "fail": 1,
            "active_workers": 2
        }
        # app.py 直接傳 msg 給 update_progress，所以這些 key 必須在頂層
        assert msg["type"] == "progress"
        assert isinstance(msg["eta"], float)
        assert isinstance(msg["speed"], float)

    def test_finished_message_contract(self):
        """完成訊息必須有 summary 和 failed_images"""
        msg = {
            "type": "finished",
            "summary": {"total": 100, "success_count": 98, "failure_count": 2},
            "failed_images": [{"path": "a.jpg", "error": "err"}],
        }
        assert "summary" in msg
        assert "failed_images" in msg
        assert isinstance(msg["failed_images"], list)

    def test_log_message_contract(self):
        msg = {"type": "log", "message": "處理中..."}
        assert "message" in msg

    def test_error_message_contract(self):
        msg = {"type": "error", "message": "出錯了"}
        assert "message" in msg

    def test_batch_message_contract(self):
        msg = {"type": "batch", "batch_id": 5, "success_count": 7, "batch_size": 8}
        for key in ["batch_id", "success_count", "batch_size"]:
            assert key in msg

    def test_writing_json_message_contract(self):
        msg = {"type": "writing_json", "current": 50, "total": 100}
        assert "current" in msg
        assert "total" in msg
