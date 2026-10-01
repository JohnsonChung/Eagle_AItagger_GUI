"""圖片清單面板 — 支援 Eagle API 直接匯入與手動載入"""
import customtkinter as ctk
import threading
import queue
from pathlib import Path
from tkinter import filedialog, messagebox

from gui.eagle_api import EagleAPI, EagleAPIError


class ImageListFrame(ctk.CTkFrame):
    """圖片清單面板，提供從 Eagle 匯入、剪貼簿貼上、載入檔案三種方式"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._image_paths = []
        self._start_callback = None
        self._eagle_api = EagleAPI()
        self._eagle_folders = []
        self._fetch_queue = queue.Queue()

        self._setup_eagle_section()
        self._setup_summary_section()
        self._setup_button_section()

        # 啟動時自動偵測 Eagle
        self.after(500, self._auto_detect_eagle)

    # === UI 建構 ===

    def _setup_eagle_section(self):
        """建立 Eagle 匯入區塊"""
        self.eagle_frame = ctk.CTkFrame(self)
        self.eagle_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.eagle_frame.grid_columnconfigure(1, weight=1)

        # 標題列
        title_frame = ctk.CTkFrame(self.eagle_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="ew")
        title_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            title_frame, text="從 Eagle 匯入",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.eagle_status_label = ctk.CTkLabel(
            title_frame, text="⏳ 偵測中...", text_color="gray"
        )
        self.eagle_status_label.pack(side="right")

        # 資源庫選擇
        ctk.CTkLabel(self.eagle_frame, text="資源庫:").grid(
            row=1, column=0, padx=(10, 5), pady=3, sticky="w"
        )
        self.library_menu = ctk.CTkOptionMenu(
            self.eagle_frame, values=["--"],
            command=self._on_library_changed, width=300
        )
        self.library_menu.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        self._library_list = []  # List[EagleLibraryInfo]
        self._current_library_path = ""

        # 資料夾選擇
        ctk.CTkLabel(self.eagle_frame, text="資料夾:").grid(
            row=2, column=0, padx=(10, 5), pady=3, sticky="w"
        )
        self.folder_menu = ctk.CTkOptionMenu(
            self.eagle_frame, values=["全部資料夾"], width=300
        )
        self.folder_menu.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        # 篩選選項
        filter_frame = ctk.CTkFrame(self.eagle_frame, fg_color="transparent")
        filter_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        # 副檔名勾選
        ext_label = ctk.CTkLabel(filter_frame, text="副檔名:")
        ext_label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.ext_vars = {}
        col = 1
        for ext in ["jpg", "png", "webp", "gif", "bmp", "heic", "avif"]:
            var = ctk.BooleanVar(value=ext in ("jpg", "png", "webp", "gif", "bmp"))
            cb = ctk.CTkCheckBox(filter_frame, text=ext, variable=var, width=60)
            cb.grid(row=0, column=col, padx=2)
            self.ext_vars[ext] = var
            col += 1

        # 標籤篩選
        self.skip_tagged_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filter_frame, text="只匯入沒有 AITagger_ed 標籤的素材",
            variable=self.skip_tagged_var
        ).grid(row=1, column=0, columnspan=8, padx=0, pady=(5, 0), sticky="w")

        # 匯入按鈕
        btn_row = ctk.CTkFrame(self.eagle_frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")

        self.btn_eagle_import = ctk.CTkButton(
            btn_row, text="從 Eagle 匯入", command=self._import_from_eagle,
            fg_color="#1f538d", state="disabled"
        )
        self.btn_eagle_import.pack(side="left", padx=5)

        self.eagle_progress_label = ctk.CTkLabel(
            btn_row, text="", text_color="gray"
        )
        self.eagle_progress_label.pack(side="left", padx=10)

    def _setup_summary_section(self):
        """建立摘要顯示區塊"""
        self.summary_label = ctk.CTkLabel(
            self, text="已載入 0 張圖片",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.summary_label.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

        self.list_textbox = ctk.CTkTextbox(self, state="disabled", height=120)
        self.list_textbox.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

    def _setup_button_section(self):
        """建立底部按鈕列"""
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.btn_paste = ctk.CTkButton(
            self.btn_frame, text="從剪貼簿貼上",
            command=self.load_from_clipboard
        )
        self.btn_paste.pack(side="left", padx=5)

        self.btn_file = ctk.CTkButton(
            self.btn_frame, text="載入檔案",
            command=self.load_from_file
        )
        self.btn_file.pack(side="left", padx=5)

        self.btn_clear = ctk.CTkButton(
            self.btn_frame, text="清除",
            command=self.clear, fg_color="gray"
        )
        self.btn_clear.pack(side="left", padx=5)

        self.btn_preview = ctk.CTkButton(
            self.btn_frame, text="🔍 預覽測試",
            command=self._on_preview,
            fg_color="#1E6091", hover_color="#14476B",
        )
        self.btn_preview.pack(side="right", padx=5)

        self.btn_start = ctk.CTkButton(
            self.btn_frame, text="開始處理",
            command=self._on_start,
            fg_color="green", hover_color="darkgreen"
        )
        self.btn_start.pack(side="right", padx=5)

    # === Eagle API 整合 ===

    def _auto_detect_eagle(self):
        """在背景偵測 Eagle 是否可用"""
        def _check():
            try:
                if self._eagle_api.is_available():
                    lib_info = self._eagle_api.get_library_info()
                    folders = self._eagle_api.get_folders_flat()
                    libraries = self._eagle_api.get_library_history()
                    self._fetch_queue.put({
                        "status": "ok",
                        "library": lib_info,
                        "folders": folders,
                        "libraries": libraries,
                    })
                else:
                    self._fetch_queue.put({"status": "unavailable"})
            except Exception as e:
                self._fetch_queue.put({"status": "error", "message": str(e)})

        threading.Thread(target=_check, daemon=True).start()
        self.after(200, self._poll_eagle_detect)

    def _poll_eagle_detect(self):
        """輪詢 Eagle 偵測結果"""
        try:
            result = self._fetch_queue.get_nowait()
            if result["status"] == "ok":
                lib_info = result["library"]
                self._eagle_folders = result["folders"]
                libraries = result.get("libraries", [])

                self.eagle_status_label.configure(
                    text="✅ Eagle 已連線", text_color="green"
                )

                # 填充資源庫下拉選單
                self._library_list = libraries
                lib_names = [lib.name for lib in libraries]
                if lib_names:
                    self.library_menu.configure(values=lib_names)
                # 標記當前資源庫
                self._current_library_path = lib_info.path
                self.library_menu.set(f"{lib_info.name}")

                # 填充資料夾下拉選單
                self._update_folder_menu()

                self.btn_eagle_import.configure(state="normal")

            elif result["status"] == "switch_done":
                # 切換完成，重新載入資料夾
                self._eagle_folders = result["folders"]
                self._current_library_path = result["library"].path
                self.library_menu.set(result["library"].name)
                self._update_folder_menu()
                self.eagle_status_label.configure(
                    text="✅ 已切換資源庫", text_color="green"
                )
                self.btn_eagle_import.configure(state="normal")
                self.library_menu.configure(state="normal")
                self.eagle_progress_label.configure(text="")

            elif result["status"] == "switch_error":
                self.eagle_status_label.configure(
                    text=f"❌ 切換失敗", text_color="red"
                )
                self.eagle_progress_label.configure(
                    text=result.get("message", "")
                )
                self.btn_eagle_import.configure(state="normal")
                self.library_menu.configure(state="normal")

            elif result["status"] == "unavailable":
                self.eagle_status_label.configure(
                    text="❌ Eagle 未啟動", text_color="red"
                )
                self.btn_eagle_import.configure(state="disabled")
            else:
                self.eagle_status_label.configure(
                    text=f"❌ {result.get('message', '錯誤')}", text_color="red"
                )
            return
        except queue.Empty:
            pass
        self.after(200, self._poll_eagle_detect)

    def _update_folder_menu(self):
        """更新資料夾下拉選單"""
        folder_names = ["全部資料夾"] + [f.name for f in self._eagle_folders]
        self.folder_menu.configure(values=folder_names)
        self.folder_menu.set("全部資料夾")

    def _on_library_changed(self, selected_name: str):
        """使用者切換資源庫"""
        # 找到對應的資源庫路徑
        target_lib = None
        for lib in self._library_list:
            if lib.name == selected_name:
                target_lib = lib
                break

        if not target_lib or target_lib.path == self._current_library_path:
            return

        # 在背景切換
        self.eagle_status_label.configure(
            text="⏳ 切換中...", text_color="orange"
        )
        self.eagle_progress_label.configure(
            text=f"正在切換至 {target_lib.name}..."
        )
        self.btn_eagle_import.configure(state="disabled")
        self.library_menu.configure(state="disabled")

        def _switch():
            try:
                success = self._eagle_api.switch_library(target_lib.path)
                if success:
                    # 切換後重新載入資料夾
                    import time
                    time.sleep(1)  # 給 Eagle 一點時間完成切換
                    lib_info = self._eagle_api.get_library_info()
                    folders = self._eagle_api.get_folders_flat()
                    self._fetch_queue.put({
                        "status": "switch_done",
                        "library": lib_info,
                        "folders": folders,
                    })
                else:
                    self._fetch_queue.put({
                        "status": "switch_error",
                        "message": "Eagle 回傳切換失敗"
                    })
            except Exception as e:
                self._fetch_queue.put({
                    "status": "switch_error",
                    "message": str(e)
                })

        threading.Thread(target=_switch, daemon=True).start()
        self.after(200, self._poll_eagle_detect)

    def _import_from_eagle(self):
        """從 Eagle API 匯入素材清單"""
        self.btn_eagle_import.configure(state="disabled", text="匯入中...")
        self.eagle_progress_label.configure(text="正在獲取素材清單...")

        # 取得篩選條件
        selected_folder = self.folder_menu.get()
        folder_id = None
        if selected_folder != "全部資料夾":
            for f in self._eagle_folders:
                if f.name == selected_folder:
                    folder_id = f.id
                    break

        selected_exts = [
            ext for ext, var in self.ext_vars.items() if var.get()
        ]
        skip_tagged = self.skip_tagged_var.get()

        def _fetch():
            try:
                def progress_cb(count):
                    self._fetch_queue.put({"status": "progress", "count": count})

                items = self._eagle_api.get_all_items(
                    folder_id=folder_id,
                    extensions=selected_exts if selected_exts else None,
                    require_no_tag="AITagger_ed" if skip_tagged else None,
                    progress_callback=progress_cb,
                )
                image_data = self._eagle_api.items_to_image_data(items)
                self._fetch_queue.put({
                    "status": "import_done",
                    "image_data": image_data
                })
            except EagleAPIError as e:
                self._fetch_queue.put({"status": "import_error", "message": str(e)})
            except Exception as e:
                self._fetch_queue.put({"status": "import_error", "message": str(e)})

        threading.Thread(target=_fetch, daemon=True).start()
        self.after(200, self._poll_eagle_import)

    def _poll_eagle_import(self):
        """輪詢 Eagle 匯入進度"""
        try:
            while True:
                result = self._fetch_queue.get_nowait()
                status = result["status"]

                if status == "progress":
                    count = result["count"]
                    self.eagle_progress_label.configure(text=f"已掃描 {count} 張素材...")
                elif status == "import_done":
                    image_data = result["image_data"]
                    self._image_paths = image_data
                    self._update_ui()
                    self.eagle_progress_label.configure(
                        text=f"匯入完成: {len(image_data)} 張"
                    )
                    self.btn_eagle_import.configure(
                        state="normal", text="從 Eagle 匯入"
                    )
                    return
                elif status == "import_error":
                    messagebox.showerror("Eagle 匯入錯誤", result["message"])
                    self.eagle_progress_label.configure(text="匯入失敗")
                    self.btn_eagle_import.configure(
                        state="normal", text="從 Eagle 匯入"
                    )
                    return
        except queue.Empty:
            pass
        self.after(200, self._poll_eagle_import)

    # === 原有功能（保留） ===

    def _parse_text(self, text: str):
        """解析文字內容為 image_data 格式"""
        items = []
        for line in text.splitlines():
            path_str = line.strip().strip('"').strip("'")
            if not path_str:
                continue
            path = Path(path_str).resolve()
            if path.suffix.lower() in (
                '.png', '.jpg', '.jpeg', '.webp', '.bmp',
                '.gif', '.heic', '.heif', '.avif'
            ):
                items.append({
                    'image_path': str(path),
                    'json_path': str(path.parent / 'metadata.json')
                })
        return items

    def _update_ui(self):
        """更新摘要顯示"""
        count = len(self._image_paths)
        self.summary_label.configure(text=f"已載入 {count:,} 張圖片")

        self.list_textbox.configure(state="normal")
        self.list_textbox.delete("1.0", "end")

        if not self._image_paths:
            self.list_textbox.insert("end", "請從 Eagle 匯入、剪貼簿或檔案載入圖片路徑...")
        else:
            paths = [item['image_path'] for item in self._image_paths]
            if len(paths) <= 8:
                self.list_textbox.insert("end", "\n".join(paths))
            else:
                top = "\n".join(paths[:5])
                bottom = "\n".join(paths[-3:])
                self.list_textbox.insert("end", f"{top}\n...\n{bottom}")

        self.list_textbox.configure(state="disabled")

    def load_from_clipboard(self) -> None:
        """從系統剪貼簿載入"""
        try:
            text = self.clipboard_get()
            new_items = self._parse_text(text)
            if new_items:
                self._image_paths.extend(new_items)
                self._update_ui()
            else:
                messagebox.showinfo("提示", "剪貼簿中沒有找到有效的圖片路徑")
        except Exception:
            messagebox.showwarning("警告", "無法讀取剪貼簿內容")

    def load_from_file(self) -> None:
        """從檔案載入"""
        file = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    text = f.read()
                new_items = self._parse_text(text)
                if new_items:
                    self._image_paths.extend(new_items)
                    self._update_ui()
            except Exception as e:
                messagebox.showerror("錯誤", f"載入檔案失敗: {e}")

    def clear(self) -> None:
        """清除所有圖片"""
        self._image_paths.clear()
        self._update_ui()
        self.eagle_progress_label.configure(text="")

    def get_image_data(self) -> list:
        """取得完整的 image_data 列表"""
        return self._image_paths.copy()

    def set_start_callback(self, callback) -> None:
        self._start_callback = callback

    def _on_start(self):
        if self._start_callback and self._image_paths:
            self._start_callback()

    def _on_preview(self):
        """預覽測試：取第一張圖片進行單張推理"""
        if not self._image_paths:
            from tkinter import messagebox
            messagebox.showinfo("預覽測試", "請先匯入或載入圖片")
            return

        # 取得第一張圖片路徑
        first = self._image_paths[0]
        image_path = first.get("image_path", "") if isinstance(first, dict) else str(first)

        if not image_path:
            return

        # 從主視窗取得目前設定
        try:
            app = self.winfo_toplevel()
            config = app.frames["config"].get_config()
        except Exception:
            from tkinter import messagebox
            messagebox.showerror("預覽測試", "無法讀取目前設定")
            return

        from gui.preview_window import PreviewWindow
        PreviewWindow(app, image_path, config)

    def set_processing_state(self, is_processing: bool) -> None:
        """處理中鎖定 / 解鎖所有按鈕"""
        state = "disabled" if is_processing else "normal"
        self.btn_paste.configure(state=state)
        self.btn_file.configure(state=state)
        self.btn_clear.configure(state=state)
        self.btn_start.configure(state=state)
        self.btn_preview.configure(state=state)
        self.btn_eagle_import.configure(state=state)
        self.library_menu.configure(state=state)
