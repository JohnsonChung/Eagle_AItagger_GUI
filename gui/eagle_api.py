"""Eagle 本地 API 客戶端

透過 Eagle 的本地 REST API (localhost:41595) 與 Eagle 互動。
需要 Eagle 應用程式正在運行。
"""
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


# Eagle API 預設位址
EAGLE_API_BASE = "http://localhost:41595"


@dataclass
class EagleFolder:
    """Eagle 資料夾"""
    id: str
    name: str
    children: List['EagleFolder'] = field(default_factory=list)

    def __str__(self):
        return self.name


@dataclass
class EagleLibraryInfo:
    """Eagle 資源庫資訊"""
    name: str
    path: str


class EagleAPIError(Exception):
    """Eagle API 呼叫失敗"""
    pass


class EagleAPI:
    """Eagle 本地 API 客戶端"""

    def __init__(self, base_url: str = EAGLE_API_BASE, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def is_available(self) -> bool:
        """檢查 Eagle API 是否可用（Eagle 是否正在運行）"""
        try:
            r = requests.get(
                f"{self.base_url}/api/application/info",
                timeout=3
            )
            return r.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def get_library_info(self) -> EagleLibraryInfo:
        """獲取當前開啟的資源庫資訊"""
        data = self._get("/api/library/info")
        lib = data.get("library", {})
        return EagleLibraryInfo(
            name=lib.get("name", "未知"),
            path=lib.get("path", "")
        )

    def get_folders(self) -> List[EagleFolder]:
        """獲取資料夾列表（含巢狀結構）"""
        data = self._get("/api/folder/list")
        return self._parse_folders(data)

    def get_folders_flat(self) -> List[EagleFolder]:
        """獲取扁平化的資料夾列表（用於下拉選單）"""
        folders = self.get_folders()
        flat = []
        self._flatten_folders(folders, flat, depth=0)
        return flat

    def get_items(
        self,
        limit: int = 200,
        offset: int = 0,
        folders: Optional[List[str]] = None,
        ext: Optional[str] = None,
        tags: Optional[List[str]] = None,
        order_by: str = "CREATEDATE",
    ) -> List[Dict[str, Any]]:
        """獲取素材列表

        Args:
            limit: 每次請求的數量上限
            offset: 偏移量（分頁）
            folders: 資料夾 ID 列表（篩選）
            ext: 副檔名篩選（如 "jpg"）
            tags: 標籤篩選
            order_by: 排序方式

        Returns:
            素材列表，每項包含 id, name, ext, tags, folders 等欄位
        """
        params = {
            "limit": limit,
            "offset": offset,
            "orderBy": order_by,
        }
        if folders:
            params["folders"] = ",".join(folders)
        if ext:
            params["ext"] = ext
        if tags:
            params["tags"] = ",".join(tags)

        return self._get("/api/item/list", params=params)

    def get_all_items(
        self,
        folder_id: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        require_no_tag: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """獲取所有符合條件的素材

        注意: Eagle API 的 offset 分頁功能有問題（offset>0 回傳空），
        因此改用單次大 limit 請求一次取回所有素材，再在本地篩選。

        Args:
            folder_id: 限定資料夾 ID（None 表示全部）
            extensions: 限定副檔名列表
            exclude_tags: 排除包含這些標籤的素材
            require_no_tag: 只匯入不包含此標籤的素材
            progress_callback: 進度回呼 callback(fetched_count)

        Returns:
            過濾後的素材列表
        """
        lib_info = self.get_library_info()

        # Eagle API 的 offset 分頁有 bug，改用大 limit 一次拉完
        params = {
            "limit": 999999,
            "orderBy": "CREATEDATE",
        }
        if folder_id:
            params["folders"] = folder_id

        if progress_callback:
            progress_callback(0)

        raw_items = self._get("/api/item/list", params=params)
        if not raw_items:
            return []

        # 本地篩選
        all_items = []
        for item in raw_items:
            # 副檔名篩選
            item_ext = item.get("ext", "").lower()
            if extensions and item_ext not in extensions:
                continue

            # 標籤篩選
            item_tags = item.get("tags", [])

            # 排除包含特定標籤的素材
            if exclude_tags:
                if any(t in item_tags for t in exclude_tags):
                    continue

            # 只匯入不包含特定標籤的素材
            # 注意: config 的 replace_underscore 會把 _ 換成空格,
            # 所以 "AITagger_ed" 實際可能存為 "AITagger ed"，需同時比對兩種
            if require_no_tag:
                tag_variants = {require_no_tag, require_no_tag.replace("_", " ")}
                if tag_variants & set(item_tags):
                    continue

            # 構建檔案路徑
            item_id = item.get("id", "")
            item_name = item.get("name", "")
            item_folder = Path(lib_info.path) / "images" / f"{item_id}.info"
            image_file = item_folder / f"{item_name}.{item_ext}"

            item["_image_path"] = str(image_file)
            item["_json_path"] = str(item_folder / "metadata.json")
            item["_library_path"] = lib_info.path

            all_items.append(item)

        if progress_callback:
            progress_callback(len(all_items))

        return all_items

    def items_to_image_data(self, items: List[Dict]) -> List[Dict[str, str]]:
        """將 Eagle API 的素材列表轉換為 backend 需要的 image_data 格式

        Returns:
            [{'image_path': str, 'json_path': str}, ...]
        """
        return [
            {
                "image_path": item["_image_path"],
                "json_path": item["_json_path"],
            }
            for item in items
            if "_image_path" in item
        ]

    def get_library_history(self) -> List[EagleLibraryInfo]:
        """獲取所有歷史資源庫列表（去重）"""
        data = self._get("/api/library/history")
        seen = set()
        libraries = []
        for raw_path in data:
            path = raw_path.rstrip("\\").rstrip("/")
            if path in seen:
                continue
            seen.add(path)
            name = Path(path).stem.replace(".library", "")
            libraries.append(EagleLibraryInfo(name=name, path=path))
        return libraries

    def switch_library(self, library_path: str) -> bool:
        """切換 Eagle 的當前資源庫

        Args:
            library_path: 資源庫完整路徑

        Returns:
            是否切換成功
        """
        try:
            r = requests.post(
                f"{self.base_url}/api/library/switch",
                json={"libraryPath": library_path},
                timeout=30,  # 切換資源庫可能需要較長時間
            )
            r.raise_for_status()
            body = r.json()
            return body.get("status") == "success"
        except Exception:
            return False

    # --- 私有方法 ---

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """發送 GET 請求"""
        try:
            r = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=self.timeout,
            )
            r.raise_for_status()
            body = r.json()
            if body.get("status") == "success":
                return body.get("data", {})
            else:
                raise EagleAPIError(f"API 回傳錯誤: {body}")
        except requests.ConnectionError:
            raise EagleAPIError("無法連接 Eagle，請確認 Eagle 已啟動")
        except requests.Timeout:
            raise EagleAPIError("Eagle API 回應逾時")

    def _parse_folders(self, data: list) -> List[EagleFolder]:
        """解析巢狀資料夾結構"""
        result = []
        for f in data:
            folder = EagleFolder(
                id=f.get("id", ""),
                name=f.get("name", ""),
                children=self._parse_folders(f.get("children", []))
            )
            result.append(folder)
        return result

    def _flatten_folders(
        self,
        folders: List[EagleFolder],
        flat: List[EagleFolder],
        depth: int = 0
    ):
        """將巢狀資料夾扁平化，名稱加上縮排前綴"""
        for f in folders:
            indent = "  " * depth
            flat_folder = EagleFolder(
                id=f.id,
                name=f"{indent}{f.name}" if depth > 0 else f.name,
            )
            flat.append(flat_folder)
            if f.children:
                self._flatten_folders(f.children, flat, depth + 1)
