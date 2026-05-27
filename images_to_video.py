#!/usr/bin/env python3
"""
图片组 → 短视频生成工具

将 wechat_articles 文件夹中的图片组制作成短视频。
支持转场效果、背景音乐、文字叠加。

依赖: moviepy, Pillow, numpy
"""

import os
import re
import sys
from pathlib import Path

from moviepy import (
    ImageClip,
    AudioFileClip,
    TextClip,
    concatenate_videoclips,
    vfx,
    afx,
)
import numpy as np
from PIL import Image


# ---------- 图片自然排序 ----------

def natural_sort_key(filename):
    """自然排序 key: 001_xxx < 002_xxx < ... < 010_xxx"""
    return [
        int(c) if c.isdigit() else c.lower()
        for c in re.split(r"(\d+)", filename)
    ]


def load_images(folder):
    """加载文件夹中的图片，按文件名自然排序，返回 (路径列表, 文件名列表)。"""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in exts
    ]
    files.sort(key=natural_sort_key)
    return [os.path.join(folder, f) for f in files], files


# ---------- 视频生成核心 ----------

def make_video(
    image_dir,
    output_path=None,
    duration=3.0,
    fps=24,
    transition="fade",
    transition_dur=0.5,
    music_path=None,
    title=None,
    title_duration=3.0,
    title_color="white",
    title_font_size=48,
    resolution=None,
):
    """
    将图片目录制作成视频。

    Args:
        image_dir:       图片目录（含 images_new/ 或 images/）
        output_path:     输出 MP4 路径（默认: 文章目录/视频.mp4）
        duration:        每张图片停留秒数
        fps:             帧率
        transition:      转场类型 "none" / "fade"
        transition_dur:  转场时长（秒）
        music_path:      背景音乐路径（可选）
        title:           片头标题文字（可选）
        title_duration:  标题显示时长
        title_color:     标题颜色
        title_font_size: 标题字号
        resolution:      (w, h) 分辨率，默认取第一张图片尺寸
    """
    # 找图片目录
    images_new = os.path.join(image_dir, "images_new")
    images_old = os.path.join(image_dir, "images")
    if os.path.isdir(images_new):
        img_dir = images_new
    elif os.path.isdir(images_old):
        img_dir = images_old
    else:
        print(f"[ERROR] 未找到图片目录: {images_new} 或 {images_old}")
        return None

    # 加载图片
    img_paths, img_names = load_images(img_dir)
    if not img_paths:
        print(f"[ERROR] 目录中无图片: {img_dir}")
        return None

    print(f"  图片数: {len(img_paths)}")
    print(f"  每张停留: {duration}s")
    print(f"  转场: {transition} ({transition_dur}s)")
    print(f"  FPS: {fps}")

    # 确定分辨率
    if resolution is None:
        with Image.open(img_paths[0]) as im:
            resolution = im.size  # (w, h)
    target_w, target_h = resolution
    print(f"  分辨率: {target_w}x{target_h}")

    # 创建图片片段
    clips = []

    # 片头标题
    if title:
        print(f"  标题: {title}")
        txt_clip = TextClip(
            text=title,
            font_size=title_font_size,
            color=title_color,
            bg_color="black",
            size=(target_w, target_h),
            method="caption",
            transparent=False,
        ).with_duration(title_duration)

        if transition == "fade":
            txt_clip = txt_clip.with_effects([
                vfx.CrossFadeIn(transition_dur),
                vfx.CrossFadeOut(transition_dur),
            ])
        clips.append(txt_clip)

    # 图片片段
    for i, path in enumerate(img_paths):
        try:
            clip = ImageClip(path).with_duration(duration)

            # 缩放到目标分辨率
            if clip.size != (target_w, target_h):
                clip = clip.resized((target_w, target_h))

            # 添加转场
            if transition == "fade":
                effects = []
                if i > 0 or title:
                    effects.append(vfx.CrossFadeIn(transition_dur))
                if i < len(img_paths) - 1:
                    effects.append(vfx.CrossFadeOut(transition_dur))
                if effects:
                    clip = clip.with_effects(effects)

            clips.append(clip)

            if (i + 1) % 10 == 0:
                print(f"    [{i + 1}/{len(img_paths)}] 已加载...")

        except Exception as e:
            print(f"    [WARN] 跳过 {os.path.basename(path)}: {e}")

    if not clips:
        print("[ERROR] 无可用水印片段")
        return None

    print(f"  正在合成 {len(clips)} 个片段...")

    # 合成
    if transition == "fade":
        final = concatenate_videoclips(clips, method="compose", padding=-transition_dur)
    else:
        final = concatenate_videoclips(clips, method="compose")

    # 添加背景音乐
    if music_path and os.path.exists(music_path):
        print(f"  背景音乐: {os.path.basename(music_path)}")
        audio = AudioFileClip(music_path)
        # 循环或裁剪音乐以匹配视频时长
        if audio.duration < final.duration:
            loops = int(final.duration / audio.duration) + 1
            from moviepy import concatenate_audioclips
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclipped(0, final.duration)
        audio = audio.with_effects([afx.AudioFadeOut(1.0)])
        final = final.with_audio(audio)

    # 输出路径
    if output_path is None:
        article_name = os.path.basename(image_dir)
        output_path = os.path.join(image_dir, f"{article_name}.mp4")

    print(f"  输出: {output_path}")

    # 写入视频
    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )

    print(f"  完成! 时长: {final.duration:.1f}s")
    return output_path


