import customtkinter as ctk
import queue
import threading
from pathlib import Path
from tkinter import messagebox
from main.unified_config import UnifiedConfig
from gui.frames.config_frame import ConfigFrame
from gui.frames.image_list_frame import ImageListFrame
from gui.frames.progress_frame import ProgressFrame
from gui.frames.result_frame import ResultFrame
from gui.env_checker import EnvCheckerWindow
from gui.backend import BackendController

class EagleTaggerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Eagle AI Tagger v4.0.1')
        self.geometry('900x650')
        self.minsize(800, 600)
        ctk.set_appearance_mode('system')
        ctk.set_default_color_theme('blue')
        
        self.config_path = Path("config.ini")
        self.config = UnifiedConfig.from_ini_file(self.config_path) if self.config_path.exists() else UnifiedConfig()
        self.backend = BackendController(self.config)
        self.progress_queue = queue.Queue()
        
        self._setup_ui()
        self._load_config()
        self._check_version_background()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 確保視窗顯示在最前面
        self.lift()
        self.focus_force()

    def _setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # 側邊導航欄
        self.sidebar_frame = ctk.CTkFrame(self, width=150, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Eagle Tagger", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.btn_nav_config = ctk.CTkButton(self.sidebar_frame, text="設定", command=lambda: self.select_frame("config"))
        self.btn_nav_config.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_nav_list = ctk.CTkButton(self.sidebar_frame, text="圖片清單", command=lambda: self.select_frame("image_list"))
        self.btn_nav_list.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_nav_progress = ctk.CTkButton(self.sidebar_frame, text="執行進度", command=lambda: self.select_frame("progress"))
        self.btn_nav_progress.grid(row=3, column=0, padx=20, pady=10)
        
        self.btn_nav_result = ctk.CTkButton(self.sidebar_frame, text="結果報告", command=lambda: self.select_frame("result"))
        self.btn_nav_result.grid(row=4, column=0, padx=20, pady=10)
        
        self.btn_env = ctk.CTkButton(self.sidebar_frame, text="環境檢查", command=self._show_env_checker, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.btn_env.grid(row=6, column=0, padx=20, pady=10)
        
        # 內容區域
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # 初始化 Frames
        self.frames = {
            "config": ConfigFrame(self.content_frame),
            "image_list": ImageListFrame(self.content_frame),
            "progress": ProgressFrame(self.content_frame),
            "result": ResultFrame(self.content_frame)
        }
        
        # 綁定事件
        self.frames["image_list"].set_start_callback(self._start_processing)
        self.frames["progress"].set_stop_callback(self._stop_processing)
        
        # 預設顯示設定頁
        self.select_frame("config")

    def select_frame(self, name: str):
        # 按鈕反白邏輯
        for btn_name, btn in {
            "config": self.btn_nav_config,
            "image_list": self.btn_nav_list,
            "progress": self.btn_nav_progress,
            "result": self.btn_nav_result
        }.items():
            if btn_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color=["#3a7ebf", "#1f538d"])
                
        # 顯示 Frame
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nsew")

    def _load_config(self):
        self.frames["config"].load_config(self.config)

    def _start_processing(self):
        # 儲存設定
        self.config = self.frames["config"].get_config()
        self.frames["config"].save_config_to_file(self.config_path)
        self.backend = BackendController(self.config)
        
        img_data = self.frames["image_list"].get_image_data()
        
        self.frames["image_list"].set_processing_state(True)
        self.frames["progress"].reset()
        self.select_frame("progress")
        
        self.backend.start(img_data, self.progress_queue)
        self.after(100, self._poll_queue)

    def _stop_processing(self):
        if self.backend.is_running():
            self.backend.stop()
            self.frames["progress"].add_log("正在停止處理程序...")

    def _poll_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                msg_type = msg.get('type')
                
                if msg_type == 'progress':
                    self.frames["progress"].update_progress(msg)
                elif msg_type == 'log':
                    self.frames["progress"].add_log(msg['message'])
                elif msg_type == 'batch':
                    self.frames["progress"].add_log(
                        f"批次 {msg['batch_id']} 完成: 成功 {msg['success_count']}/{msg['batch_size']}"
                    )
                elif msg_type == 'writing_json':
                    self.frames["progress"].add_log(
                        f"寫入 JSON: {msg['current']}/{msg['total']}"
                    )
                elif msg_type == 'error':
                    self.frames["progress"].add_log(f"錯誤: {msg['message']}")
                    self.frames["image_list"].set_processing_state(False)
                elif msg_type == 'finished':
                    summary = msg.get('summary', {})
                    failed = msg.get('failed_images', [])
                    self.frames["progress"].set_finished(summary)
                    self.frames["result"].show_results(summary, failed)
                    self.frames["result"].on_processing_finished()
                    self.frames["image_list"].set_processing_state(False)
                    self.select_frame("result")
                    return  # 結束 polling
        except queue.Empty:
            pass
            
        if self.backend.is_running():
            self.after(100, self._poll_queue)
        else:
            self.frames["image_list"].set_processing_state(False)

    def _check_version_background(self):
        def check():
            try:
                latest, url = BackendController.check_version(self.config)
            except Exception:
                pass
        threading.Thread(target=check, daemon=True).start()

    def _show_env_checker(self):
        EnvCheckerWindow(self)

    def _on_closing(self):
        if self.backend.is_running():
            if messagebox.askokcancel("退出", "目前正在處理中，確定要終止並退出嗎？"):
                self.backend.stop()
                self.destroy()
        else:
            self.destroy()
