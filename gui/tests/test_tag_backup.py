"""標籤備份/還原測試"""
import json
import pytest
from pathlib import Path
from gui.tag_backup import TagBackupManager


@pytest.fixture
def backup_mgr(tmp_path):
    """使用臨時目錄的 TagBackupManager"""
    return TagBackupManager(backup_dir=tmp_path / "backups")


@pytest.fixture
def sample_metadata(tmp_path):
    """建立模擬的 metadata.json 檔案"""
    items = []
    for i in range(3):
        item_dir = tmp_path / "images" / f"ITEM{i}.info"
        item_dir.mkdir(parents=True, exist_ok=True)
        json_path = item_dir / "metadata.json"
        original_tags = [f"tag_{i}_a", f"tag_{i}_b"]
        json_path.write_text(
            json.dumps({"tags": original_tags}, ensure_ascii=False),
            encoding="utf-8"
        )
        items.append({
            "image_path": str(item_dir / f"photo{i}.jpg"),
            "json_path": str(json_path),
            "_original_tags": original_tags,  # 方便測試驗證
        })
    return items


class TestCreateBackup:
    """備份建立測試"""

    def test_creates_backup_file(self, backup_mgr, sample_metadata):
        path = backup_mgr.create_backup(sample_metadata)
        assert path.exists()
        assert path.suffix == ".json"

    def test_backup_contains_original_tags(self, backup_mgr, sample_metadata):
        path = backup_mgr.create_backup(sample_metadata)
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["items"]
        assert len(items) == 3
        # 驗證標籤內容正確
        for key, info in items.items():
            assert "tags" in info
            assert len(info["tags"]) == 2

    def test_backup_records_item_count(self, backup_mgr, sample_metadata):
        path = backup_mgr.create_backup(sample_metadata)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["item_count"] == 3

    def test_handles_missing_metadata(self, backup_mgr, tmp_path):
        """metadata.json 不存在時應標記 was_missing"""
        items = [{"image_path": "x.jpg", "json_path": str(tmp_path / "nonexist" / "metadata.json")}]
        path = backup_mgr.create_backup(items)
        data = json.loads(path.read_text(encoding="utf-8"))
        item = list(data["items"].values())[0]
        assert item["was_missing"] is True
        assert item["tags"] == []

    def test_progress_callback_called(self, backup_mgr, sample_metadata):
        calls = []
        backup_mgr.create_backup(sample_metadata, progress_callback=lambda c, t: calls.append((c, t)))
        assert len(calls) > 0
        assert calls[-1] == (3, 3)


class TestRestoreBackup:
    """備份還原測試"""

    def test_restores_original_tags(self, backup_mgr, sample_metadata):
        """還原後標籤應回到備份時的狀態"""
        # 備份
        backup_path = backup_mgr.create_backup(sample_metadata)

        # 模擬 AI Tagger 修改標籤
        for item in sample_metadata:
            jp = Path(item["json_path"])
            data = json.loads(jp.read_text(encoding="utf-8"))
            data["tags"] = ["ai_tag_1", "ai_tag_2", "ai_tag_3"]
            jp.write_text(json.dumps(data), encoding="utf-8")

        # 還原
        stats = backup_mgr.restore_backup(backup_path)
        assert stats["restored"] == 3
        assert stats["errors"] == 0

        # 驗證標籤已還原
        for item in sample_metadata:
            jp = Path(item["json_path"])
            data = json.loads(jp.read_text(encoding="utf-8"))
            assert data["tags"] == item["_original_tags"]

    def test_restore_returns_stats(self, backup_mgr, sample_metadata):
        backup_path = backup_mgr.create_backup(sample_metadata)
        stats = backup_mgr.restore_backup(backup_path)
        assert "restored" in stats
        assert "skipped" in stats
        assert "errors" in stats


class TestListBackups:
    """備份列表測試"""

    def test_lists_backups_sorted_desc(self, backup_mgr, sample_metadata):
        import time
        backup_mgr.create_backup(sample_metadata)
        time.sleep(1.1)  # 確保時間戳不同（精度到秒）
        backup_mgr.create_backup(sample_metadata)
        backups = backup_mgr.list_backups()
        assert len(backups) == 2
        # 最新的在前
        assert backups[0]["created_at"] >= backups[1]["created_at"]

    def test_empty_when_no_backups(self, backup_mgr):
        assert backup_mgr.list_backups() == []

    def test_backup_info_has_required_fields(self, backup_mgr, sample_metadata):
        backup_mgr.create_backup(sample_metadata)
        backups = backup_mgr.list_backups()
        b = backups[0]
        assert "path" in b
        assert "created_at" in b
        assert "item_count" in b


class TestDeleteBackup:
    """備份刪除測試"""

    def test_deletes_backup_file(self, backup_mgr, sample_metadata):
        path = backup_mgr.create_backup(sample_metadata)
        assert path.exists()
        assert backup_mgr.delete_backup(path) is True
        assert not path.exists()
