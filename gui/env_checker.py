import customtkinter as ctk
import threading
import queue
import webbrowser
from typing import List
from .env_checks import (
    PythonCheck,
    GPUCheck,
    CUDACheck,
    CUDNNCheck,
    VCRedistCheck,
    DepsCheck,
    ModelCheck,
    CheckResult
)

class EnvCheckerWindow(ctk.CTkToplevel):
    """環境檢查主視窗"""
    def __init__(self, parent=None, config_path='config.ini'):
        super().__init__(parent)
        
        self.title("Eagle AI Tagger — 環境檢查")
        self.geometry("550x500")
        self.resizable(False, False)
        
        # 使視窗置中與取得焦點
        self.grab_set()
        
        self.config_path = config_path
        self.result_queue = queue.Queue()
        self.all_passed = True
        self.is_checking = False
        
        self._setup_ui()
        
        # 啟動檢查
        self.start_checks()
        
    def _setup_ui(self):
        """建立 UI 佈局"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 標題
        title_label = ctk.CTkLabel(
            self, 
            text="系統環境檢查", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")
        
        # 檢查項目列表 (可捲動)
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(1, weight=1)
        
        # 底部按鈕區
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, pady=20, sticky="ew")
        bottom_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.btn_recheck = ctk.CTkButton(
            bottom_frame,
            text="重新檢查",
            command=self.start_checks
        )
        self.btn_recheck.grid(row=0, column=0, padx=10)
        
        self.btn_start = ctk.CTkButton(
            bottom_frame,
            text="啟動主程式",
            state="disabled",
            command=self.on_start_main
        )
        self.btn_start.grid(row=0, column=1, padx=10)
        
    def _clear_results(self):
        """清除舊的檢查結果"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
    def start_checks(self):
        """啟動所有檢查"""
        if self.is_checking:
            return
            
        self.is_checking = True
        self.all_passed = True
        self.btn_recheck.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self._clear_results()
        
        # 定義要執行的檢查
        checks = [
            PythonCheck(),
            VCRedistCheck(),
            GPUCheck(),
            CUDACheck(),
            CUDNNCheck(),
            DepsCheck(),
            ModelCheck(config_path=self.config_path)
        ]
        
        # 在背景執行緒中執行
        threading.Thread(target=self._run_checks_thread, args=(checks,), daemon=True).start()
        
        # 開始輪詢佇列
        self.after(100, self._process_queue)
        
    def _run_checks_thread(self, checks: List):
        """背景執行緒：執行所有檢查"""
        for check in checks:
            try:
                result = check.run()
            except Exception as e:
                result = CheckResult(
                    name=check.__class__.__name__,
                    status="fail",
                    message=f"檢查時發生錯誤: {str(e)}"
                )
            self.result_queue.put(result)
            
        self.result_queue.put("DONE")
        
    def _process_queue(self):
        """主執行緒：更新 UI"""
        try:
            while True:
                item = self.result_queue.get_nowait()
                if item == "DONE":
                    self.is_checking = False
                    self.btn_recheck.configure(state="normal")
                    if self.all_passed:
                        self.btn_start.configure(state="normal")
                    return
                else:
                    self._add_result_row(item)
                    if item.status == "fail":
                        self.all_passed = False
        except queue.Empty:
            pass
            
        if self.is_checking:
            self.after(100, self._process_queue)
            
    def _add_result_row(self, result: CheckResult):
        """新增一筆檢查結果到 UI"""
        row_idx = len(self.scrollable_frame.winfo_children()) // 3  # 計算當前列數
        
        # 決定狀態圖示與顏色
        if result.status == "pass":
            icon = "✅"
            color = "green"
        elif result.status == "warn":
            icon = "⚠️"
            color = "orange"
        else:
            icon = "❌"
            color = "red"
            
        # 圖示
        icon_label = ctk.CTkLabel(
            self.scrollable_frame,
            text=icon,
            text_color=color,
            font=ctk.CTkFont(size=16)
        )
        icon_label.grid(row=row_idx, column=0, padx=(5, 10), pady=10, sticky="n")
        
        # 內容區塊 (名稱 + 訊息)
        content_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        content_frame.grid(row=row_idx, column=1, pady=5, sticky="ew")
        content_frame.grid_columnconfigure(0, weight=1)
        
        name_label = ctk.CTkLabel(
            content_frame,
            text=result.name,
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        msg_label = ctk.CTkLabel(
            content_frame,
            text=result.message,
            text_color="gray",
            anchor="w",
            justify="left",
            wraplength=400
        )
        msg_label.grid(row=1, column=0, sticky="w")
        
        # 修正連結 (如果有的話)
        if result.fix_url and result.status != "pass":
            link_label = ctk.CTkLabel(
                content_frame,
                text="下載/修正連結",
                text_color="#1f538d",
                cursor="hand2",
                anchor="w",
                font=ctk.CTkFont(underline=True)
            )
            link_label.grid(row=2, column=0, sticky="w", pady=(2, 0))
            link_label.bind("<Button-1>", lambda e, url=result.fix_url: webbrowser.open(url))
            
    def on_start_main(self):
        """啟動主程式事件處理"""
        # 可以發出信號或直接關閉視窗，讓主程式接手
        self.destroy()

if __name__ == "__main__":
    app = ctk.CTk()
    checker = EnvCheckerWindow(app)
    app.mainloop()
