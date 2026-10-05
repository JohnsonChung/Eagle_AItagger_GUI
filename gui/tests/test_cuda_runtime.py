"""CUDA / cuDNN 定位測試（不需 GPU，以暫存目錄模擬安裝位置）"""
import os

import pytest

import gui.cuda_runtime as cr


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    """清空 CUDA 相關環境變數，並把 Program Files 指向暫存目錄"""
    for key in list(os.environ):
        if key.upper().startswith("CUDA_PATH"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(cr, "_PROGRAM_FILES", str(tmp_path))
    return tmp_path


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_not_found(fake_env):
    assert cr.find_dll(cr.CUDA_MARKER_DLL) is None
    assert cr.find_dll(cr.CUDNN_MARKER_DLL) is None


def test_cuda_toolkit_default_location(fake_env):
    d = fake_env / "NVIDIA GPU Computing Toolkit" / "CUDA" / "v12.9" / "bin"
    _touch(d / cr.CUDA_MARKER_DLL)
    assert cr.find_dll(cr.CUDA_MARKER_DLL) == d


def test_cudnn_installer_location_not_on_path(fake_env):
    """cuDNN 9 官方安裝程式的位置預設不在 PATH，必須能找到"""
    d = fake_env / "NVIDIA" / "CUDNN" / "v9.10" / "bin" / "12.9"
    _touch(d / cr.CUDNN_MARKER_DLL)
    assert cr.find_dll(cr.CUDNN_MARKER_DLL) == d


def test_cuda_path_env(fake_env, monkeypatch):
    root = fake_env / "custom_cuda"
    _touch(root / "bin" / cr.CUDA_MARKER_DLL)
    monkeypatch.setenv("CUDA_PATH", str(root))
    assert cr.find_dll(cr.CUDA_MARKER_DLL) == root / "bin"


def test_cuda_11_is_ignored(fake_env):
    """CUDA 11 目錄不符合 onnxruntime-gpu 1.2x 需求"""
    d = fake_env / "NVIDIA GPU Computing Toolkit" / "CUDA" / "v11.8" / "bin"
    _touch(d / "cublasLt64_11.dll")
    assert cr.find_dll(cr.CUDA_MARKER_DLL) is None


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_register_adds_to_path(fake_env):
    d = fake_env / "NVIDIA" / "CUDNN" / "v9.10" / "bin" / "12.9"
    _touch(d / cr.CUDNN_MARKER_DLL)
    registered = cr.register_cuda_dll_dirs()
    assert d in registered
    assert str(d) in os.environ["PATH"].split(os.pathsep)
