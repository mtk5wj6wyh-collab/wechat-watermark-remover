#!/usr/bin/env python3
"""
图片组 → 短视频 (专业版)

支持自定义剧本、中文配音、字幕、背景音乐。

剧本格式 (script.txt):
  每行对应一张图片，按顺序匹配。
  空行跳过。以 # 开头的行是注释。

  # 这是注释
  第一张图片的配音文字和字幕内容
  第二张图片的配音文字和字幕内容

用法:
  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台"
  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台" --script script.txt
  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台" --voice zh-CN-YunxiNeural --music bgm.mp3
"""

import os
import re
import sys
import asyncio
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ---------- 剧本解析 ----------

def parse_script(script_path):
    """
    解析剧本文件，返回 [(text, image_index), ...]
    每行文字对应第 N 张图片（从 0 开始）。
    """
    segments = []
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            segments.append(line)
    return segments


def load_images(folder):
    """加载图片目录，按文件名自然排序。"""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files = sorted(
        [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts],
        key=lambda x: [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", x)],
    )
    return [os.path.join(folder, f) for f in files]


# ---------- TTS 配音 ----------

async def generate_tts(text, output_path, voice="zh-CN-YunxiNeural", rate="+0%"):
    """用 edge-tts 生成单段配音 MP3。"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


async def generate_all_tts(segments, output_dir, voice="zh-CN-YunxiNeural", rate="+0%"):
    """批量生成所有段落的配音。"""
    os.makedirs(output_dir, exist_ok=True)
    tasks = []
    for i, text in enumerate(segments):
        mp3_path = os.path.join(output_dir, f"seg_{i:04d}.mp3")
        tasks.append(generate_tts(text, mp3_path, voice, rate))
    # 串行执行，避免并发过高
    for task in tasks:
        await task
    return [os.path.join(output_dir, f"seg_{i:04d}.mp3") for i in range(len(segments))]


# ---------- 字幕渲染 ----------

def find_cjk_font():
    """查找系统中可用的中文字体。"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",      # Microsoft YaHei
        "C:/Windows/Fonts/msyhbd.ttc",     # Microsoft YaHei Bold
        "C:/Windows/Fonts/simsun.ttc",     # SimSun
        "C:/Windows/Fonts/simhei.ttf",     # SimHei
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def render_subtitle_frame(img_array, text, font_size=36, max_width_ratio=0.85):
    """
    在图片底部渲染字幕。
    白色文字 + 黑色描边，半透明黑色底条。
    返回新的 numpy 数组。
    """
    pil_img = Image.fromarray(img_array).convert("RGBA")
    w, h = pil_img.size

    # 创建字幕层
    txt_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # 加载字体
    font_path = find_cjk_font()
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    # 自动换行
    max_width = int(w * max_width_ratio)
    lines = wrap_text(draw, text, font, max_width)

    # 计算字幕区域高度
    line_height = font_size + 8
    total_height = len(lines) * line_height + 20

    # 绘制半透明黑色底条
    bar_y = h - total_height - 15
    draw.rectangle(
        [(0, bar_y), (w, h)],
        fill=(0, 0, 0, 140),
    )

    # 绘制文字（黑色描边 + 白色填充）
    y = bar_y + 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2

        # 黑色描边
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        # 白色文字
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    # 合成
    result = Image.alpha_composite(pil_img, txt_layer)
    return np.array(result.convert("RGB"))


def wrap_text(draw, text, font, max_width):
    """中文文本自动换行。"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ---------- 视频合成核心 ----------

def make_video_pro(
    image_dir,
    script_path=None,
    output_path=None,
    voice="zh-CN-YunxiNeural",
    voice_rate="+0%",
    music_path=None,
    music_volume=0.3,
    font_size=36,
    fps=24,
    resolution=None,
):
    """
    专业版视频生成：图片 + 配音 + 字幕 + 背景音乐。

    Args:
        image_dir:       图片目录
        script_path:     剧本文件路径（每行对应一张图片）
        output_path:     输出 MP4 路径
        voice:           edge-tts 语音名称
        voice_rate:      语速调整 ("+0%", "-20%", "+10%" 等)
        music_path:      背景音乐路径
        music_volume:    背景音乐音量 (0.0-1.0)
        font_size:       字幕字号
        fps:             帧率
        resolution:      (w, h) 分辨率
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, afx
    import edge_tts

    # 找图片目录
    images_new = os.path.join(image_dir, "images_new")
    images_old = os.path.join(image_dir, "images")
    img_dir = images_new if os.path.isdir(images_new) else images_old
    if not os.path.isdir(img_dir):
        print(f"[ERROR] 未找到图片目录: {img_dir}")
        return None

    # 加载图片
    img_paths = load_images(img_dir)
    if not img_paths:
        print(f"[ERROR] 无图片: {img_dir}")
        return None

    # 加载或生成剧本
    if script_path and os.path.exists(script_path):
        segments = parse_script(script_path)
        print(f"  剧本: {len(segments)} 段")
    else:
        # 无剧本时，每张图片用空文本（仅展示，无配音）
        segments = [""] * len(img_paths)
        print("  无剧本，生成纯画面视频")

    # 对齐图片和剧本
    n = min(len(img_paths), len(segments))
    img_paths = img_paths[:n]
    segments = segments[:n]
    print(f"  图片: {n} 张")

    # 确定分辨率
    if resolution is None:
        with Image.open(img_paths[0]) as im:
            resolution = im.size
    target_w, target_h = resolution
    print(f"  分辨率: {target_w}x{target_h}")
    print(f"  语音: {voice}")
    print(f"  背景音乐: {os.path.basename(music_path) if music_path else '无'}")

    # 生成 TTS 配音
    tts_dir = tempfile.mkdtemp(prefix="wechat_tts_")
    has_voice = any(s.strip() for s in segments)

    if has_voice:
        print("  生成配音...")
        tts_files = asyncio.run(
            generate_all_tts(segments, tts_dir, voice=voice, rate=voice_rate)
        )
        print("  配音生成完成")
    else:
        tts_files = [""] * n

    # 创建片段
    clips = []
    for i in range(n):
        try:
            # 加载并缩放图片
            img = Image.open(img_paths[i])
            if img.size != (target_w, target_h):
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            img_array = np.array(img)

            # 渲染字幕
            text = segments[i].strip()
            if text:
                img_array = render_subtitle_frame(img_array, text, font_size=font_size)

            # 加载音频获取时长
            if has_voice and tts_files[i] and os.path.exists(tts_files[i]):
                audio_clip = AudioFileClip(tts_files[i])
                # 多留 0.5 秒间隔
                duration = audio_clip.duration + 0.5
            else:
                audio_clip = None
                duration = 3.0

            # 创建视频片段
            clip = ImageClip(img_array).with_duration(duration)
            if audio_clip:
                clip = clip.with_audio(audio_clip)

            clips.append(clip)

            if (i + 1) % 10 == 0:
                print(f"    [{i + 1}/{n}] 已处理...")

        except Exception as e:
            print(f"    [WARN] 跳过 {os.path.basename(img_paths[i])}: {e}")

    if not clips:
        print("[ERROR] 无可用水印片段")
        return None

    # 合成
    print(f"  正在合成 {len(clips)} 个片段...")
    from moviepy import concatenate_videoclips
    final = concatenate_videoclips(clips, method="compose")

    # 混入背景音乐
    if music_path and os.path.exists(music_path):
        print(f"  混入背景音乐: {os.path.basename(music_path)}")
        bgm = AudioFileClip(music_path)
        # 循环背景音乐
        if bgm.duration < final.duration:
            from moviepy import concatenate_audioclips
            loops = int(final.duration / bgm.duration) + 1
            bgm = concatenate_audioclips([bgm] * loops)
        bgm = bgm.subclipped(0, final.duration)
        # 降低背景音乐音量
        bgm = bgm.with_effects([afx.MultiplyVolume(music_volume)])
        # 混合：配音 + 背景音乐
        if final.audio:
            from moviepy import CompositeAudioClip
            mixed = CompositeAudioClip([final.audio, bgm])
            final = final.with_audio(mixed)
        else:
            final = final.with_audio(bgm)

    # 输出
    if output_path is None:
        article_name = os.path.basename(image_dir)
        output_path = os.path.join(image_dir, f"{article_name}_pro.mp4")

    print(f"  输出: {output_path}")
    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )

    total_dur = final.duration
    print(f"  完成! 时长: {total_dur:.1f}s ({total_dur/60:.1f}min)")
    return output_path


