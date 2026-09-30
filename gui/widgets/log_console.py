import datetime
import customtkinter as ctk

class LogConsole(ctk.CTkTextbox):
    """自定義的日誌控制台元件"""
    
    def __init__(self, master, max_lines=500, **kwargs):
        super().__init__(master, **kwargs)
        self.max_lines = max_lines
        
        # 預設為禁用狀態，防止使用者編輯
        self.configure(state="disabled")

    def add_log(self, message: str):
        """添加一條帶時間戳的日誌"""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        log_line = f"{timestamp} {message}\n"
        
        # 暫時啟用以寫入日誌
        self.configure(state="normal")
        self.insert("end", log_line)
        
        # 控制行數，防止記憶體問題
        content = self.get("1.0", "end-1c")
        lines = content.split('\n')
        if len(lines) > self.max_lines:
            # 刪除多餘的行
            delete_count = len(lines) - self.max_lines
            self.delete("1.0", f"{delete_count + 1}.0")
            
        # 自動捲動到底部
        self.see("end")
        
        # 恢復禁用狀態
        self.configure(state="disabled")

    def clear(self):
        """清除所有日誌"""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
