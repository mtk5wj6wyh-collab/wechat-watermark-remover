#!/usr/bin/env python3
"""
去水印工具使用示例
"""

from remove_watermark import WatermarkRemover


def example_single_image():
    """处理单张图片"""
    remover = WatermarkRemover()

    remover.process_image(
        input_path="downloaded_images/001_32ac7a98.jpg",
        output_path="downloaded_images/001_32ac7a98_clean.jpg",
        preset="medium",
    )


def example_batch_folder():
    """批量处理整个文件夹"""
    remover = WatermarkRemover()

    remover.process_folder(
        input_dir="downloaded_images",
        output_dir="downloaded_images_clean",
        preset="medium",
    )


def example_compare_presets():
    """对比不同修复强度的效果"""
    remover = WatermarkRemover()
    input_path = "downloaded_images/001_32ac7a98.jpg"

    for preset in ("light", "medium", "heavy"):
        out = f"downloaded_images/test_{preset}.jpg"
        print(f"\n测试预设: {preset}")
        remover.process_image(input_path, out, preset)


if __name__ == "__main__":
    print("=== 去水印工具示例 ===\n")

    print("1. 批量处理文件夹（推荐）")
    example_batch_folder()

    # 如需测试其他功能，取消注释：
    # print("\n2. 处理单张图片")
    # example_single_image()
    #
    # print("\n3. 对比不同预设")
    # example_compare_presets()
