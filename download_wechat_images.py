#!/usr/bin/env python3
"""
微信公众号文章图片下载器
下载指定微信公众号文章链接中的所有图片
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from pathlib import Path
import hashlib
import sys


class WeChatImageDownloader:
    def __init__(self, output_dir="downloaded_images"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.downloaded_count = 0
        self.failed_count = 0
        
    def create_output_directory(self):
        """创建输出目录"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        print(f"图片将保存到: {os.path.abspath(self.output_dir)}")
    
    def get_page_html(self, url):
        """获取页面HTML内容"""
        try:
            print(f"正在获取页面: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"获取页面失败: {e}")
            return None
    
    def extract_image_urls(self, html, base_url):
        """从HTML中提取所有图片URL"""
        soup = BeautifulSoup(html, 'lxml')
        image_urls = set()
        
        # 1. 查找所有img标签的src属性
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(base_url, src)
                if self.is_valid_image_url(absolute_url):
                    image_urls.add(absolute_url)
        
        # 2. 查找data-src属性（微信懒加载图片）
        for img in soup.find_all('img'):
            data_src = img.get('data-src')
            if data_src:
                absolute_url = urljoin(base_url, data_src)
                if self.is_valid_image_url(absolute_url):
                    image_urls.add(absolute_url)
        
        # 3. 查找style属性中的背景图片
        for element in soup.find_all(style=True):
            style = element['style']
            urls = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for url in urls:
                absolute_url = urljoin(base_url, url)
                if self.is_valid_image_url(absolute_url):
                    image_urls.add(absolute_url)
        
        # 4. 查找其他可能的图片标签
        for source in soup.find_all('source'):
            srcset = source.get('srcset')
            if srcset:
                urls = re.findall(r'([^\s,]+)', srcset)
                for url in urls:
                    absolute_url = urljoin(base_url, url)
                    if self.is_valid_image_url(absolute_url):
                        image_urls.add(absolute_url)
        
        # 5. 查找微信特有的图片格式
        # 微信公众号文章中的图片通常在mmbiz.qpic.cn域名下
        wechat_pattern = re.compile(r'https?://mmbiz\.qpic\.cn/[^"\'>\s]+')
        found_urls = wechat_pattern.findall(html)
        for url in found_urls:
            # 清理URL，移除可能的参数
            clean_url = url.split('?')[0] if '?' in url else url
            if self.is_valid_image_url(clean_url):
                image_urls.add(clean_url)
        
        return list(image_urls)
    
    def is_valid_image_url(self, url):
        """检查URL是否是有效的图片URL"""
        if not url:
            return False
        
        # 过滤掉明显的非图片URL
        invalid_patterns = [
            r'\.js$',
            r'\.css$',
            r'\.html$',
            r'\.php$',
            r'data:image',  # base64图片
            r'javascript:',
            r'about:',
            r'chrome:',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 检查是否是图片扩展名
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
        url_lower = url.lower()
        
        # 如果URL包含图片扩展名，很可能是图片
        for ext in image_extensions:
            if ext in url_lower:
                return True
        
        # 微信CDN域名通常包含图片
        wechat_domains = ['mmbiz.qpic.cn', 'mmbiz.qlogo.cn']
        for domain in wechat_domains:
            if domain in url_lower:
                return True
        
        # 其他CDN域名
        cdn_patterns = [
            r'img\.',
            r'image\.',
            r'pic\.',
            r'photo\.',
            r'cdn\.',
        ]
        
        for pattern in cdn_patterns:
            if re.search(pattern, url_lower):
                return True
        
        # 如果没有明确的非图片特征，尝试下载
        return True
    
    def generate_filename(self, url, index):
        """生成文件名"""
        # 尝试从URL中提取原始文件名
        parsed = urlparse(url)
        path = parsed.path
        
        if path:
            # 获取路径中的文件名
            filename = os.path.basename(path)
            if filename and '.' in filename:
                # 清理文件名
                filename = re.sub(r'[^\w\-_\.]', '_', filename)
                return f"{index:03d}_{filename}"
        
        # 如果无法提取，使用哈希值
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # 尝试确定扩展名
        ext = '.jpg'  # 默认扩展名
        if '.png' in url.lower():
            ext = '.png'
        elif '.gif' in url.lower():
            ext = '.gif'
        elif '.webp' in url.lower():
            ext = '.webp'
        elif '.svg' in url.lower():
            ext = '.svg'
        
        return f"{index:03d}_{url_hash}{ext}"
    
    def download_image(self, url, filename):
        """下载单个图片"""
        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type and not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                print(f"  跳过非图片: {content_type}")
                return False
            
            # 保存图片
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 获取文件大小
            file_size = os.path.getsize(filepath)
            size_str = self.format_size(file_size)
            
            print(f"  [OK] 下载成功: {filename} ({size_str})")
            self.downloaded_count += 1
            return True
            
        except Exception as e:
            print(f"  [FAIL] 下载失败: {filename} - {e}")
            self.failed_count += 1
            return False
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def download_all_images(self, url):
        """下载文章中的所有图片"""
        self.create_output_directory()
        
        # 获取页面HTML
        html = self.get_page_html(url)
        if not html:
            return False
        
        # 提取图片URL
        print("正在分析页面，提取图片链接...")
        image_urls = self.extract_image_urls(html, url)
        
        if not image_urls:
            print("未找到任何图片链接")
            return False
        
        print(f"找到 {len(image_urls)} 个图片链接")
        print("-" * 50)
        
        # 下载每个图片
        for i, img_url in enumerate(image_urls, 1):
            print(f"[{i}/{len(image_urls)}] 正在下载: {img_url[:80]}...")
            filename = self.generate_filename(img_url, i)
            self.download_image(img_url, filename)
            
            # 添加延迟，避免请求过快
            if i < len(image_urls):
                time.sleep(0.5)
        
        # 显示统计信息
        print("-" * 50)
        print(f"下载完成！")
        print(f"成功: {self.downloaded_count} 张")
        print(f"失败: {self.failed_count} 张")
        print(f"保存位置: {os.path.abspath(self.output_dir)}")
        
        return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python download_wechat_images.py <微信公众号文章链接>")
        print("示例: python download_wechat_images.py https://mp.weixin.qq.com/s/xxxxx")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # 验证URL
    if not url.startswith(('http://', 'https://')):
        print("错误: 请提供有效的URL链接")
        sys.exit(1)
    
    # 创建下载器并开始下载
    downloader = WeChatImageDownloader()
    success = downloader.download_all_images(url)
    
    if success:
        print("\n所有任务完成！")
    else:
        print("\n任务失败，请检查链接是否正确")
        sys.exit(1)


if __name__ == "__main__":
    main()