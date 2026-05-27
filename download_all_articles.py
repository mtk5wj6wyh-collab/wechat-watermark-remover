#!/usr/bin/env python3
"""
微信公众号所有文章下载器
下载指定公众号的所有文章（文字+图片），按文章名创建文件夹保存
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import time
from pathlib import Path
import hashlib
import sys
import html


class WeChatArticleDownloader:
    def __init__(self, output_dir="wechat_articles"):
        self.output_dir = output_dir
        self.session = requests.Session()
        # 模拟微信内置浏览器的User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.downloaded_articles = 0
        self.failed_articles = 0
        self.downloaded_images = 0
        self.failed_images = 0
        
    def create_output_directory(self):
        """创建输出目录"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        print(f"文章将保存到: {os.path.abspath(self.output_dir)}")
    
    def extract_biz_from_url(self, url):
        """从文章URL中提取公众号的biz参数"""
        try:
            # 方法1: 从URL参数中提取
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if '__biz' in params:
                return params['__biz'][0]
            
            # 方法2: 从页面HTML中提取
            print("正在从页面中提取公众号信息...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text
            
            # 查找biz参数
            biz_patterns = [
                r'var\s+biz\s*=\s*["\']([^"\']+)["\']',
                r'__biz=([^&"\']+)',
                r'biz\s*:\s*["\']([^"\']+)["\']',
            ]
            
            for pattern in biz_patterns:
                match = re.search(pattern, html_content)
                if match:
                    biz = match.group(1)
                    print(f"找到公众号biz: {biz}")
                    return biz
            
            print("无法提取公众号biz参数")
            return None
            
        except Exception as e:
            print(f"提取biz参数失败: {e}")
            return None
    
    def get_article_list_by_api(self, biz, max_articles=100):
        """通过微信API获取文章列表"""
        articles = []
        offset = 0
        count = 10
        
        print(f"正在获取公众号文章列表（最多{max_articles}篇）...")
        
        while len(articles) < max_articles:
            try:
                # 微信公众号文章列表API
                api_url = f"https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={biz}&f=json&offset={offset}&count={count}"
                
                response = self.session.get(api_url, timeout=30)
                response.raise_for_status()
                
                # 尝试解析JSON响应
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    print("API返回非JSON格式，尝试其他方法...")
                    break
                
                if 'general_msg_list' not in data:
                    print("API响应中没有文章列表")
                    break
                
                msg_list = json.loads(data['general_msg_list'])
                
                if not msg_list:
                    break
                
                for msg in msg_list:
                    if 'app_msg_ext_info' in msg:
                        app_msg = msg['app_msg_ext_info']
                        title = app_msg.get('title', '')
                        content_url = app_msg.get('content_url', '')
                        
                        if title and content_url:
                            # 修复URL中的特殊字符
                            content_url = content_url.replace('&amp;', '&')
                            articles.append({
                                'title': title,
                                'url': content_url
                            })
                            print(f"  找到文章: {title}")
                    
                    # 检查多图文消息
                    if 'multi_app_msg_item_list' in app_msg:
                        for item in app_msg['multi_app_msg_item_list']:
                            title = item.get('title', '')
                            content_url = item.get('content_url', '')
                            
                            if title and content_url:
                                content_url = content_url.replace('&amp;', '&')
                                articles.append({
                                    'title': title,
                                    'url': content_url
                                })
                                print(f"  找到文章: {title}")
                
                offset += count
                print(f"  已获取 {len(articles)} 篇文章")
                
                # 检查是否还有更多文章
                if len(msg_list) < count:
                    break
                
                # 添加延迟，避免请求过快
                time.sleep(1)
                
            except Exception as e:
                print(f"获取文章列表失败: {e}")
                break
        
        return articles[:max_articles]
    
    def get_article_list_from_page(self, url, max_articles=100):
        """从公众号历史消息页面获取文章列表"""
        articles = []
        
        print("正在从页面获取文章列表...")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text
            
            # 解析页面中的文章链接
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 查找文章链接
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                if 'mp.weixin.qq.com' in href and title:
                    # 修复URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = 'https://mp.weixin.qq.com' + href
                    
                    articles.append({
                        'title': title,
                        'url': href
                    })
                    print(f"  找到文章: {title}")
            
            print(f"从页面获取到 {len(articles)} 篇文章")
            
        except Exception as e:
            print(f"从页面获取文章列表失败: {e}")
        
        return articles[:max_articles]
    
    def get_related_articles_from_article(self, url, max_articles=100):
        """从当前文章页面提取相关文章链接"""
        articles = []
        
        print("正在从当前文章页面提取相关文章...")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 提取当前文章标题
            current_title = ""
            title_tag = soup.find('h1', class_='rich_media_title') or soup.find('h1')
            if title_tag:
                current_title = title_tag.get_text(strip=True)
            
            # 方法1: 查找"相关推荐"或"推荐阅读"部分
            related_sections = soup.find_all(['div', 'section'], string=re.compile(r'相关推荐|推荐阅读|更多文章|历史文章'))
            for section in related_sections:
                for link in section.find_all('a', href=True):
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    if 'mp.weixin.qq.com' in href and title and title != current_title:
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = 'https://mp.weixin.qq.com' + href
                        
                        articles.append({
                            'title': title,
                            'url': href
                        })
                        print(f"  找到相关文章: {title}")
            
            # 方法2: 查找页面中所有微信文章链接
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                # 检查是否是微信文章链接
                if ('mp.weixin.qq.com/s' in href or 'mp.weixin.qq.com/mp/appmsg' in href) and title:
                    # 排除当前文章
                    if title == current_title:
                        continue
                    
                    # 修复URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = 'https://mp.weixin.qq.com' + href
                    
                    # 检查是否已经添加过
                    if not any(a['url'] == href for a in articles):
                        articles.append({
                            'title': title,
                            'url': href
                        })
                        print(f"  找到文章: {title}")
            
            # 方法3: 从JavaScript中提取文章链接
            js_pattern = re.compile(r'url\s*:\s*["\']([^"\']*mp\.weixin\.qq\.com[^"\']+)["\']')
            for match in js_pattern.finditer(html_content):
                href = match.group(1)
                if href.startswith('//'):
                    href = 'https:' + href
                
                # 尝试从URL中提取标题
                title_match = re.search(r'title=([^&]+)', href)
                if title_match:
                    title = title_match.group(1)
                    # URL解码
                    import urllib.parse
                    title = urllib.parse.unquote(title)
                    
                    if title != current_title and not any(a['url'] == href for a in articles):
                        articles.append({
                            'title': title,
                            'url': href
                        })
                        print(f"  找到文章: {title}")
            
            print(f"从当前文章页面提取到 {len(articles)} 篇相关文章")
            
        except Exception as e:
            print(f"从当前文章页面提取相关文章失败: {e}")
        
        return articles[:max_articles]
    
    def get_article_list(self, url, max_articles=100):
        """获取文章列表"""
        articles = []
        
        # 先尝试提取biz参数
        biz = self.extract_biz_from_url(url)
        
        if biz:
            # 尝试通过API获取文章列表
            articles = self.get_article_list_by_api(biz, max_articles)
            if articles:
                return articles
        
        # 如果API失败，尝试从当前文章页面提取相关文章
        articles = self.get_related_articles_from_article(url, max_articles)
        if articles:
            return articles
        
        # 如果还是失败，尝试从页面获取
        articles = self.get_article_list_from_page(url, max_articles)
        
        # 如果都没有找到，至少返回当前文章
        if not articles:
            print("未找到其他文章，将只下载当前文章")
            # 获取当前文章标题
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'lxml')
                title_tag = soup.find('h1', class_='rich_media_title') or soup.find('h1')
                title = title_tag.get_text(strip=True) if title_tag else "当前文章"
                articles.append({
                    'title': title,
                    'url': url
                })
            except:
                articles.append({
                    'title': "当前文章",
                    'url': url
                })
        
        return articles
    
    def sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        filename = re.sub(illegal_chars, '_', filename)
        
        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:200]
        
        # 移除首尾空格
        filename = filename.strip()
        
        # 如果文件名为空，使用默认名称
        if not filename:
            filename = "untitled"
        
        return filename
    
    def extract_article_content(self, html_content, base_url):
        """提取文章内容（文字和图片）"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取标题
        title = ""
        title_tag = soup.find('h1', class_='rich_media_title') or soup.find('h1')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # 提取作者
        author = ""
        author_tag = soup.find('span', class_='rich_media_meta_nickname') or soup.find('a', id='js_name')
        if author_tag:
            author = author_tag.get_text(strip=True)
        
        # 提取发布时间
        publish_time = ""
        time_tag = soup.find('em', id='publish_time') or soup.find('span', class_='rich_media_meta_text')
        if time_tag:
            publish_time = time_tag.get_text(strip=True)
        
        # 提取正文内容
        content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
        
        text_content = ""
        image_urls = []
        
        if content_div:
            # 提取文字内容
            for p in content_div.find_all(['p', 'span', 'section']):
                text = p.get_text(strip=True)
                if text:
                    text_content += text + "\n"
            
            # 提取图片URL
            for img in content_div.find_all('img'):
                src = img.get('data-src') or img.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if self.is_valid_image_url(absolute_url):
                        image_urls.append(absolute_url)
        
        # 提取封面图
        cover_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image:
            cover_url = og_image.get('content', '')
        
        return {
            'title': title,
            'author': author,
            'publish_time': publish_time,
            'text_content': text_content.strip(),
            'image_urls': list(set(image_urls)),
            'cover_url': cover_url
        }
    
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
            r'data:image',
            r'javascript:',
            r'about:',
            r'chrome:',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 微信CDN域名通常包含图片
        wechat_domains = ['mmbiz.qpic.cn', 'mmbiz.qlogo.cn']
        for domain in wechat_domains:
            if domain in url.lower():
                return True
        
        # 检查是否是图片扩展名
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
        for ext in image_extensions:
            if ext in url.lower():
                return True
        
        return True
    
    def download_image(self, url, filepath):
        """下载单个图片"""
        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type and not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                return False
            
            # 保存图片
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.downloaded_images += 1
            return True
            
        except Exception as e:
            print(f"    [FAIL] 下载图片失败: {e}")
            self.failed_images += 1
            return False
    
    def generate_image_filename(self, url, index):
        """生成图片文件名"""
        # 尝试从URL中提取原始文件名
        parsed = urlparse(url)
        path = parsed.path
        
        if path:
            filename = os.path.basename(path)
            if filename and '.' in filename:
                filename = re.sub(r'[^\w\-_\.]', '_', filename)
                return f"{index:03d}_{filename}"
        
        # 如果无法提取，使用哈希值
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # 尝试确定扩展名
        ext = '.jpg'
        if '.png' in url.lower():
            ext = '.png'
        elif '.gif' in url.lower():
            ext = '.gif'
        elif '.webp' in url.lower():
            ext = '.webp'
        
        return f"{index:03d}_{url_hash}{ext}"
    
    def download_article(self, article_info, index):
        """下载单篇文章"""
        title = article_info['title']
        url = article_info['url']
        
        print(f"\n[{index}] 正在下载文章: {title}")
        print(f"    URL: {url[:80]}...")
        
        try:
            # 获取文章页面
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text
            
            # 提取文章内容
            content = self.extract_article_content(html_content, url)
            
            # 创建文章目录（使用文章标题）
            safe_title = self.sanitize_filename(title)
            article_dir = os.path.join(self.output_dir, safe_title)
            Path(article_dir).mkdir(parents=True, exist_ok=True)
            
            # 保存文字内容
            text_file = os.path.join(article_dir, "content.txt")
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(f"标题: {content['title']}\n")
                f.write(f"作者: {content['author']}\n")
                f.write(f"发布时间: {content['publish_time']}\n")
                f.write(f"原文链接: {url}\n")
                f.write("=" * 50 + "\n\n")
                f.write(content['text_content'])
            
            print(f"    [OK] 文字内容已保存")
            
            # 下载图片
            if content['image_urls']:
                print(f"    正在下载 {len(content['image_urls'])} 张图片...")
                images_dir = os.path.join(article_dir, "images")
                Path(images_dir).mkdir(parents=True, exist_ok=True)
                
                for i, img_url in enumerate(content['image_urls'], 1):
                    filename = self.generate_image_filename(img_url, i)
                    filepath = os.path.join(images_dir, filename)
                    
                    if self.download_image(img_url, filepath):
                        print(f"    [OK] 图片 {i}/{len(content['image_urls'])}: {filename}")
                    
                    # 添加延迟
                    if i < len(content['image_urls']):
                        time.sleep(0.3)
            
            # 下载封面图
            if content['cover_url']:
                cover_dir = os.path.join(article_dir, "cover")
                Path(cover_dir).mkdir(parents=True, exist_ok=True)
                cover_file = os.path.join(cover_dir, "cover.jpg")
                
                if self.download_image(content['cover_url'], cover_file):
                    print(f"    [OK] 封面图已保存")
            
            self.downloaded_articles += 1
            print(f"    [OK] 文章下载完成: {safe_title}")
            return True
            
        except Exception as e:
            print(f"    [FAIL] 下载文章失败: {e}")
            self.failed_articles += 1
            return False
    
    def download_all_articles(self, url, max_articles=100):
        """下载公众号所有文章"""
        self.create_output_directory()
        
        # 获取文章列表
        articles = self.get_article_list(url, max_articles)
        
        if not articles:
            print("未找到任何文章")
            return False
        
        print(f"\n共找到 {len(articles)} 篇文章")
        print("=" * 50)
        
        # 下载每篇文章
        for i, article in enumerate(articles, 1):
            self.download_article(article, i)
            
            # 添加延迟，避免请求过快
            if i < len(articles):
                time.sleep(1)
        
        # 显示统计信息
        print("\n" + "=" * 50)
        print("下载完成！")
        print(f"文章: 成功 {self.downloaded_articles} 篇，失败 {self.failed_articles} 篇")
        print(f"图片: 成功 {self.downloaded_images} 张，失败 {self.failed_images} 张")
        print(f"保存位置: {os.path.abspath(self.output_dir)}")
        
        return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("微信公众号所有文章下载器")
        print("=" * 50)
        print("使用方法: python download_all_articles.py <微信公众号文章链接> [最大文章数]")
        print("\n示例:")
        print("  python download_all_articles.py https://mp.weixin.qq.com/s/xxxxx")
        print("  python download_all_articles.py https://mp.weixin.qq.com/s/xxxxx 50")
        print("\n说明:")
        print("  - 提供任意一篇该公众号的文章链接")
        print("  - 脚本会自动获取该公众号的所有文章")
        print("  - 每篇文章会创建独立文件夹，包含文字和图片")
        sys.exit(1)
    
    url = sys.argv[1]
    max_articles = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    # 验证URL
    if not url.startswith(('http://', 'https://')):
        print("错误: 请提供有效的URL链接")
        sys.exit(1)
    
    # 创建下载器并开始下载
    downloader = WeChatArticleDownloader()
    success = downloader.download_all_articles(url, max_articles)
    
    if success:
        print("\n所有任务完成！")
    else:
        print("\n任务失败，请检查链接是否正确")
        sys.exit(1)


if __name__ == "__main__":
    main()