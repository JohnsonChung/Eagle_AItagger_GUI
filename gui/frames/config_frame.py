import customtkinter as ctk
import configparser
import threading
from pathlib import Path
from tkinter import filedialog
from main.unified_config import UnifiedConfig, ModelConfig, TagConfig, ProcessConfig, ReportConfig

class ConfigFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        
        # --- 模型設定 ---
        self.model_label = ctk.CTkLabel(self, text="模型設定", font=ctk.CTkFont(size=16, weight="bold"))
        self.model_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")
        
        # 模型路徑
        ctk.CTkLabel(self, text="模型路徑:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.model_path_var = ctk.StringVar()
        self.model_path_entry = ctk.CTkEntry(self, textvariable=self.model_path_var)
        self.model_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.model_path_btn = ctk.CTkButton(self, text="瀏覽", width=60, command=self._browse_model)
        self.model_path_btn.grid(row=1, column=2, padx=10, pady=5)
        
        # 標籤字典
        ctk.CTkLabel(self, text="標籤字典:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.tags_path_var = ctk.StringVar()
        self.tags_path_entry = ctk.CTkEntry(self, textvariable=self.tags_path_var)
        self.tags_path_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.tags_path_btn = ctk.CTkButton(self, text="瀏覽", width=60, command=self._browse_tags)
        self.tags_path_btn.grid(row=2, column=2, padx=10, pady=5)

        # 測試模型按鈕 + 結果
        self.test_model_btn = ctk.CTkButton(
            self, text="🔍 測試模型", width=120,
            fg_color="#2B7A0B", hover_color="#1E5A08",
            command=self._on_test_model,
        )
        self.test_model_btn.grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.test_result_label = ctk.CTkLabel(self, text="", anchor="w")
        self.test_result_label.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # --- 標籤設定 ---
        self.tag_label = ctk.CTkLabel(self, text="標籤設定", font=ctk.CTkFont(size=16, weight="bold"))
        self.tag_label.grid(row=4, column=0, columnspan=3, padx=10, pady=(20, 5), sticky="w")
        
        # 置信度閾值
        ctk.CTkLabel(self, text="置信度閾值:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.threshold_var = ctk.DoubleVar(value=0.5)
        self.threshold_slider = ctk.CTkSlider(self, from_=0.0, to=1.0, number_of_steps=20, variable=self.threshold_var, command=self._update_threshold_label)
        self.threshold_slider.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.threshold_val_label = ctk.CTkLabel(self, text="0.50")
        self.threshold_val_label.grid(row=5, column=2, padx=10, pady=5)
        
        # Checkboxes
        self.use_chinese_var = ctk.BooleanVar()
        self.cb_use_chinese = ctk.CTkCheckBox(self, text="使用中文標籤", variable=self.use_chinese_var)
        self.cb_use_chinese.grid(row=6, column=1, padx=5, pady=5, sticky="w")
        
        self.replace_underscore_var = ctk.BooleanVar()
        self.cb_replace_underscore = ctk.CTkCheckBox(self, text="替換底線為空格", variable=self.replace_underscore_var)
        self.cb_replace_underscore.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        
        self.escape_tags_var = ctk.BooleanVar()
        self.cb_escape_tags = ctk.CTkCheckBox(self, text="轉義特殊字元", variable=self.escape_tags_var)
        self.cb_escape_tags.grid(row=8, column=1, padx=5, pady=5, sticky="w")
        
        self.sort_alpha_var = ctk.BooleanVar()
        self.cb_sort_alpha = ctk.CTkCheckBox(self, text="按字母排序", variable=self.sort_alpha_var)
        self.cb_sort_alpha.grid(row=9, column=1, padx=5, pady=5, sticky="w")
        
        # 強制追加/排除
        ctk.CTkLabel(self, text="強制追加標籤:").grid(row=10, column=0, padx=10, pady=5, sticky="e")
        self.add_tags_var = ctk.StringVar()
        self.add_tags_entry = ctk.CTkEntry(self, textvariable=self.add_tags_var, placeholder_text="以逗號分隔")
        self.add_tags_entry.grid(row=10, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(self, text="強制排除標籤:").grid(row=11, column=0, padx=10, pady=5, sticky="e")
        self.exclude_tags_var = ctk.StringVar()
        self.exclude_tags_entry = ctk.CTkEntry(self, textvariable=self.exclude_tags_var, placeholder_text="以逗號分隔")
        self.exclude_tags_entry.grid(row=11, column=1, padx=5, pady=5, sticky="ew")
        
        # --- 處理設定 ---
        self.process_label = ctk.CTkLabel(self, text="處理設定", font=ctk.CTkFont(size=16, weight="bold"))
        self.process_label.grid(row=12, column=0, columnspan=3, padx=10, pady=(20, 5), sticky="w")
        
        # 寫入模式
        ctk.CTkLabel(self, text="寫入模式:").grid(row=13, column=0, padx=10, pady=5, sticky="e")
        self.write_mode_var = ctk.BooleanVar(value=False) # False=覆蓋, True=追加
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.grid(row=13, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkRadioButton(self.mode_frame, text="覆蓋", variable=self.write_mode_var, value=False).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(self.mode_frame, text="追加", variable=self.write_mode_var, value=True).pack(side="left")
        
        # 工作進程數
        ctk.CTkLabel(self, text="工作進程數:").grid(row=14, column=0, padx=10, pady=5, sticky="e")
        self.workers_var = ctk.StringVar(value="2")
        self.workers_menu = ctk.CTkOptionMenu(self, variable=self.workers_var, values=[str(i) for i in range(1, 9)])
        self.workers_menu.grid(row=14, column=1, padx=5, pady=5, sticky="w")
        
        # 批次大小
        ctk.CTkLabel(self, text="批次大小:").grid(row=15, column=0, padx=10, pady=5, sticky="e")
        self.batch_size_var = ctk.StringVar(value="8")
        self.batch_size_menu = ctk.CTkOptionMenu(self, variable=self.batch_size_var, values=["1","2","4","8","16","32","50"])
        self.batch_size_menu.grid(row=15, column=1, padx=5, pady=5, sticky="w")
        
        self._original_config = None

    def _update_threshold_label(self, value):
        self.threshold_val_label.configure(text=f"{value:.2f}")

    def _browse_model(self):
        file = filedialog.askopenfilename(filetypes=[("ONNX Models", "*.onnx"), ("All Files", "*.*")])
        if file:
            self.model_path_var.set(file)

    def _browse_tags(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if file:
            self.tags_path_var.set(file)

    @staticmethod
    def csv_has_chinese(path: str) -> bool:
        """檢查標籤 CSV 是否含中文欄位 right_tag_cn"""
        try:
            with open(path, encoding="utf-8-sig") as f:
                header = f.readline()
            return "right_tag_cn" in [c.strip() for c in header.split(",")]
        except OSError:
            return False

    def _refresh_chinese_support(self, *_):
        """依目前標籤字典啟用 / 停用「使用中文標籤」"""
        if self.csv_has_chinese(self.tags_path_var.get()):
            self.cb_use_chinese.configure(state="normal", text="使用中文標籤")
        else:
            self.use_chinese_var.set(False)
            self.cb_use_chinese.configure(
                state="disabled", text="使用中文標籤（此字典無中文欄位）"
            )

    def load_config(self, config: UnifiedConfig) -> None:
        self._original_config = config
        self.model_path_var.set(str(config.model.model_path))
        self.tags_path_var.set(str(config.model.tags_path))
        
        self.threshold_var.set(config.tag.threshold)
        self._update_threshold_label(config.tag.threshold)
        
        self.use_chinese_var.set(config.tag.use_chinese_name)
        self.replace_underscore_var.set(config.tag.replace_underscore)
        self.escape_tags_var.set(config.tag.escape_tags)
        self.sort_alpha_var.set(config.tag.sort_alphabetically)
        
        self.add_tags_var.set(", ".join(config.tag.additional_tags))
        self.exclude_tags_var.set(", ".join(config.tag.exclude_tags))
        
        self.write_mode_var.set(config.process.add_write_mode)
        self.workers_var.set(str(config.process.max_workers))
        self.batch_size_var.set(str(config.process.batch_size))

        # 載入後依字典校正中文選項，並在之後路徑變更時自動重新檢查
        self._refresh_chinese_support()
        if not getattr(self, "_tags_trace_added", False):
            self.tags_path_var.trace_add("write", self._refresh_chinese_support)
            self._tags_trace_added = True

    def get_config(self) -> UnifiedConfig:
        config = self._original_config if self._original_config else UnifiedConfig()
        
        config.model.model_path = Path(self.model_path_var.get())
        config.model.tags_path = Path(self.tags_path_var.get())
        
        config.tag.threshold = self.threshold_var.get()
        # 字典沒有中文欄位時強制使用英文，避免推理時 KeyError
        config.tag.use_chinese_name = (
            self.use_chinese_var.get() and self.csv_has_chinese(self.tags_path_var.get())
        )
        config.tag.replace_underscore = self.replace_underscore_var.get()
        config.tag.escape_tags = self.escape_tags_var.get()
        config.tag.sort_alphabetically = self.sort_alpha_var.get()
        
        config.tag.additional_tags = [t.strip() for t in self.add_tags_var.get().split(",") if t.strip()]
        config.tag.exclude_tags = [t.strip() for t in self.exclude_tags_var.get().split(",") if t.strip()]
        
        config.process.add_write_mode = self.write_mode_var.get()
        config.process.max_workers = int(self.workers_var.get())
        config.process.batch_size = int(self.batch_size_var.get())
        
        return config

    def save_config_to_file(self, path: Path) -> None:
        parser = configparser.ConfigParser()
        if path.exists():
            parser.read(path, encoding='utf-8')
            
        if not parser.has_section("Model"): parser.add_section("Model")
        parser.set("Model", "model_path", self.model_path_var.get())
        parser.set("Model", "tags_path", self.tags_path_var.get())
        
        if not parser.has_section("Tag"): parser.add_section("Tag")
        parser.set("Tag", "threshold", str(self.threshold_var.get()))
        parser.set("Tag", "use_chinese_name", str(self.use_chinese_var.get()))
        parser.set("Tag", "replace_underscore", str(self.replace_underscore_var.get()))
        parser.set("Tag", "escape_tags", str(self.escape_tags_var.get()))
        parser.set("Tag", "sort_alphabetically", str(self.sort_alpha_var.get()))
        parser.set("Tag", "additional_tags", self.add_tags_var.get())
        parser.set("Tag", "exclude_tags", self.exclude_tags_var.get())
        
        if not parser.has_section("Process"): parser.add_section("Process")
        parser.set("Process", "max_workers", self.workers_var.get())
        parser.set("Process", "batch_size", self.batch_size_var.get())
        
        if not parser.has_section("Json"): parser.add_section("Json")
        parser.set("Json", "add_write_mode", str(self.write_mode_var.get()))
        
        with open(path, 'w', encoding='utf-8') as f:
            parser.write(f)

    def _on_test_model(self):
        """測試模型按鈕點擊事件"""
        model_path = self.model_path_var.get()
        tags_path = self.tags_path_var.get()

        if not model_path or not tags_path:
            self.test_result_label.configure(
                text="⚠️ 請先設定模型路徑和標籤字典",
                text_color="orange",
            )
            return

        self.test_model_btn.configure(state="disabled", text="⏳ 測試中...")
        self.test_result_label.configure(text="正在載入模型並執行推理...", text_color="gray")

        def _run_test():
            from gui.model_tester import test_model
            result = test_model(model_path, tags_path)
            self.after(0, lambda: self._show_test_result(result))

        threading.Thread(target=_run_test, daemon=True).start()

    def _show_test_result(self, result):
        """顯示模型測試結果"""
        self.test_model_btn.configure(state="normal", text="🔍 測試模型")

        if result.success:
            self.test_result_label.configure(
                text=(
                    f"✅ 通過 | {result.provider} | "
                    f"輸入 {result.input_shape} | "
                    f"{result.output_count} 標籤 | "
                    f"推理 {result.inference_time_ms}ms"
                ),
                text_color="#2B7A0B",
            )
        else:
            self.test_result_label.configure(
                text=f"❌ {result.error}",
                text_color="red",
            )
