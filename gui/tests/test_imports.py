"""模組匯入相容性測試 — 捕捉跨模組命名不一致"""
import pytest
import importlib
import os


class TestAppImports:
    """驗證 app.py 的 import 能找到正確的類別名稱"""

    def test_imports_env_checker_window(self):
        """app.py import EnvCheckerWindow（不是 EnvironmentChecker）"""
        from gui.env_checker import EnvCheckerWindow
        assert EnvCheckerWindow is not None

    def test_imports_backend_controller(self):
        from gui.backend import BackendController
        assert BackendController is not None

    def test_imports_all_frames(self):
        from gui.frames.config_frame import ConfigFrame
        from gui.frames.image_list_frame import ImageListFrame
        from gui.frames.progress_frame import ProgressFrame
        from gui.frames.result_frame import ResultFrame
        assert all([ConfigFrame, ImageListFrame, ProgressFrame, ResultFrame])


class TestEnvChecksImports:
    """驗證 env_checks 模組導出名稱正確"""

    def test_imports_via_init(self):
        """透過 __init__.py 匯入所有檢查類別"""
        from gui.env_checks import (
            PythonCheck, GPUCheck, CUDACheck, CUDNNCheck,
            VCRedistCheck, ModelCheck, DepsCheck, CheckResult
        )
        assert all([PythonCheck, GPUCheck, CUDACheck, CUDNNCheck,
                     VCRedistCheck, ModelCheck, DepsCheck, CheckResult])

    def test_all_inherit_base_check(self):
        from gui.env_checks.base import BaseCheck
        from gui.env_checks import (
            PythonCheck, GPUCheck, CUDACheck, CUDNNCheck,
            VCRedistCheck, ModelCheck, DepsCheck
        )
        for cls in [PythonCheck, GPUCheck, CUDACheck, CUDNNCheck,
                     VCRedistCheck, ModelCheck, DepsCheck]:
            assert issubclass(cls, BaseCheck), f"{cls.__name__} 未繼承 BaseCheck"


class TestAllGuiModulesImportable:
    """遞迴匯入 gui/ 下所有 .py 檔案，確保無 SyntaxError"""

    def test_no_import_errors(self):
        gui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        errors = []
        for root, dirs, files in os.walk(gui_dir):
            if 'tests' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    rel = os.path.relpath(os.path.join(root, file), start=os.path.dirname(gui_dir))
                    module_name = rel.replace(os.sep, '.')[:-3]
                    try:
                        importlib.import_module(module_name)
                    except Exception as e:
                        errors.append(f"{module_name}: {e}")
        assert not errors, f"匯入失敗:\n" + "\n".join(errors)


class TestEagleApiImports:
    """驗證 Eagle API 模組匯入"""

    def test_imports_eagle_api(self):
        from gui.eagle_api import EagleAPI, EagleLibraryInfo, EagleFolder
        assert all([EagleAPI, EagleLibraryInfo, EagleFolder])

    def test_imports_log_console(self):
        from gui.widgets.log_console import LogConsole
        assert LogConsole is not None
