"""標籤備份與還原管理器

在執行 AI Tagger 之前備份每個素材的原始標籤，
支援一鍵還原到處理前的狀態。
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional


# 預設備份目錄（相對於專案根目錄）
DEFAULT_BACKUP_DIR = Path("backups")


class TagBackupManager:
    """標籤備份/還原管理器"""

    def __init__(self, backup_dir: Path = DEFAULT_BACKUP_DIR):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        image_data: List[Dict[str, str]],
        progress_callback=None,
    ) -> Path:
        """在處理前備份所有素材的原始標籤

        Args:
            image_data: [{'image_path': str, 'json_path': str}, ...]
            progress_callback: 進度回呼 callback(current, total)

        Returns:
            備份檔案路徑
        """
        backup = {}
        total = len(image_data)

        for i, item in enumerate(image_data):
            json_path = Path(item["json_path"])
            # 用 json_path 的父資料夾名稱作為 key（即 ITEM_ID.info）
            item_key = json_path.parent.name

            try:
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    backup[item_key] = {
                        "tags": data.get("tags", []),
                        "json_path": str(json_path),
                    }
                else:
                    # metadata.json 不存在，標記為無原始標籤
                    backup[item_key] = {
                        "tags": [],
                        "json_path": str(json_path),
                        "was_missing": True,
                    }
            except Exception as e:
                backup[item_key] = {
                    "tags": [],
                    "json_path": str(json_path),
                    "error": str(e),
                }

            if progress_callback and (i % 50 == 0 or i == total - 1):
                progress_callback(i + 1, total)

        # 寫入備份檔案
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        backup_file = self.backup_dir / f"tags_backup_{timestamp}.json"

        backup_data = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "item_count": len(backup),
            "items": backup,
        }

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        return backup_file

    def restore_backup(
        self,
        backup_path: Path,
        progress_callback=None,
    ) -> Dict[str, int]:
        """從備份檔案還原標籤

        Args:
            backup_path: 備份檔案路徑
            progress_callback: 進度回呼 callback(current, total)

        Returns:
            {"restored": int, "skipped": int, "errors": int}
        """
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        items = backup_data.get("items", {})
        total = len(items)
        stats = {"restored": 0, "skipped": 0, "errors": 0}

        for i, (item_key, item_info) in enumerate(items.items()):
            json_path = Path(item_info["json_path"])
            original_tags = item_info["tags"]
            was_missing = item_info.get("was_missing", False)

            try:
                if was_missing:
                    # 原本就沒有 metadata.json，如果現在有就刪除 tags
                    if json_path.exists():
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["tags"] = []
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False)
                    stats["restored"] += 1
                elif json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["tags"] = original_tags
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                    stats["restored"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                stats["errors"] += 1

            if progress_callback and (i % 50 == 0 or i == total - 1):
                progress_callback(i + 1, total)

        return stats

    def list_backups(self) -> List[Dict]:
        """列出所有可用的備份

        Returns:
            [{"path": Path, "created_at": str, "item_count": int}, ...]
        """
        backups = []
        for f in sorted(self.backup_dir.glob("tags_backup_*.json"), reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                backups.append({
                    "path": f,
                    "filename": f.name,
                    "created_at": data.get("created_at", "未知"),
                    "item_count": data.get("item_count", 0),
                })
            except Exception:
                continue
        return backups

    def delete_backup(self, backup_path: Path) -> bool:
        """刪除備份檔案"""
        try:
            backup_path.unlink()
            return True
        except Exception:
            return False
