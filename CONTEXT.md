# Eagle AI 圖像標註 (Eagle AI Tagger)

連接 Eagle 素材庫與 WD14 深度學習標籤模型的自動標註系統，實現素材特徵辨識、多語系標籤格式化與標籤寫入。

## Language

### Eagle 資源架構

**EagleItem (Eagle 素材項目)**:
Eagle 資源庫中代表單一素材的實體單位，包含素材資料夾、主媒體檔案與其專屬的 `metadata.json`。
_Avoid_: 圖片, 檔案夾, 圖庫, 檔案

**Library (資源庫)**:
Eagle 管理全部素材的最上層目錄結構，包含 `images/` 目錄與資料庫設定檔。
_Avoid_: 資料庫, 工作區, 相簿

**ItemMetadata (素材中繼資料)**:
存在於素材資料夾中的 `metadata.json`，儲存該素材的標籤、註釋與屬性資料。
_Avoid_: 描述檔, 設定檔, 圖片資訊

**ImageList (圖片清單)**:
使用者從 Eagle 複製並貼入的待處理素材路徑列表，是系統唯一的輸入介面。
_Avoid_: 任務列表, 檔案清單, 佇列

### 標籤與模型領域

**Tag (標籤)**:
附著於 EagleItem 上、描述視覺特徵的語義字串，作為檢索與篩選條件。
_Avoid_: 關鍵字, 標記, 類別

**RatingTag (分級標籤)**:
模型輸出的前四個固定位置指標，代表內容的敏感程度分級（general、sensitive、questionable、explicit）。目前未寫入 EagleItem。
_Avoid_: 評分, 年齡限制, 敏感度等級

**RawTag (原始標籤)**:
模型與 Danbooru 體系原生輸出的英文底線格式標籤（如 `blue_eyes`）。
_Avoid_: 預設標籤, 英文標籤, 原始字串

**DisplayTag (呈現標籤)**:
依據使用者配置（轉換為中文、替換底線為空格或進行特殊符號轉義）後最終寫入 EagleItem 的標籤文字。
_Avoid_: 最終標籤, 輸出標籤, 介面標籤

**TagDictionary (標籤字典)**:
定義所有模型標籤的 RawTag 名稱、分類與中文對應名稱的參照表格檔案（CSV），包含 tag_id、category、count 與 right_tag_cn 等欄位。
_Avoid_: 翻譯表, 碼表, 詞庫

**Interrogator (推理引擎)**:
WD 社群中對載入 ONNX 模型並執行圖像特徵推理的核心元件的專有稱呼。
_Avoid_: 分類器, 辨識器, 模型包裝器

**ForcedTag (強制標籤)**:
略過模型推論結果，由使用者在設定檔中指定必然追加或必然排除的特定標籤。
_Avoid_: 預設標籤, 系統標籤, 固化標籤

### 操作與處理模式

**AppendMode (追加模式)**:
保留 EagleItem 既有標籤、將新標籤與之聯集去重的寫入策略。
_Avoid_: 增量模式, 補充模式

**OverwriteMode (覆蓋模式)**:
以全新結果取代 EagleItem 既有全部標籤的寫入策略。
_Avoid_: 重置模式, 取代模式

**TagMigration (標籤遷移)**:
將歷史英文標籤依據標籤字典轉換為中文標籤的離線批次程序。
_Avoid_: 標籤同步, 標籤修復, 重新標註
