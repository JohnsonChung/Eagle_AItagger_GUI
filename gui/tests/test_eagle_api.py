"""Eagle API 客戶端測試 — 使用 mock 模擬所有 HTTP 請求"""
import pytest
from unittest.mock import MagicMock, patch
from gui.eagle_api import EagleAPI, EagleLibraryInfo


def _mock_response(json_data, status_code=200):
    """建立模擬的 requests.Response"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestIsAvailable:
    """Eagle 連線偵測測試"""

    @patch("gui.eagle_api.requests.get")
    def test_returns_true_when_running(self, mock_get):
        mock_get.return_value = _mock_response({"status": "success"})
        api = EagleAPI()
        assert api.is_available() is True

    @patch("gui.eagle_api.requests.get")
    def test_returns_false_when_not_running(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("refused")
        api = EagleAPI()
        assert api.is_available() is False


class TestGetLibraryInfo:
    """資源庫資訊查詢測試"""

    @patch("gui.eagle_api.requests.get")
    def test_returns_correct_fields(self, mock_get):
        mock_get.return_value = _mock_response({
            "status": "success",
            "data": {"library": {"name": "Download", "path": "C:\\Eagle\\Download.library"}}
        })
        api = EagleAPI()
        info = api.get_library_info()
        assert info.name == "Download"
        assert info.path == "C:\\Eagle\\Download.library"


class TestGetLibraryHistory:
    """資源庫歷史列表測試"""

    @patch("gui.eagle_api.requests.get")
    def test_deduplicates_trailing_slashes(self, mock_get):
        """帶/不帶結尾斜線的相同路徑應去重"""
        mock_get.return_value = _mock_response({
            "status": "success",
            "data": [
                "C:\\Eagle\\lib1.library",
                "C:\\Eagle\\lib1.library\\",
                "C:\\Eagle\\lib2.library",
            ]
        })
        api = EagleAPI()
        history = api.get_library_history()
        assert len(history) == 2
        paths = [lib.path for lib in history]
        assert "C:\\Eagle\\lib1.library" in paths
        assert "C:\\Eagle\\lib2.library" in paths

    @patch("gui.eagle_api.requests.get")
    def test_extracts_name_from_path(self, mock_get):
        """從路徑中正確擷取資源庫名稱"""
        mock_get.return_value = _mock_response({
            "status": "success",
            "data": ["C:\\Eagle\\Download.library"]
        })
        api = EagleAPI()
        history = api.get_library_history()
        assert history[0].name == "Download"


class TestGetAllItems:
    """素材取得與篩選測試"""

    @patch("gui.eagle_api.requests.get")
    def test_uses_large_limit_not_200(self, mock_get):
        """驗證使用 limit=999999 而非分頁的 200（修復 Eagle offset bug）"""
        # 第一次呼叫: get_library_info, 第二次: item/list
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "Test", "path": "C:\\test.library"}}}),
            _mock_response({"status": "success", "data": []}),
        ]
        api = EagleAPI()
        api.get_all_items()
        # 檢查第二次呼叫（item/list）的 params
        item_call = mock_get.call_args_list[1]
        assert item_call.kwargs["params"]["limit"] == 999999

    @patch("gui.eagle_api.requests.get")
    def test_filters_by_extension(self, mock_get):
        """副檔名篩選：只回傳 jpg，排除 mp4"""
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "T", "path": "C:\\t.library"}}}),
            _mock_response({"status": "success", "data": [
                {"id": "1", "name": "a", "ext": "jpg", "tags": []},
                {"id": "2", "name": "b", "ext": "mp4", "tags": []},
            ]}),
        ]
        api = EagleAPI()
        items = api.get_all_items(extensions=["jpg"])
        assert len(items) == 1
        assert items[0]["ext"] == "jpg"

    @patch("gui.eagle_api.requests.get")
    def test_filters_by_require_no_tag(self, mock_get):
        """排除已有 AITagger_ed 標籤的素材（底線版本）"""
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "T", "path": "C:\\t.library"}}}),
            _mock_response({"status": "success", "data": [
                {"id": "1", "name": "a", "ext": "jpg", "tags": []},
                {"id": "2", "name": "b", "ext": "jpg", "tags": ["AITagger_ed"]},
            ]}),
        ]
        api = EagleAPI()
        items = api.get_all_items(require_no_tag="AITagger_ed")
        assert len(items) == 1
        assert items[0]["id"] == "1"

    @patch("gui.eagle_api.requests.get")
    def test_filters_by_require_no_tag_space_variant(self, mock_get):
        """排除 'AITagger ed'（空格版本）— replace_underscore 會把 _ 變空格"""
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "T", "path": "C:\\t.library"}}}),
            _mock_response({"status": "success", "data": [
                {"id": "1", "name": "a", "ext": "jpg", "tags": []},
                {"id": "2", "name": "b", "ext": "jpg", "tags": ["AITagger ed"]},
            ]}),
        ]
        api = EagleAPI()
        # 傳入底線版本，應該也能過濾掉空格版本
        items = api.get_all_items(require_no_tag="AITagger_ed")
        assert len(items) == 1
        assert items[0]["id"] == "1"

    @patch("gui.eagle_api.requests.get")
    def test_returns_all_without_filters(self, mock_get):
        """無篩選條件時回傳所有素材"""
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "T", "path": "C:\\t.library"}}}),
            _mock_response({"status": "success", "data": [
                {"id": "1", "name": "a", "ext": "jpg", "tags": []},
                {"id": "2", "name": "b", "ext": "png", "tags": []},
            ]}),
        ]
        api = EagleAPI()
        items = api.get_all_items()
        assert len(items) == 2


class TestItemsToImageData:
    """素材列表轉換格式測試"""

    def test_output_has_required_keys(self):
        """輸出必須包含 image_path 和 json_path"""
        api = EagleAPI()
        items = [{"_image_path": "C:\\a.jpg", "_json_path": "C:\\metadata.json"}]
        data = api.items_to_image_data(items)
        assert len(data) == 1
        assert "image_path" in data[0]
        assert "json_path" in data[0]

    @patch("gui.eagle_api.requests.get")
    def test_path_follows_eagle_structure(self, mock_get):
        """路徑格式: {lib_path}/images/{id}.info/{name}.{ext}"""
        mock_get.side_effect = [
            _mock_response({"status": "success", "data": {"library": {"name": "T", "path": "C:\\test.library"}}}),
            _mock_response({"status": "success", "data": [
                {"id": "ABC123", "name": "photo", "ext": "jpg", "tags": []},
            ]}),
        ]
        api = EagleAPI()
        items = api.get_all_items()
        data = api.items_to_image_data(items)
        assert "ABC123.info" in data[0]["image_path"]
        assert "photo.jpg" in data[0]["image_path"]
        assert "metadata.json" in data[0]["json_path"]


class TestSwitchLibrary:
    """資源庫切換測試"""

    @patch("gui.eagle_api.requests.post")
    def test_switch_success(self, mock_post):
        mock_post.return_value = _mock_response({"status": "success"})
        api = EagleAPI()
        assert api.switch_library("C:\\test.library") is True

    @patch("gui.eagle_api.requests.post")
    def test_switch_failure(self, mock_post):
        mock_post.return_value = _mock_response({"status": "error"})
        api = EagleAPI()
        assert api.switch_library("C:\\test.library") is False

    @patch("gui.eagle_api.requests.post")
    def test_switch_connection_error(self, mock_post):
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError("refused")
        api = EagleAPI()
        assert api.switch_library("C:\\test.library") is False


class TestGetFoldersFlat:
    """資料夾扁平化測試"""

    @patch("gui.eagle_api.requests.get")
    def test_flattens_nested_structure(self, mock_get):
        mock_get.return_value = _mock_response({
            "status": "success",
            "data": [{
                "id": "f1", "name": "Parent",
                "children": [{"id": "f2", "name": "Child", "children": []}]
            }]
        })
        api = EagleAPI()
        folders = api.get_folders_flat()
        assert len(folders) == 2
        assert folders[0].name == "Parent"
        assert "Child" in folders[1].name
