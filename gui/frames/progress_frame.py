import customtkinter as ctk
from gui.widgets.log_console import LogConsole

class ProgressFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._stop_callback = None
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew")
        self.progress_bar.set(0)
        
        # 狀態資訊列
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.info_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.stats_label = ctk.CTkLabel(self.info_frame, text="0.0% (0/0)")
        self.stats_label.grid(row=0, column=0, sticky="w")
        
        self.speed_label = ctk.CTkLabel(self.info_frame, text="處理速度: 0.0 張/秒    預計剩餘: 00:00")
        self.speed_label.grid(row=0, column=1, sticky="w")
        
        self.counters_label = ctk.CTkLabel(self.info_frame, text="成功: 0   失敗: 0   活躍進程: 0/0")
        self.counters_label.grid(row=0, column=2, sticky="e")
        
        # Log console
        self.log_console = LogConsole(self)
        self.log_console.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        # 按鈕列
        self.btn_stop = ctk.CTkButton(self, text="停止", fg_color="red", hover_color="darkred", command=self._on_stop)
        self.btn_stop.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="e")

    def update_progress(self, data: dict) -> None:
        total = data.get('total', 0)
        processed = data.get('processed', 0)
        pct = processed / total if total > 0 else 0
        
        self.progress_bar.set(pct)
        self.stats_label.configure(text=f"{pct*100:.1f}% ({processed}/{total})")
        
        speed = data.get('speed', 0.0)
        eta_seconds = data.get('eta', 0.0)
        eta_min = int(eta_seconds) // 60
        eta_sec = int(eta_seconds) % 60
        self.speed_label.configure(text=f"處理速度: {speed:.1f} 張/秒    預計剩餘: {eta_min:02d}:{eta_sec:02d}")
        
        succ = data.get('success', 0)
        fail = data.get('fail', 0)
        active = data.get('active_workers', '0/0')
        self.counters_label.configure(text=f"成功: {succ}   失敗: {fail}   活躍進程: {active}")

    def add_log(self, message: str) -> None:
        self.log_console.add_log(message)

    def reset(self) -> None:
        self.progress_bar.set(0)
        self.stats_label.configure(text="0.0% (0/0)")
        self.speed_label.configure(text="處理速度: 0.0 張/秒    預計剩餘: 00:00")
        self.counters_label.configure(text="成功: 0   失敗: 0   活躍進程: 0/0")
        self.log_console.clear()
        self.btn_stop.configure(state="normal", text="停止")

    def set_stop_callback(self, callback) -> None:
        self._stop_callback = callback
        
    def _on_stop(self):
        self.btn_stop.configure(state="disabled", text="正在停止...")
        if self._stop_callback:
            self._stop_callback()

    def set_finished(self, summary: dict) -> None:
        self.progress_bar.set(1.0)
        self.btn_stop.configure(state="disabled", text="已完成")
        total = summary.get('total') if 'total' in summary else summary.get('total_images', 0)
        success = summary.get('success') if 'success' in summary else summary.get('success_count', 0)
        fail = summary.get('fail') if 'fail' in summary else summary.get('failure_count', 0)
        self.add_log(f"處理完成！總計: {total} 成功: {success} 失敗: {fail}")
