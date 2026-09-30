from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
import time
import json
from .unified_config import UnifiedConfig


class ResultCollector:
    """结果收集器"""

    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.results: List[Dict] = []
        self.start_time = time.time()
        self.success_count = 0
        self.failure_count = 0
        self.total_tags = 0

    def add_result(self, result: Dict[str, Any]):
        batch_results = result.get("results", [])
        for item in batch_results:
            self.results.append(item)
            if item.get("success", False):
                self.success_count += 1
                self.total_tags += len(item.get("tags", []))
            else:
                self.failure_count += 1
        # 简化批次完成日志，避免干扰进度条
        success_count = sum(r["success"] for r in batch_results)
        if success_count < len(batch_results):
            print(
                f"\n批次 {result.get('batch_id')} 处理完成: 成功 {success_count}/{len(batch_results)}"
            )

    def update_json_files(self):
        """批量更新JSON（在结果合并后）"""
        for result in self.results:
            if result.get("success", False):
                json_path = Path(result["json_path"])
                new_tags = result["tags"]
                try:
                    if not json_path.exists():
                        data = {
                            "tags": new_tags,
                            "annotation": f"AI标注于 {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        }
                    else:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    if self.config.process.add_write_mode:
                        existing_tags = data.get("tags", [])
                        combined_tags = list(set(existing_tags + new_tags))
                        data["tags"] = combined_tags
                    else:
                        data["tags"] = new_tags
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                except Exception as e:
                    print(f"更新文件失败: {json_path}，错误信息: {e}")

    def get_summary(self) -> Dict[str, Any]:
        total_images = self.success_count + self.failure_count
        processing_time = time.time() - self.start_time
        avg_tags_per_image = (
            self.total_tags / self.success_count if self.success_count > 0 else 0
        )
        success_rate = (
            (self.success_count / total_images * 100) if total_images > 0 else 0
        )
        images_per_second = (
            total_images / processing_time if processing_time > 0 else 0
        )
        return {
            "total_images": total_images,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "total_tags_generated": self.total_tags,
            "avg_tags_per_image": avg_tags_per_image,
            "total_processing_time": processing_time,
            "images_per_second": images_per_second,
            # GUI 相容欄位別名
            "total": total_images,
            "success": self.success_count,
            "fail": self.failure_count,
            "generated_tags": self.total_tags,
            "avg_tags": avg_tags_per_image,
            "total_time": f"{processing_time:.1f}s",
            "speed": images_per_second,
        }

    def get_failed_images(self) -> List[Dict]:
        return [
            {"image_path": r["image_path"], "error": r.get("error", "未知错误")}
            for r in self.results
            if not r.get("success", False)
        ]

    def generate_report(self):
        """生成报告"""
        if self.config.report.create_csv_report:
            csv_data = [
                {
                    "image_path": r["image_path"],
                    "success": r.get("success", False),
                    "tags": ", ".join(r.get("tags", [])),
                    "tag_count": len(r.get("tags", [])),
                    "error": r.get("error", "无"),
                }
                for r in self.results
            ]
            df = pd.DataFrame(csv_data)
            csv_path = "processing_report.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"CSV报告已生成: {csv_path}")

        summary = self.get_summary()
        report_path = "图像标注处理报告.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("图像标注处理报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"处理时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总图像数: {summary['total_images']}\n")
            f.write(f"成功标注: {summary['success_count']}\n")
            f.write(f"失败标注: {summary['failure_count']}\n")
            f.write(f"成功率: {summary['success_rate']:.2f}%\n")
            f.write(f"生成标签总数: {summary['total_tags_generated']}\n")
            f.write(f"平均每张图像标签数: {summary['avg_tags_per_image']:.2f}\n")
            f.write(f"总处理时间: {summary['total_processing_time']:.2f}秒\n")
            f.write(f"处理速度: {summary['images_per_second']:.2f} 图像/秒\n")
            failed = self.get_failed_images()
            if failed:
                f.write("\n失败图像列表:\n")
                for item in failed:
                    f.write(f"- {item['image_path']}: {item['error']}\n")
        print(f"处理摘要已生成: {report_path}")
        return summary
