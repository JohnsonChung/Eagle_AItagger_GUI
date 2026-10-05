"""發佈設定與中文字典偵測的回歸測試"""
import configparser
from pathlib import Path

from gui.frames.config_frame import ConfigFrame

ROOT = Path(__file__).resolve().parents[2]


class TestChineseColumnDetection:
    """「使用中文標籤」只在字典含 right_tag_cn 時可用"""

    def test_csv_with_chinese_column(self, tmp_path):
        p = tmp_path / "cn.csv"
        p.write_text("tag_id,name,category,count,right_tag_cn\n1,general,9,0,普通\n", encoding="utf-8")
        assert ConfigFrame.csv_has_chinese(str(p)) is True

    def test_csv_with_bom(self, tmp_path):
        p = tmp_path / "bom.csv"
        p.write_text("tag_id,name,category,count,right_tag_cn\n", encoding="utf-8-sig")
        assert ConfigFrame.csv_has_chinese(str(p)) is True

    def test_csv_without_chinese_column(self, tmp_path):
        p = tmp_path / "en.csv"
        p.write_text("tag_id,name,category,count\n1,general,9,0\n", encoding="utf-8")
        assert ConfigFrame.csv_has_chinese(str(p)) is False

    def test_missing_file(self, tmp_path):
        assert ConfigFrame.csv_has_chinese(str(tmp_path / "nope.csv")) is False

    def test_bundled_cn_dictionary_supports_chinese(self):
        assert ConfigFrame.csv_has_chinese(str(ROOT / "csv" / "Tags-cn_2024_ver-1.0.csv"))


class TestReleaseDefaultConfig:
    """build/config.default.ini 必須是可攜的相對路徑"""

    def _load(self):
        parser = configparser.ConfigParser()
        parser.read(ROOT / "build" / "config.default.ini", encoding="utf-8")
        return parser

    def test_model_paths_are_relative(self):
        parser = self._load()
        for key in ("model_path", "tags_path"):
            value = parser.get("Model", key)
            assert not Path(value).is_absolute(), f"{key} 不可為絕對路徑: {value}"
            assert ":" not in value, f"{key} 不可含磁碟代號: {value}"

    def test_default_tags_file_is_bundled(self):
        tags = self._load().get("Model", "tags_path")
        assert (ROOT / Path(tags.replace("\\", "/"))).exists()

    def test_chinese_flag_consistent_with_dictionary(self):
        parser = self._load()
        if parser.getboolean("Tag", "use_chinese_name"):
            tags = parser.get("Model", "tags_path").replace("\\", "/")
            assert ConfigFrame.csv_has_chinese(str(ROOT / tags))
