"""模型驗證工具

提供輕量級的模型可用性測試：
1. 檔案存在性
2. onnxruntime 能否載入
3. 能否用空白圖完成一次推理
4. 標籤 CSV 數量是否與模型輸出匹配
"""
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelTestResult:
    """模型測試結果"""
    success: bool
    model_path: str
    tags_path: str
    provider: str = ""           # 實際使用的 execution provider
    input_shape: str = ""        # 模型輸入尺寸
    output_count: int = 0        # 模型輸出標籤數
    tags_count: int = 0          # CSV 標籤數
    inference_time_ms: float = 0 # 推理耗時
    error: str = ""              # 錯誤訊息


def test_model(model_path: str, tags_path: str) -> ModelTestResult:
    """測試模型是否可用

    Args:
        model_path: .onnx 模型檔案路徑
        tags_path: 標籤 CSV 檔案路徑

    Returns:
        ModelTestResult 包含測試結果
    """
    result = ModelTestResult(
        success=False,
        model_path=model_path,
        tags_path=tags_path,
    )

    # 1. 檔案存在
    if not Path(model_path).exists():
        result.error = f"模型檔案不存在: {model_path}"
        return result

    if not Path(tags_path).exists():
        result.error = f"標籤檔案不存在: {tags_path}"
        return result

    # 2. 載入模型
    try:
        from onnxruntime import InferenceSession
        session = InferenceSession(
            str(model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
    except Exception as e:
        result.error = f"模型載入失敗: {e}"
        return result

    # 取得實際 provider
    result.provider = session.get_providers()[0] if session.get_providers() else "unknown"

    # 3. 取得輸入形狀
    try:
        input_info = session.get_inputs()[0]
        input_shape = input_info.shape  # e.g. [1, 448, 448, 3]
        result.input_shape = str(input_shape)
        target_size = input_shape[1]  # 448 or 224
    except Exception as e:
        result.error = f"無法讀取模型輸入格式: {e}"
        return result

    # 4. 載入標籤 CSV
    try:
        import pandas as pd
        tags_df = pd.read_csv(tags_path)
        result.tags_count = len(tags_df)
    except Exception as e:
        result.error = f"標籤 CSV 讀取失敗: {e}"
        return result

    # 5. 用空白圖推理
    try:
        import numpy as np

        # 建立空白測試圖（白色）
        dummy = np.ones((1, target_size, target_size, 3), dtype=np.float32)

        input_name = input_info.name
        output_name = session.get_outputs()[0].name

        start = time.perf_counter()
        confs = session.run([output_name], {input_name: dummy})[0][0]
        elapsed = time.perf_counter() - start

        result.inference_time_ms = round(elapsed * 1000, 1)
        result.output_count = len(confs)
    except Exception as e:
        result.error = f"推理失敗: {e}"
        return result
    finally:
        del session

    # 6. 驗證標籤數量匹配
    if result.output_count != result.tags_count:
        result.error = (
            f"模型輸出 {result.output_count} 個標籤，"
            f"但 CSV 有 {result.tags_count} 個標籤，不匹配"
        )
        return result

    result.success = True
    return result
