#!/usr/bin/env python3
"""
微信公众号所有文章下载器使用示例
"""

from download_all_articles import WeChatArticleDownloader


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建下载器实例
    downloader = WeChatArticleDownloader()
    
    # 下载指定公众号的所有文章
    url = "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw"
    downloader.download_all_articles(url, max_articles=50)


def example_custom_directory():
    """自定义输出目录示例"""
    print("\n=== 自定义输出目录示例 ===")
    
    # 创建下载器并指定输出目录
    downloader = WeChatArticleDownloader(output_dir="my_wechat_articles")
    
    # 下载文章
    url = "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw"
    downloader.download_all_articles(url, max_articles=20)


def example_limited_articles():
    """限制文章数量示例"""
    print("\n=== 限制文章数量示例 ===")
    
    # 创建下载器
    downloader = WeChatArticleDownloader()
    
    # 只下载最近10篇文章
    url = "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw"
    downloader.download_all_articles(url, max_articles=10)


if __name__ == "__main__":
    print("微信公众号所有文章下载器使用示例")
    print("=" * 50)
    
    # 运行基本使用示例
    example_basic_usage()
    
    # 如果需要运行其他示例，可以取消注释下面的代码
    # example_custom_directory()
    # example_limited_articles()
    
    print("\n" + "=" * 50)
    print("示例运行完成！")
    print("查看下载的文章：")
    print("  - 基本示例: wechat_articles/")
    print("  - 自定义目录示例: my_wechat_articles/")
    print("\n每个文章文件夹包含：")
    print("  - content.txt: 文字内容")
    print("  - images/: 文章中的图片")
    print("  - cover/: 封面图（如果有）")