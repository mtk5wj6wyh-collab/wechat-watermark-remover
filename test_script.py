#!/usr/bin/env python3
"""
测试脚本功能
"""

import os
import sys
from download_wechat_images import WeChatImageDownloader


def test_url_validation():
    """测试URL验证功能"""
    print("测试URL验证功能...")
    
    downloader = WeChatImageDownloader()
    
    # 测试有效URL
    valid_urls = [
        "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw",
        "http://mp.weixin.qq.com/s/xxxxx",
        "https://mmbiz.qpic.cn/mmbiz_jpg/xxxxx",
    ]
    
    for url in valid_urls:
        if downloader.is_valid_image_url(url):
            print(f"  [OK] 有效: {url[:50]}...")
        else:
            print(f"  [FAIL] 无效: {url[:50]}...")
    
    # 测试无效URL
    invalid_urls = [
        "https://example.com/script.js",
        "https://example.com/style.css",
        "data:image/png;base64,xxxxx",
        "javascript:void(0)",
    ]
    
    for url in invalid_urls:
        if not downloader.is_valid_image_url(url):
            print(f"  [OK] 正确过滤: {url[:50]}...")
        else:
            print(f"  [FAIL] 错误通过: {url[:50]}...")


def test_filename_generation():
    """测试文件名生成功能"""
    print("\n测试文件名生成功能...")
    
    downloader = WeChatImageDownloader()
    
    test_cases = [
        ("https://mmbiz.qpic.cn/mmbiz_jpg/xxxxx/image123.jpg", 1),
        ("https://mmbiz.qpic.cn/mmbiz_png/xxxxx/photo.png", 2),
        ("https://mmbiz.qpic.cn/mmbiz_gif/xxxxx/animation.gif", 3),
        ("https://example.com/image.jpg?param=value", 4),
        ("https://example.com/no-extension", 5),
    ]
    
    for url, index in test_cases:
        filename = downloader.generate_filename(url, index)
        print(f"  {index}: {filename}")


def test_directory_creation():
    """测试目录创建功能"""
    print("\n测试目录创建功能...")
    
    test_dir = "test_output_dir"
    downloader = WeChatImageDownloader(output_dir=test_dir)
    
    # 创建目录
    downloader.create_output_directory()
    
    if os.path.exists(test_dir):
        print(f"  [OK] 目录创建成功: {test_dir}")
        # 清理测试目录
        os.rmdir(test_dir)
        print(f"  [OK] 测试目录已清理")
    else:
        print(f"  [FAIL] 目录创建失败: {test_dir}")


def main():
    """运行所有测试"""
    print("开始测试微信公众号图片下载器...")
    print("=" * 50)
    
    try:
        test_url_validation()
        test_filename_generation()
        test_directory_creation()
        
        print("\n" + "=" * 50)
        print("所有测试完成！")
        return True
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)