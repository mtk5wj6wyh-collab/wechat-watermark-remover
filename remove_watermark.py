#!/usr/bin/env python3
"""
微信公众号图片去水印工具（单张/文件夹）
基于水印区域检测 + LaMa 深度学习修复
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import argparse

# 从 batch_remove_watermark 复用核心函数
from batch_remove_watermark import (
    detect_watermark_mask, dilate_mask, read_image, write_image,
    inpaint_lama, inpaint_opencv, PRESETS, _get_lama_model,
)


class WatermarkRemover:
    def process_image(self, input_path, output_path, preset="medium"):
        """处理单张图片。"""
        img = read_image(input_path)
        if img is None:
            print(f"  [FAIL] 无法读取: {input_path}")
            return False

        params = PRESETS.get(preset, PRESETS["medium"])
        mask = detect_watermark_mask(img)
        has_wc = mask is not None and cv2.countNonZero(mask) > 0

        if has_wc:
            mask = dilate_mask(mask, params["dilate_iter"])
            lama = _get_lama_model()
            if lama is not None:
                try:
                    result = inpaint_lama(img, mask)
                except Exception:
                    result = inpaint_opencv(img, mask, params["opencv_radius"])
            else:
                result = inpaint_opencv(img, mask, params["opencv_radius"])
        else:
            print("  [INFO] 未检测到水印")
            result = img.copy()

        if write_image(output_path, result):
            return True
        print(f"  [FAIL] 保存失败: {output_path}")
        return False

    def process_folder(self, input_dir, output_dir=None, preset="medium"):
        """批量处理文件夹中的图片。"""
        if output_dir is None:
            output_dir = input_dir + "_no_watermark"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        files = [f for f in Path(input_dir).iterdir()
                 if f.suffix.lower() in exts]

        if not files:
            print(f"未找到图片: {input_dir}")
            return

        print(f"找到 {len(files)} 张图片")
        print(f"预设: {preset} — {PRESETS[preset]['desc']}")
        print(f"输出: {output_dir}")
        print("=" * 50)

        ok, fail = 0, 0
        for i, fp in enumerate(files, 1):
            out = os.path.join(output_dir, fp.name)
            tag = f"[{i}/{len(files)}] {fp.name}"
            if self.process_image(str(fp), out, preset):
                print(f"{tag} [OK]")
                ok += 1
            else:
                print(f"{tag} [FAIL]")
                fail += 1

        print("=" * 50)
        print(f"完成: 成功 {ok} 张，失败 {fail} 张")
        print(f"输出: {os.path.abspath(output_dir)}")


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号图片去水印工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
预设:
  light   轻微修复，适合非常淡的水印
  medium  中等修复，默认推荐
  heavy   强力修复，适合较深的水印
""")
    parser.add_argument("input", help="输入图片路径或文件夹路径")
    parser.add_argument("-o", "--output", help="输出路径（默认在原目录后加 _no_watermark）")
    parser.add_argument("-p", "--preset", choices=["light", "medium", "heavy"],
                        default="medium", help="修复预设（默认: medium）")

    args = parser.parse_args()
    remover = WatermarkRemover()

    if os.path.isfile(args.input):
        out = args.output
        if not out:
            name, ext = os.path.splitext(args.input)
            out = f"{name}_no_watermark{ext}"
        print(f"输入: {args.input}")
        print(f"输出: {out}")
        print(f"预设: {args.preset}")
        if remover.process_image(args.input, out, args.preset):
            print("完成！")
        else:
            print("失败！")
            sys.exit(1)

    elif os.path.isdir(args.input):
        remover.process_folder(args.input, args.output, args.preset)

    else:
        print(f"错误: 路径不存在 — {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
