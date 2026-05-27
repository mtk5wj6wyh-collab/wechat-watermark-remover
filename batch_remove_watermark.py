#!/usr/bin/env python3
"""
批量去水印脚本 - 处理 wechat_articles 文件夹
支持增量处理，记录已处理文件

基于水印区域检测 + LaMa 深度学习修复的去水印方案
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# ---------- LaMa 模型（延迟加载） ----------
_lama_model = None
_lama_available = None


def _get_lama_model():
    global _lama_model, _lama_available
    if _lama_available is not None:
        return _lama_model
    try:
        from simple_lama_inpainting import SimpleLama
        _lama_model = SimpleLama()
        _lama_available = True
        return _lama_model
    except Exception:
        _lama_available = False
        return None


# ---------- 水印检测 ----------

def detect_watermark_mask(img, search_region="bottom-left"):
    """
    生成水印区域掩码。

    微信公众号水印位于图片左下角（"ST" Logo + 版权信息）。
    水印位置在所有图片中一致，使用固定矩形掩码覆盖水印区域。

    Args:
        img: BGR 图像
        search_region: 搜索区域 "bottom-left" / "bottom" / "all"

    Returns:
        mask: uint8 掩码
        bbox: (x, y, w, h)
    """
    h, w = img.shape[:2]

    # 水印固定位置：左下角
    # 覆盖 "ST" Logo + 版权信息文字
    wm_h = int(h * 0.12)   # 底部 12% 高度
    wm_w = int(w * 0.40)   # 左侧 40% 宽度

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[h - wm_h:h, 0:wm_w] = 255

    return mask, (0, h - wm_h, wm_w, wm_h)


def dilate_mask(mask, iterations=2):
    """扩张掩码，覆盖水印边缘的半透明过渡区域。"""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.dilate(mask, kernel, iterations=iterations)


# ---------- 图片 I/O（支持中文路径） ----------

def read_image(path):
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path, img, quality=95):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    elif ext == ".png":
        ok, buf = cv2.imencode(".png", img)
    else:
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if ok:
        with open(path, "wb") as f:
            f.write(buf.tobytes())
    return ok


# ---------- 修复算法 ----------

def inpaint_lama(img, mask):
    from PIL import Image
    model = _get_lama_model()
    if model is None:
        raise RuntimeError("LaMa 未安装")
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_mask = Image.fromarray(mask)
    result_pil = model(pil_img, pil_mask)
    return cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)


def inpaint_opencv(img, mask, radius=5):
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)


# ---------- 预设参数 ----------

PRESETS = {
    "light":   {"dilate_iter": 1, "opencv_radius": 3,
                "desc": "轻微修复，适合非常淡的水印"},
    "medium":  {"dilate_iter": 2, "opencv_radius": 5,
                "desc": "中等修复，默认推荐"},
    "heavy":   {"dilate_iter": 3, "opencv_radius": 7,
                "desc": "强力修复，适合较深的水印"},
}


# ---------- 核心处理 ----------

def remove_watermark(img, preset="medium", mask=None):
    params = PRESETS.get(preset, PRESETS["medium"])

    if mask is None:
        mask, _ = detect_watermark_mask(img)
        if mask is None or cv2.countNonZero(mask) == 0:
            return img.copy(), np.zeros(img.shape[:2], dtype=np.uint8)

    mask = dilate_mask(mask, params["dilate_iter"])

    lama = _get_lama_model()
    if lama is not None:
        try:
            result = inpaint_lama(img, mask)
        except Exception as e:
            print(f"    [WARN] LaMa failed: {e}, falling back to OpenCV")
            result = inpaint_opencv(img, mask, params["opencv_radius"])
    else:
        result = inpaint_opencv(img, mask, params["opencv_radius"])

    return result, mask


# ---------- 批量处理 ----------

class BatchWatermarkRemover:
    PROCESSED_LOG = "processed_images.txt"

    def __init__(self, base_dir="wechat_articles"):
        self.base_dir = base_dir

    @staticmethod
    def _read_processed(log_path):
        if not os.path.exists(log_path):
            return set()
        with open(log_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}

    @staticmethod
    def _write_processed(log_path, processed):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"# 已处理图片记录\n")
            f.write(f"# 更新时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"# 总计: {len(processed)} 张\n")
            f.write("=" * 50 + "\n")
            for name in sorted(processed):
                f.write(name + "\n")

    def process_article(self, article_dir, preset="medium", force=False):
        images_dir = os.path.join(article_dir, "images")
        out_dir = os.path.join(article_dir, "images_new")
        log_path = os.path.join(article_dir, self.PROCESSED_LOG)

        if not os.path.exists(images_dir):
            print("  [SKIP] 未找到 images 目录")
            return 0, 0

        Path(out_dir).mkdir(parents=True, exist_ok=True)

        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        all_imgs = [f for f in os.listdir(images_dir)
                    if os.path.splitext(f)[1].lower() in exts]

        if force:
            unprocessed = all_imgs
            processed = set()
            import shutil
            if os.path.exists(out_dir):
                shutil.rmtree(out_dir)
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            print(f"  强制模式: 重新处理全部 {len(all_imgs)} 张")
        else:
            processed = self._read_processed(log_path)
            unprocessed = [f for f in all_imgs if f not in processed]

        if not unprocessed:
            print("  [OK] 全部已处理")
            return len(all_imgs), 0

        print(f"  待处理: {len(unprocessed)} / {len(all_imgs)} 张")

        ok, fail = 0, 0
        for i, name in enumerate(unprocessed, 1):
            inp = os.path.join(images_dir, name)
            outp = os.path.join(out_dir, name)
            try:
                img = read_image(inp)
                if img is None:
                    print(f"    [{i}] [FAIL] 无法读取: {name}")
                    fail += 1
                    continue

                result, _ = remove_watermark(img, preset)

                if write_image(outp, result):
                    processed.add(name)
                    ok += 1
                else:
                    print(f"    [{i}] [FAIL] 保存失败: {name}")
                    fail += 1

                if i % 10 == 0:
                    print(f"    [{i}/{len(unprocessed)}] 已处理...")

            except Exception as e:
                print(f"    [{i}] [FAIL] {name}: {e}")
                fail += 1

        self._write_processed(log_path, processed)
        return ok, fail

    def process_all(self, preset="medium", force=False):
        print("=" * 60)
        print("微信公众号图片批量去水印工具")
        print("=" * 60)
        print(f"工作目录: {os.path.abspath(self.base_dir)}")
        print(f"修复方案: {preset} — {PRESETS[preset]['desc']}")

        lama = _get_lama_model()
        print(f"修复引擎: {'LaMa 深度学习' if lama else 'OpenCV Navier-Stokes（降级）'}")
        print(f"强制模式: {'是' if force else '否'}")
        print()

        if not os.path.exists(self.base_dir):
            print(f"错误: 目录不存在 — {self.base_dir}")
            return

        folders = [d for d in os.listdir(self.base_dir)
                   if os.path.isdir(os.path.join(self.base_dir, d))]
        if not folders:
            print("未找到文章文件夹")
            return

        print(f"找到 {len(folders)} 篇文章")
        print("=" * 60)

        t_ok, t_fail, t_articles = 0, 0, 0
        for i, folder in enumerate(folders, 1):
            print(f"\n[{i}/{len(folders)}] {folder}")
            s, f = self.process_article(
                os.path.join(self.base_dir, folder), preset, force)
            if s > 0 or f > 0:
                t_articles += 1
            t_ok += s
            t_fail += f

        print("\n" + "=" * 60)
        print("处理完成！")
        print(f"文章数: {t_articles}")
        print(f"图片数: 成功 {t_ok} 张，失败 {t_fail} 张")
        print(f"输出位置: {self.base_dir}/<文章名>/images_new/")
        print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="微信公众号图片批量去水印工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
预设:
  light   轻微修复，适合非常淡的水印
  medium  中等修复，默认推荐
  heavy   强力修复，适合较深的水印
""")
    parser.add_argument("-d", "--dir", default="wechat_articles",
                        help="文章目录（默认: wechat_articles）")
    parser.add_argument("-p", "--preset", choices=["light", "medium", "heavy"],
                        default="medium", help="修复预设（默认: medium）")
    parser.add_argument("-f", "--force", action="store_true",
                        help="强制重新处理所有图片")

    args = parser.parse_args()
    remover = BatchWatermarkRemover(args.dir)
    remover.process_all(args.preset, args.force)


if __name__ == "__main__":
    main()
