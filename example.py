#!/usr/bin/env python3
"""
微信公众号图片下载器使用示例
"""

from download_wechat_images import WeChatImageDownloader


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建下载器实例
    downloader = WeChatImageDownloader()
    
    # 下载指定文章的所有图片
    url = "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw"
    downloader.download_all_images(url)


def example_custom_directory():
    """自定义输出目录示例"""
    print("\n=== 自定义输出目录示例 ===")
    
    # 创建下载器并指定输出目录
    downloader = WeChatImageDownloader(output_dir="my_wechat_images")
    
    # 下载图片
    url = "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw"
    downloader.download_all_images(url)


def example_multiple_articles():
    """下载多个文章示例"""
    print("\n=== 下载多个文章示例 ===")
    
    # 文章链接列表
    articles = [
        "https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw",
        # 可以添加更多文章链接
        # "https://mp.weixin.qq.com/s/xxxxx",
        # "https://mp.weixin.qq.com/s/yyyyy",
    ]
    
    for i, url in enumerate(articles, 1):
        print(f"\n正在处理第 {i} 篇文章...")
        downloader = WeChatImageDownloader(output_dir=f"article_{i}")
        downloader.download_all_images(url)


if __name__ == "__main__":
    print("微信公众号图片下载器使用示例")
    print("=" * 50)
    
    # 运行基本使用示例
    example_basic_usage()
    
    # 如果需要运行其他示例，可以取消注释下面的代码
    # example_custom_directory()
    # example_multiple_articles()
    
    print("\n" + "=" * 50)
    print("示例运行完成！")
    print("查看下载的图片：")
    print("  - 基本示例: downloaded_images/")
    print("  - 自定义目录示例: my_wechat_images/")
    print("  - 多文章示例: article_1/, article_2/, ...")