# ---------- CLI ----------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="图片组 → 短视频 (专业版: 配音+字幕+音乐)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
剧本格式 (script.txt):
  每行对应一张图片，空行跳过，# 开头为注释。

示例:
  # 横琴天沐琴台
  天沐琴台，横琴新区的标志性建筑
  曲线优美的屋顶设计，如同展翅的飞鸟
  宽阔的桥面连接着两岸
  夜晚的灯光更是美轮美奂

  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台" --script script.txt
  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台" --script script.txt --voice zh-CN-XiaoxiaoNeural
  python images_to_video_pro.py -d "wechat_articles/天 沐 琴 台" --script script.txt --music bgm.mp3
""")
    parser.add_argument("-d", "--dir", required=True, help="文章目录")
    parser.add_argument("-s", "--script", default=None, help="剧本文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出 MP4 路径")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural",
                        help="edge-tts 语音 (默认: zh-CN-YunxiNeural)")
    parser.add_argument("--voice-rate", default="+0%",
                        help="语速调整 (默认: +0%%, 可用 -20%%/%%+10%% 等)")
    parser.add_argument("--music", default=None, help="背景音乐路径")
    parser.add_argument("--music-volume", type=float, default=0.3,
                        help="背景音乐音量 0.0-1.0 (默认: 0.3)")
    parser.add_argument("--font-size", type=int, default=36,
                        help="字幕字号 (默认: 36)")
    parser.add_argument("--fps", type=int, default=24, help="帧率 (默认: 24)")
    parser.add_argument("--resolution", default=None,
                        help="输出分辨率 WxH (默认: 与图片一致)")

    args = parser.parse_args()

    resolution = None
    if args.resolution:
        w, h = args.resolution.lower().split("x")
        resolution = (int(w), int(h))

    print("=" * 50)
    print("图片组 → 短视频 (专业版)")
    print("=" * 50)

    make_video_pro(
        image_dir=args.dir,
        script_path=args.script,
        output_path=args.output,
        voice=args.voice,
        voice_rate=args.voice_rate,
        music_path=args.music,
        music_volume=args.music_volume,
        font_size=args.font_size,
        fps=args.fps,
        resolution=resolution,
    )


if __name__ == "__main__":
    main()
