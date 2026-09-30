import queue
import threading
import time
import traceback
from pathlib import Path
from typing import Optional, Tuple

from main.unified_config import UnifiedConfig
from main.task_dispatcher import TaskDispatcher
from main.process_pool_manager import ProcessPoolManager
from main.result_collector import ResultCollector
from main.check_update import VersionChecker

class BackendController:
    """推理流程控制器 — GUI 版的 mainp.main() 替代品"""

    def __init__(self, config: UnifiedConfig):
        self.config = config
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.pool_manager: Optional[ProcessPoolManager] = None

    def start(self, image_data: list, progress_queue: queue.Queue):
        """啟動背景推理執行緒"""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, 
            args=(image_data, progress_queue),
            daemon=True
        )
        self._thread.start()

    def _run(self, image_data: list, progress_queue: queue.Queue):
        """在背景執行緒中執行完整推理流程
        
        Queue message format:
          {'type': 'log',      'message': str}
          {'type': 'progress', 'processed': int, 'total': int,
                               'speed': float, 'eta': float,
                               'success': int, 'fail': int,
                               'active_workers': int}
          {'type': 'batch',    'batch_id': int, 'success_count': int, 'batch_size': int}
          {'type': 'finished', 'summary': dict}
          {'type': 'error',    'message': str}
          {'type': 'writing_json', 'current': int, 'total': int}  # JSON write progress
        """
        try:
            progress_queue.put({'type': 'log', 'message': f"找到圖片數量: {len(image_data)}"})
            if not image_data:
                progress_queue.put({'type': 'log', 'message': "沒有需要處理的圖片"})
                progress_queue.put({'type': 'finished', 'summary': {}, 'failed_images': []})
                return

            # 備份原始標籤
            progress_queue.put({'type': 'log', 'message': "正在備份原始標籤..."})
            from gui.tag_backup import TagBackupManager
            backup_mgr = TagBackupManager()

            def backup_progress(current, total):
                progress_queue.put({
                    'type': 'log',
                    'message': f"備份標籤中... {current}/{total}"
                })

            backup_path = backup_mgr.create_backup(image_data, backup_progress)
            progress_queue.put({
                'type': 'log',
                'message': f"標籤備份完成: {backup_path.name}"
            })
            self._last_backup_path = backup_path

            progress_queue.put({'type': 'log', 'message': "正在初始化組件..."})
            dispatcher = TaskDispatcher(self.config)
            self.pool_manager = ProcessPoolManager(self.config)
            result_collector = ResultCollector(self.config)

            if self._stop_event.is_set():
                progress_queue.put({'type': 'log', 'message': "處理已被使用者中斷"})
                return

            batches = dispatcher.create_batches(image_data)
            progress_queue.put({'type': 'log', 'message': f"已創建 {len(batches)} 個處理批次"})

            worker_config = self.config.to_dict()
            self.pool_manager.start_workers(worker_config)

            if self._stop_event.is_set():
                progress_queue.put({'type': 'log', 'message': "處理已被使用者中斷"})
                return

            progress_queue.put({'type': 'log', 'message': "開始處理圖片..."})
            self.pool_manager.submit_tasks(batches)
            
            completed_batches = 0
            total_batches = len(batches)
            
            start_time = time.time()
            last_update_time = 0.0

            while completed_batches < total_batches:
                if self._stop_event.is_set():
                    progress_queue.put({'type': 'log', 'message': "處理已被使用者中斷"})
                    break
                    
                result = self.pool_manager.get_results(timeout=1.0)
                
                if 'error' in result:
                    if result['error'] == '获取结果超时':
                        continue
                    progress_queue.put({'type': 'log', 'message': f"獲取結果出錯: {result['error']}"})
                    continue
                    
                result_collector.add_result(result)
                completed_batches += 1
                
                results_list = result.get('results', [])
                batch_size = len(results_list)
                dispatcher.update_progress(batch_size)
                
                success_count = sum(1 for res in results_list if res.get('success', False))
                
                progress_queue.put({
                    'type': 'batch',
                    'batch_id': completed_batches,
                    'success_count': success_count,
                    'batch_size': batch_size
                })
                
                current_time = time.time()
                if current_time - last_update_time >= 0.5 or completed_batches == total_batches:
                    elapsed = current_time - start_time
                    processed = dispatcher.processed_images
                    total = dispatcher.total_images
                    
                    speed = processed / elapsed if elapsed > 0 else 0.0
                    remaining = total - processed
                    eta = remaining / speed if speed > 0 else 0.0
                    
                    summary = result_collector.get_summary()
                    
                    # 嘗試獲取 active_workers，如果 process_pool_manager 有對應的方法或狀態
                    active_workers = 0
                    if hasattr(self.pool_manager, 'monitor_workers'):
                        monitor_data = self.pool_manager.monitor_workers()
                        active_workers = monitor_data.get('active_workers', 0)
                    
                    progress_queue.put({
                        'type': 'progress',
                        'processed': processed,
                        'total': total,
                        'speed': speed,
                        'eta': eta,
                        'success': summary.get('success_count', 0),
                        'fail': summary.get('failure_count', 0),
                        'active_workers': active_workers
                    })
                    last_update_time = current_time

                if completed_batches % 10 == 0:
                    summary = result_collector.get_summary()
                    avg_time = summary['total_processing_time'] / completed_batches if completed_batches > 0 else 0
                    dispatcher.adjust_batch_size(
                        summary['success_rate'] / 100, 
                        avg_time
                    )

            if not self._stop_event.is_set():
                progress_queue.put({'type': 'log', 'message': "正在更新 JSON 檔案..."})
                
                progress_queue.put({'type': 'writing_json', 'current': 0, 'total': 1})
                result_collector.update_json_files()
                progress_queue.put({'type': 'writing_json', 'current': 1, 'total': 1})
                
                progress_queue.put({'type': 'log', 'message': "正在生成報告..."})
                result_collector.generate_report()
                
                summary = result_collector.get_summary()
                failed_images = result_collector.get_failed_images()
                progress_queue.put({
                    'type': 'finished', 
                    'summary': summary,
                    'failed_images': failed_images
                })

        except Exception as e:
            error_msg = traceback.format_exc()
            progress_queue.put({'type': 'error', 'message': f"處理過程中發生錯誤: {e}\n{error_msg}"})
        finally:
            progress_queue.put({'type': 'log', 'message': "正在清理資源..."})
            if self.pool_manager:
                self.pool_manager.shutdown()

    def stop(self):
        """使用者點擊停止 → 安全終止"""
        self._stop_event.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def parse_image_list(img_list_path: Path) -> list:
        """解析圖片清單檔案 (from mainp.get_image_list_info)"""
        with img_list_path.open('r', encoding='utf-8') as f:
            img_paths = [Path(line.strip()).resolve() for line in f if line.strip()]
        return [
            {'image_path': str(img_path), 'json_path': str(img_path.parent / 'metadata.json')}
            for img_path in img_paths
        ]

    @staticmethod
    def parse_image_list_from_text(text: str) -> list:
        """從文字內容解析圖片清單 (用於剪貼簿貼上)"""
        img_paths = [Path(line.strip()).resolve() for line in text.splitlines() if line.strip()]
        return [
            {'image_path': str(img_path), 'json_path': str(img_path.parent / 'metadata.json')}
            for img_path in img_paths
        ]

    @staticmethod  
    def check_version(config: UnifiedConfig) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """非阻塞版本檢查 (繞過 check_for_update 的 input())"""
        checker = VersionChecker(config)
        local_version = checker.get_local_version()
        remote_version, update_notes = checker.get_remote_version()
        return local_version, remote_version, update_notes
