"""图片处理工具函数"""

import os
import io
from PIL import Image


def compress_image_if_needed(
    image_path: str,
    max_size_mb: float = 5.0,
    max_dimension: int = 1568,
    quality: int = 85,
) -> bytes:
    """
    智能图片压缩：仅在必要时处理

    根据 Claude API 和主流 LLM 最佳实践：
    - 文件大小限制：5MB（Claude）/ 20MB（OpenAI）
    - 推荐尺寸：1568px 长边（Claude）/ 2048px（OpenAI）
    - 推荐质量：85（业界标准）

    Args:
        image_path: 图片文件路径
        max_size_mb: 最大文件大小（MB），默认 5MB
        max_dimension: 最大宽度或高度（像素），默认 1568px
        quality: JPEG 质量（1-95），默认 85

    Returns:
        图片字节数据（原始或压缩后）
    """
    # 检查文件大小
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

    # 打开图片检查尺寸
    img = Image.open(image_path)
    width, height = img.size
    max_current_dimension = max(width, height)

    # 判断是否需要处理
    needs_compression = file_size_mb > max_size_mb
    needs_resize = max_current_dimension > max_dimension

    if not needs_compression and not needs_resize:
        # 图片已经符合要求，直接返回原始文件
        print(f"✓ 图片无需压缩: {file_size_mb:.2f}MB, {width}×{height}px")
        with open(image_path, "rb") as f:
            return f.read()

    # 需要压缩或缩放
    print(f"⚙ 压缩中: {file_size_mb:.2f}MB ({width}×{height}px) → 目标 <{max_size_mb}MB, <{max_dimension}px")

    # 转换 RGBA/LA/P 模式为 RGB（JPEG 不支持透明度）
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        # 使用 alpha 通道作为 mask（如果存在）
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background

    # 缩放图片（保持宽高比）
    if needs_resize:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # 保存为 JPEG 格式（optimize=True 会自动优化编码）
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    compressed_data = output.getvalue()

    compressed_size_mb = len(compressed_data) / (1024 * 1024)
    new_width, new_height = img.size
    print(f"✓ 压缩完成: {compressed_size_mb:.2f}MB ({new_width}×{new_height}px)")

    return compressed_data