# ---------- 批量处理 ----------

def process_all(base_dir="wechat_articles", **kwargs):
    """处理 base_dir 下所有文章文件夹。"""
    if not os.path.exists(base_dir):
        print(f"[ERROR] 目录不存在: {base_dir}")
        return

    folders = sorted([
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ])

    if not folders:
        print("未找到文章文件夹")
        return

    print(f"找到 {len(folders)} 篇文章")
    print("=" * 50)

    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] {folder}")
        article_dir = os.path.join(base_dir, folder)
        make_video(article_dir, **kwargs)


# ---------- CLI ----------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="图片组 → 短视频生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python images_to_video.py -d "wechat_articles/天 沐 琴 台"
  python images_to_video.py -d "wechat_articles/天 沐 琴 台" -t 5 --title "天 沐 琴 台"
  python images_to_video.py -d "wechat_articles/天 沐 琴 台" --music bgm.mp3 --transition fade
  python images_to_video.py -d "wechat_articles" --all -t 3
""")
    parser.add_argument("-d", "--dir", default="wechat_articles",
                        help="文章目录或父目录（默认: wechat_articles）")
    parser.add_argument("--all", action="store_true",
                        help="处理目录下所有文章")
    parser.add_argument("-t", "--time", type=float, default=3.0,
                        help="每张图片停留秒数（默认: 3）")
    parser.add_argument("--fps", type=int, default=24,
                        help="帧率（默认: 24）")
    parser.add_argument("--transition", choices=["none", "fade"], default="fade",
                        help="转场效果（默认: fade）")
    parser.add_argument("--transition-dur", type=float, default=0.5,
                        help="转场时长秒数（默认: 0.5）")
    parser.add_argument("--music", default=None,
                        help="背景音乐文件路径")
    parser.add_argument("--title", default=None,
                        help="片头标题文字")
    parser.add_argument("--title-duration", type=float, default=3.0,
                        help="标题显示时长（默认: 3）")
    parser.add_argument("--title-color", default="white",
                        help="标题颜色（默认: white）")
    parser.add_argument("--title-font-size", type=int, default=48,
                        help="标题字号（默认: 48）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件路径（仅单文章模式）")
    parser.add_argument("--resolution", default=None,
                        help="输出分辨率 WxH（默认: 与图片一致）")

    args = parser.parse_args()

    resolution = None
    if args.resolution:
        w, h = args.resolution.lower().split("x")
        resolution = (int(w), int(h))

    kwargs = dict(
        duration=args.time,
        fps=args.fps,
        transition=args.transition,
        transition_dur=args.transition_dur,
        music_path=args.music,
        title=args.title,
        title_duration=args.title_duration,
        title_color=args.title_color,
        title_font_size=args.title_font_size,
        output_path=args.output,
        resolution=resolution,
    )

    if args.all:
        process_all(args.dir, **kwargs)
    else:
        print("=" * 50)
        print("图片组 → 短视频生成工具")
        print("=" * 50)
        make_video(args.dir, **kwargs)


if __name__ == "__main__":
    main()
