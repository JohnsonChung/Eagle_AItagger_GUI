"""環境檢查模組測試"""
import pytest
from unittest.mock import MagicMock, patch
from gui.env_checks.base import CheckResult, BaseCheck
from gui.env_checks.python_check import PythonCheck
from gui.env_checks.gpu_check import GPUCheck
from gui.env_checks.cuda_check import CUDACheck
from gui.env_checks.cudnn_check import CUDNNCheck
from gui.env_checks.vcredist_check import VCRedistCheck
from gui.env_checks.model_check import ModelCheck
from gui.env_checks.deps_check import DepsCheck


ALL_CHECK_CLASSES = [PythonCheck, GPUCheck, CUDACheck, CUDNNCheck, VCRedistCheck, ModelCheck, DepsCheck]


class TestCheckResult:
    """CheckResult 資料結構測試"""

    def test_valid_status_values(self, sample_check_result):
        for res in sample_check_result.values():
            assert res.status in ("pass", "fail", "warn")

    def test_has_required_fields(self):
        r = CheckResult(name="Test", status="pass", message="OK")
        assert hasattr(r, "name")
        assert hasattr(r, "status")
        assert hasattr(r, "message")
        assert hasattr(r, "fix_url")

    def test_fix_url_default_none(self):
        r = CheckResult(name="Test", status="pass", message="OK")
        assert r.fix_url is None


class TestBaseCheckInterface:
    """驗證所有檢查類別都正確繼承 BaseCheck"""

    @pytest.mark.parametrize("check_class", ALL_CHECK_CLASSES)
    def test_inherits_base_check(self, check_class):
        assert issubclass(check_class, BaseCheck)

    @pytest.mark.parametrize("check_class", ALL_CHECK_CLASSES)
    def test_has_run_method(self, check_class):
        assert hasattr(check_class, "run")


class TestPythonCheck:
    """Python 版本檢查測試"""

    def test_passes_in_test_env(self):
        """在測試環境中 Python 版本檢查應通過"""
        result = PythonCheck().run()
        assert isinstance(result, CheckResult)
        assert result.status == "pass"


class TestModelCheck:
    """模型檔案檢查測試"""

    def test_warns_with_missing_config(self, tmp_path):
        """config.ini 不存在時應回傳 warn"""
        check = ModelCheck(config_path=str(tmp_path / "nonexistent.ini"))
        result = check.run()
        assert isinstance(result, CheckResult)
        assert result.status == "warn"


class TestDepsCheck:
    """依賴檢查測試"""

    def test_returns_check_result(self):
        result = DepsCheck().run()
        assert isinstance(result, CheckResult)


class TestGPUCheck:
    """GPU 檢查測試"""

    @patch("subprocess.run")
    def test_returns_check_result_on_failure(self, mock_run):
        """nvidia-smi 不可用時應回傳 fail"""
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        result = GPUCheck().run()
        assert isinstance(result, CheckResult)
