# gui/ — Eagle AI Tagger 圖形介面

> 基於 customtkinter 的桌面 GUI，替代原始 CLI (`main/mainp.py`)，提供完整的圖形化操作流程。

## 架構總覽

```
gui_main.py          ← 入口（freeze_support + CWD 修正）
│
├── app.py           ← EagleTaggerApp 主視窗，sidebar 導航 + queue 輪詢
│   ├── frames/
│   │   ├── config_frame.py       設定面板（模型路徑、標籤參數）
│   │   ├── image_list_frame.py   圖片清單（Eagle API 匯入 / 貼上 / 載入檔案）
│   │   ├── progress_frame.py     即時進度（進度條、速度、ETA）
│   │   └── result_frame.py       結果報告 + 標籤還原
│   │
│   ├── backend.py                推理控制器（背景執行緒）
│   ├── eagle_api.py              Eagle REST API 客戶端
│   ├── tag_backup.py             標籤備份 / 還原管理器
│   ├── env_checker.py            環境檢查視窗
│   │
│   ├── env_checks/               7 個環境檢查模組
│   │   ├── base.py               CheckResult + BaseCheck ABC
│   │   ├── python_check.py       Python 版本
│   │   ├── gpu_check.py          NVIDIA GPU
│   │   ├── cuda_check.py         CUDA 版本
│   │   ├── cudnn_check.py        cuDNN
│   │   ├── vcredist_check.py     VC Redistributable
│   │   ├── model_check.py        模型檔案（支援 GUI 即時路徑）
│   │   └── deps_check.py         Python 依賴套件
│   │
│   └── widgets/
│       └── log_console.py        日誌文字框（500 行上限）
│
└── tests/                        83 個自動化測試
```

## 執行緒模型

```
┌──────────────────────┐     queue.Queue      ┌───────────────────────┐
│    GUI 主執行緒       │◄────────────────────│   Backend 執行緒       │
│                      │                      │                       │
│  customtkinter       │  flat dict 訊息      │  BackendController    │
│  mainloop()          │  (每 100ms 輪詢)     │  ._run()              │
│                      │                      │                       │
│  app._poll_queue()   │                      │  TaskDispatcher       │
│  progress_frame      │                      │  ProcessPoolManager   │
│  result_frame        │                      │  ResultCollector      │
└──────────────────────┘                      └───────────────────────┘
```

**重要規則：**
- GUI 主執行緒只做 UI 更新，不做任何阻塞操作
- 所有推理、Eagle API 呼叫、標籤備份/還原都在背景執行緒
- 執行緒間通訊只用 `queue.Queue`，不用 shared state

## Queue 訊息契約

Backend → GUI 的所有訊息都是 **flat dict**（不可嵌套 `data` key）：

```python
# 進度
{'type': 'progress', 'processed': int, 'total': int,
 'speed': float, 'eta': float,        # eta 必須是 float 秒數
 'success': int, 'fail': int, 'active_workers': int}

# 日誌
{'type': 'log', 'message': str}

# 批次完成
{'type': 'batch', 'batch_id': int, 'success_count': int, 'batch_size': int}

# JSON 寫入進度
{'type': 'writing_json', 'current': int, 'total': int}

# 完成
{'type': 'finished', 'summary': dict, 'failed_images': list}

# 錯誤
{'type': 'error', 'message': str}
```

## Eagle API 注意事項

| 事項 | 說明 |
|:---|:---|
| offset 分頁 | **壞的**，不可使用。改用 `limit=999999` 一次取回 |
| AITagger_ed 標籤 | `replace_underscore=True` 時存為 `AITagger ed`（空格），篩選需比對兩種變體 |
| 資源庫切換 | `POST /api/library/switch` 會同時切換 Eagle UI |
| 連線 | `localhost:41595`，不需認證，Eagle 必須開啟 |

## 標籤備份機制

```
執行前自動備份 → backups/tags_backup_YYYY-MM-DD_HHMMSS.json
                 {"items": {"ITEM_ID.info": {"tags": [...], "json_path": "..."}}}

結果頁面「還原」按鈕 → 讀取備份 → 寫回 metadata.json
```

## 已知地雷

1. **不要在測試中建立 CTk 視窗** — 會卡住。用純資料流驗證
2. **不要 import `main.mainp`** — 裡面有 `input()` 會阻塞
3. **`main/` 目錄不可修改** — 上游原始碼，修改會破壞 merge
4. **`ResultCollector.get_summary()`** 回傳 `success_count` / `failure_count`，不是 `successful_images`
5. **ETA 必須是 `float`** — ProgressFrame 自行格式化為 mm:ss
6. **PyInstaller frozen 模式** — `sys.executable` 是 exe 路徑，`__file__` 在 `_internal/` 裡

## 修改指引

### 新增 GUI 面板
1. 在 `frames/` 建立 `xxx_frame.py`，繼承 `ctk.CTkFrame`
2. 在 `app.py` 的 `_create_frames()` 註冊
3. 在 sidebar 加按鈕

### 新增環境檢查
1. 在 `env_checks/` 建立 `xxx_check.py`，繼承 `BaseCheck`
2. 實作 `run() -> CheckResult`
3. 在 `env_checks/__init__.py` 加入 export
4. 在 `env_checker.py` 的 `start_checks()` 加入實例

### 修改 Queue 訊息格式
1. 修改 `backend.py` 的 docstring 和發送邏輯
2. 修改 `app.py` 的 `_poll_queue()` 接收邏輯
3. **同時更新** `tests/test_frames_integration.py::TestQueueMessageContract`

## 測試

```bash
# 執行全部測試（不需 Eagle 運行、不需 GPU）
python -m pytest gui/tests/ -v

# 執行單一檔案
python -m pytest gui/tests/test_eagle_api.py -v

# 目前: 83 passed, ~2s
```

| 測試檔案 | 涵蓋 |
|:---|:---|
| `test_imports.py` | 跨模組命名一致性（防 EnvironmentChecker vs EnvCheckerWindow） |
| `test_eagle_api.py` | API 連線、分頁、篩選、切換、路徑建構 |
| `test_backend.py` | Queue 訊息格式、ETA 型別、控制流 |
| `test_env_checks.py` | 7 個檢查模組的介面與回傳 |
| `test_frames_integration.py` | ETA 格式化、圖片解析、訊息契約 |
| `test_tag_backup.py` | 備份建立、還原驗證、列表、刪除 |
