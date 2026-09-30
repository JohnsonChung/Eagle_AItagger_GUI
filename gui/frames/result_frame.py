import customtkinter as ctk
import threading
import queue
from tkinter import filedialog, messagebox
from pathlib import Path
from gui.tag_backup import TagBackupManager


class ResultFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._last_summary = None
        self._last_failed = []
        self._backup_mgr = TagBackupManager()
        self._restore_queue = queue.Queue()
        
        # 標題
        ctk.CTkLabel(self, text="處理結果報告", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=15, sticky="w", padx=20)
        
        # 統計資訊
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.lbl_total = ctk.CTkLabel(self.stats_frame, text="總處理: 0")
        self.lbl_total.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        
        self.lbl_success = ctk.CTkLabel(self.stats_frame, text="成功: 0", text_color="green")
        self.lbl_success.grid(row=0, column=1, padx=15, pady=5, sticky="w")
        
        self.lbl_fail = ctk.CTkLabel(self.stats_frame, text="失敗: 0", text_color="red")
        self.lbl_fail.grid(row=0, column=2, padx=15, pady=5, sticky="w")
        
        self.lbl_tags = ctk.CTkLabel(self.stats_frame, text="產生標籤數: 0")
        self.lbl_tags.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        
        self.lbl_avg_tags = ctk.CTkLabel(self.stats_frame, text="平均每張: 0.0")
        self.lbl_avg_tags.grid(row=1, column=1, padx=15, pady=5, sticky="w")
        
        self.lbl_time = ctk.CTkLabel(self.stats_frame, text="總耗時: 0s")
        self.lbl_time.grid(row=2, column=0, padx=15, pady=5, sticky="w")
        
        self.lbl_speed = ctk.CTkLabel(self.stats_frame, text="速度: 0.0 it/s")
        self.lbl_speed.grid(row=2, column=1, padx=15, pady=5, sticky="w")
        
        # 失敗清單
        ctk.CTkLabel(self, text="失敗項目清單:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="nw", padx=20, pady=(10,0))
        self.failed_textbox = ctk.CTkTextbox(self, state="disabled")
        self.failed_textbox.grid(row=2, column=0, padx=20, pady=(35,10), sticky="nsew")
        
        # 按鈕列
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.btn_export = ctk.CTkButton(btn_frame, text="匯出報告", command=self.export_report)
        self.btn_export.pack(side="right", padx=5)

        # === 還原標籤區塊 ===
        restore_frame = ctk.CTkFrame(self)
        restore_frame.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="ew")
        restore_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            restore_frame, text="還原標籤",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 5), sticky="w")

        ctk.CTkLabel(restore_frame, text="備份:").grid(
            row=1, column=0, padx=(10, 5), pady=5, sticky="w"
        )
        self.backup_menu = ctk.CTkOptionMenu(
            restore_frame, values=["無備份"], width=350
        )
        self.backup_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.btn_restore = ctk.CTkButton(
            restore_frame, text="還原", width=80,
            command=self._on_restore,
            fg_color="#c0392b", hover_color="#922b21"
        )
        self.btn_restore.grid(row=1, column=2, padx=(5, 10), pady=5)

        self.restore_status = ctk.CTkLabel(
            restore_frame, text="", text_color="gray"
        )
        self.restore_status.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 8), sticky="w")

        # 初始化時載入備份列表
        self._refresh_backup_list()

    def _parse_summary(self, summary: dict) -> dict:
        total = summary.get('total') if 'total' in summary else summary.get('total_images', 0)
        success = summary.get('success') if 'success' in summary else summary.get('success_count', 0)
        fail = summary.get('fail') if 'fail' in summary else summary.get('failure_count', 0)
        generated_tags = summary.get('generated_tags') if 'generated_tags' in summary else summary.get('total_tags_generated', 0)
        avg_tags = summary.get('avg_tags') if 'avg_tags' in summary else summary.get('avg_tags_per_image', 0.0)
        
        raw_time = summary.get('total_time') if 'total_time' in summary else summary.get('total_processing_time', 0.0)
        if isinstance(raw_time, (int, float)):
            total_time = f"{raw_time:.1f}s"
        else:
            total_time = str(raw_time) if raw_time else "0s"
            
        speed = summary.get('speed') if 'speed' in summary else summary.get('images_per_second', 0.0)
        success_rate = summary.get('success_rate', (success / total * 100) if total > 0 else 0.0)
        
        return {
            'total': total,
            'success': success,
            'fail': fail,
            'generated_tags': generated_tags,
            'avg_tags': avg_tags,
            'total_time': total_time,
            'speed': speed,
            'success_rate': success_rate
        }

    def show_results(self, summary: dict, failed_images: list) -> None:
        self._last_summary = summary
        self._last_failed = failed_images
        
        p = self._parse_summary(summary)
        self.lbl_total.configure(text=f"總處理: {p['total']}")
        self.lbl_success.configure(text=f"成功: {p['success']}")
        self.lbl_fail.configure(text=f"失敗: {p['fail']}")
        self.lbl_tags.configure(text=f"產生標籤數: {p['generated_tags']}")
        self.lbl_avg_tags.configure(text=f"平均每張: {p['avg_tags']:.1f}")
        self.lbl_time.configure(text=f"總耗時: {p['total_time']}")
        self.lbl_speed.configure(text=f"速度: {p['speed']:.1f} it/s")
        
        self.failed_textbox.configure(state="normal")
        self.failed_textbox.delete("1.0", "end")
        if failed_images:
            formatted = []
            for item in failed_images:
                if isinstance(item, dict):
                    img_path = item.get("image_path", "")
                    err = item.get("error", "未知錯誤")
                    formatted.append(f"{img_path}: {err}")
                else:
                    formatted.append(str(item))
            self.failed_textbox.insert("end", "\n".join(formatted))
        else:
            self.failed_textbox.insert("end", "無失敗項目。")
        self.failed_textbox.configure(state="disabled")

    def export_report(self) -> None:
        if not self._last_summary:
            return
            
        file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], initialfile="eagle_tagger_report.txt")
        if file:
            p = self._parse_summary(self._last_summary)
            with open(file, 'w', encoding='utf-8') as f:
                f.write("Eagle AI Tagger 處理報告\n")
                f.write("="*30 + "\n")
                f.write(f"總處理: {p['total']}\n")
                f.write(f"成功: {p['success']}\n")
                f.write(f"失敗: {p['fail']}\n")
                f.write(f"成功率: {p['success_rate']:.2f}%\n")
                f.write(f"產生標籤數: {p['generated_tags']}\n")
                f.write(f"平均每張: {p['avg_tags']:.1f}\n")
                f.write(f"總耗時: {p['total_time']}\n")
                f.write(f"速度: {p['speed']:.1f} it/s\n")
                f.write("="*30 + "\n")
                if self._last_failed:
                    f.write("\n失敗項目:\n")
                    for item in self._last_failed:
                        if isinstance(item, dict):
                            img_path = item.get("image_path", "")
                            err = item.get("error", "未知錯誤")
                            f.write(f"- {img_path}: {err}\n")
                        else:
                            f.write(f"- {item}\n")

    def clear(self) -> None:
        self.show_results({}, [])

    # === 標籤還原功能 ===

    def _refresh_backup_list(self):
        """重新載入備份列表到下拉選單"""
        backups = self._backup_mgr.list_backups()
        self._backups = backups
        if backups:
            names = [
                f"{b['created_at']}（{b['item_count']} 張）"
                for b in backups
            ]
            self.backup_menu.configure(values=names)
            self.backup_menu.set(names[0])
        else:
            self.backup_menu.configure(values=["無備份"])
            self.backup_menu.set("無備份")

    def _on_restore(self):
        """使用者按下還原按鈕"""
        if not self._backups:
            messagebox.showinfo("提示", "沒有可用的備份")
            return

        # 找到選中的備份
        selected = self.backup_menu.get()
        backup_info = None
        for b in self._backups:
            label = f"{b['created_at']}（{b['item_count']} 張）"
            if label == selected:
                backup_info = b
                break

        if not backup_info:
            return

        # 確認對話框
        confirm = messagebox.askyesno(
            "確認還原",
            f"即將還原 {backup_info['item_count']} 張素材的標籤\n"
            f"至備份時間: {backup_info['created_at']}\n\n"
            f"此操作會覆蓋這些素材的現有標籤，確定要繼續嗎？"
        )
        if not confirm:
            return

        # 在背景執行還原
        self.btn_restore.configure(state="disabled", text="還原中...")
        self.restore_status.configure(text="正在還原標籤...", text_color="orange")

        def _do_restore():
            try:
                def progress_cb(current, total):
                    self._restore_queue.put({
                        "status": "progress",
                        "current": current,
                        "total": total,
                    })

                stats = self._backup_mgr.restore_backup(
                    backup_info["path"], progress_cb
                )
                self._restore_queue.put({"status": "done", "stats": stats})
            except Exception as e:
                self._restore_queue.put({"status": "error", "message": str(e)})

        threading.Thread(target=_do_restore, daemon=True).start()
        self.after(200, self._poll_restore)

    def _poll_restore(self):
        """輪詢還原進度"""
        try:
            while True:
                result = self._restore_queue.get_nowait()
                if result["status"] == "progress":
                    c, t = result["current"], result["total"]
                    self.restore_status.configure(
                        text=f"還原中... {c}/{t}"
                    )
                elif result["status"] == "done":
                    stats = result["stats"]
                    self.restore_status.configure(
                        text=f"✅ 還原完成: {stats['restored']} 張成功"
                             f"{'、' + str(stats['errors']) + ' 張失敗' if stats['errors'] else ''}",
                        text_color="green"
                    )
                    self.btn_restore.configure(state="normal", text="還原")
                    return
                elif result["status"] == "error":
                    self.restore_status.configure(
                        text=f"❌ 還原失敗: {result['message']}",
                        text_color="red"
                    )
                    self.btn_restore.configure(state="normal", text="還原")
                    return
        except queue.Empty:
            pass
        self.after(200, self._poll_restore)

    def on_processing_finished(self):
        """處理完成後自動刷新備份列表"""
        self._refresh_backup_list()
