"""單張圖片預覽推理視窗

在大量處理前，讓使用者用一張圖片測試模型效果和閾值設定。
可即時調整閾值，觀察標籤篩選結果。
"""
import customtkinter as ctk
import threading
import queue
from pathlib import Path
from PIL import Image


class PreviewWindow(ctk.CTkToplevel):
    """預覽測試視窗"""

    def __init__(self, parent, image_path: str, config, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("預覽測試 — 單張推理結果")
        self.geometry("700x600")
        self.grab_set()

        self._image_path = image_path
        self._config = config
        self._ratings = {}
        self._all_tags = {}  # {tag_name: confidence}
        self._result_queue = queue.Queue()

        self._setup_ui()

        # 啟動推理
        self.after(100, self._start_inference)

    def _setup_ui(self):
        """建立 UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 頂部：圖片資訊
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        filename = Path(self._image_path).name
        self.info_label = ctk.CTkLabel(
            info_frame, text=f"📷 {filename}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.info_label.pack(side="left")

        self.status_label = ctk.CTkLabel(
            info_frame, text="⏳ 推理中...", anchor="e",
        )
        self.status_label.pack(side="right")

        # 閾值控制列
        threshold_frame = ctk.CTkFrame(self, fg_color="transparent")
        threshold_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(threshold_frame, text="置信度閾值:").pack(side="left")
        self.threshold_var = ctk.DoubleVar(value=self._config.tag.threshold)
        self.threshold_slider = ctk.CTkSlider(
            threshold_frame, from_=0.0, to=1.0,
            number_of_steps=100, variable=self.threshold_var,
            command=self._on_threshold_change,
        )
        self.threshold_slider.pack(side="left", padx=10, fill="x", expand=True)
        self.threshold_label = ctk.CTkLabel(
            threshold_frame, text=f"{self._config.tag.threshold:.2f}", width=40,
        )
        self.threshold_label.pack(side="left")

        self.count_label = ctk.CTkLabel(threshold_frame, text="", width=100)
        self.count_label.pack(side="right")

        # 結果區域
        self.result_text = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=13))
        self.result_text.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="nsew")

        # 底部按鈕
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.btn_apply = ctk.CTkButton(
            btn_frame, text="✅ 套用此閾值到設定",
            command=self._apply_threshold,
            fg_color="#2B7A0B", hover_color="#1E5A08",
        )
        self.btn_apply.pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="關閉", command=self.destroy,
            fg_color="gray",
        ).pack(side="right", padx=5)

    def _start_inference(self):
        """在背景執行推理"""
        def _run():
            try:
                from main.tagger import WaifuDiffusionInterrogator
                tagger = WaifuDiffusionInterrogator(self._config)
                tagger.load()

                image = Image.open(self._image_path)
                ratings, tags = tagger.interrogate(image)
                tagger.unload()

                self._result_queue.put({
                    "status": "ok",
                    "ratings": ratings,
                    "tags": tags,
                })
            except Exception as e:
                self._result_queue.put({
                    "status": "error",
                    "message": str(e),
                })

        threading.Thread(target=_run, daemon=True).start()
        self.after(200, self._poll_result)

    def _poll_result(self):
        """輪詢推理結果"""
        try:
            result = self._result_queue.get_nowait()
        except queue.Empty:
            self.after(200, self._poll_result)
            return

        if result["status"] == "error":
            self.status_label.configure(text="❌ 失敗")
            self.result_text.insert("end", f"推理失敗:\n{result['message']}")
            return

        self._ratings = result["ratings"]
        self._all_tags = result["tags"]
        self.status_label.configure(text="✅ 完成")
        self._render_results()

    def _on_threshold_change(self, value):
        """閾值滑桿變動時重新篩選"""
        self.threshold_label.configure(text=f"{value:.2f}")
        if self._all_tags:
            self._render_results()

    def _render_results(self):
        """依閾值渲染標籤結果"""
        threshold = self.threshold_var.get()
        self.result_text.delete("1.0", "end")

        # 評分（前4個特殊標籤）
        self.result_text.insert("end", "═══ 評分 ═══\n")
        for tag, conf in sorted(self._ratings.items(), key=lambda x: -x[1]):
            bar = "█" * int(conf * 20) + "░" * (20 - int(conf * 20))
            self.result_text.insert("end", f"  {bar}  {conf:.3f}  {tag}\n")

        # 通過閾值的標籤
        passed = {k: v for k, v in self._all_tags.items() if v >= threshold}
        failed = {k: v for k, v in self._all_tags.items() if v < threshold}

        self.count_label.configure(
            text=f"通過: {len(passed)} / {len(self._all_tags)}"
        )

        self.result_text.insert("end", f"\n═══ 通過閾值 ({len(passed)}) ═══\n")
        for tag, conf in sorted(passed.items(), key=lambda x: -x[1]):
            self.result_text.insert("end", f"  ✅ {conf:.3f}  {tag}\n")

        if failed:
            self.result_text.insert("end", f"\n═══ 未通過 ({len(failed)}) ═══\n")
            # 只顯示接近閾值的（前 30 個）
            near_miss = sorted(failed.items(), key=lambda x: -x[1])[:30]
            for tag, conf in near_miss:
                self.result_text.insert("end", f"  ❌ {conf:.3f}  {tag}\n")
            if len(failed) > 30:
                self.result_text.insert(
                    "end", f"  ... 還有 {len(failed) - 30} 個低信心標籤\n"
                )

    def _apply_threshold(self):
        """將目前閾值套用回主視窗設定"""
        try:
            parent = self.master
            if hasattr(parent, 'frames') and 'config' in parent.frames:
                config_frame = parent.frames['config']
                new_val = self.threshold_var.get()
                config_frame.threshold_var.set(new_val)
                config_frame.threshold_val_label.configure(text=f"{new_val:.2f}")
                self.btn_apply.configure(text="✅ 已套用！")
                self.after(1500, lambda: self.btn_apply.configure(text="✅ 套用此閾值到設定"))
        except Exception:
            pass
