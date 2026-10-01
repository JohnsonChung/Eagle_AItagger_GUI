import re
from pathlib import Path
from typing import Dict, Tuple
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
import pandas as pd

# 注册 HEIC/HEIF 格式支持
register_heif_opener()
import numpy as np
from onnxruntime import InferenceSession
from .image_utils import ImageUtils  # 导入预处理工具


class WaifuDiffusionInterrogator:
    """WD14模型实现"""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.tags = None

    def load(self):
        """加载模型和标签"""
        self.model = InferenceSession(
            str(self.config.model.model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.tags = pd.read_csv(self.config.model.tags_path)
        print(f"从{self.config.model.model_path}加载模型")

    def unload(self):
        """卸载模型"""
        if self.model is not None:
            del self.model
            self.model = None
            print("卸载模型")
        return True

    def interrogate(self, image: Image.Image) -> Tuple[Dict, Dict]:
        """执行图像分析"""
        input_shape = self.model.get_inputs()[0].shape

        # 自動偵測 NCHW / NHWC
        if len(input_shape) == 4 and input_shape[1] == 3:
            # NCHW: [batch, 3, H, W]
            target_size = input_shape[2]
            is_nchw = True
        else:
            # NHWC: [batch, H, W, 3]
            target_size = input_shape[1]
            is_nchw = False

        processed = ImageUtils.preprocess_image(image, target_size)

        # NCHW 模型需要轉置: [1,H,W,3] → [1,3,H,W]
        if is_nchw:
            processed = processed.transpose(0, 3, 1, 2)

        # 模型推理
        input_name = self.model.get_inputs()[0].name
        output_name = self.model.get_outputs()[0].name
        confs = self.model.run([output_name], {input_name: processed})[0][0]

        # 验证标签列和置信度对齐
        tag_col = "right_tag_cn" if self.config.tag.use_chinese_name else "name"

        total_tags = len(self.tags)
        if len(confs) != total_tags:
            raise ValueError(
                f"模型输出置信度数量({len(confs)})与标签数量({total_tags})不匹配"
            )

        # 分割评分和普通标签
        ratings = dict(zip(self.tags.head(4)[tag_col], confs[:4]))
        tags = dict(zip(self.tags[4:][tag_col], confs[4:]))

        return ratings, tags


class TaggerService:
    """标签生成服务"""

    def __init__(self, config):
        self.config = config
        self.interrogator = WaifuDiffusionInterrogator(config)
        self.interrogator.load()
        self.TAG_ESCAPE_PATTERN = re.compile(r"([\\()])")

    def process_single_image(self, image_path: Path) -> Dict[str, float]:
        """处理单张图像，返回处理后的标签"""
        try:
            with Image.open(image_path) as img:
                _, raw_tags = self.interrogator.interrogate(img)
                return self.process_tags(raw_tags)
        except (IOError, UnidentifiedImageError) as e:
            print(f"处理图片时出错 {image_path}: {str(e)}")
        return {}

    def process_tags(self, raw_tags: Dict[str, float]) -> Dict[str, float]:
        """处理标签"""
        tags = raw_tags.copy()

        if self.config.tag.additional_tags:
            tags.update(
                {tag: 1.0 for tag in self.config.tag.additional_tags if tag not in tags}
            )

        filtered = {
            tag: conf for tag, conf in tags.items() if conf >= self.config.tag.threshold
        }

        if self.config.tag.exclude_tags:
            filtered = {
                tag: conf
                for tag, conf in filtered.items()
                if tag not in self.config.tag.exclude_tags
            }

        # 过滤非法字符
        illegal_chars = {"[", "]", ",", "(", ")", "\\"}
        valid_tags = {
            tag: conf
            for tag, conf in filtered.items()
            if not (len(tag) == 1 and tag in illegal_chars)
        }

        # 排序
        sorted_tags = sorted(
            valid_tags.items(),
            key=lambda x: (
                (-x[1], x[0]) if not self.config.tag.sort_alphabetically else x[0]
            ),
        )

        processed = []
        for tag, conf in sorted_tags:
            new_tag = tag
            if self.config.tag.replace_underscore:
                if tag not in self.config.tag.underscore_excludes:
                    new_tag = new_tag.replace("_", " ")
            if self.config.tag.escape_tags:
                new_tag = self.TAG_ESCAPE_PATTERN.sub(r"\\\1", new_tag)
            processed.append((new_tag, conf))

        return dict(processed)

    def unload(self):
        self.interrogator.unload()
