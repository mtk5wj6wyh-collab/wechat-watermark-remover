# 微信公众号文章下载器

一个用于下载微信公众号文章（文字+图片）的Python脚本集合。

## 功能特点

### 单篇文章下载（download_wechat_images.py）
- 自动提取微信公众号文章中的所有图片
- 支持多种图片格式（JPG、PNG、GIF、WebP等）
- 自动处理微信特有的图片加载方式（data-src懒加载）
- 智能识别微信CDN域名（mmbiz.qpic.cn）
- 批量下载并自动命名
- 显示下载进度和统计信息

### 公众号所有文章下载（download_all_articles.py）
- 自动获取公众号的所有文章列表
- 按文章名创建独立文件夹
- 保存文章文字内容（content.txt）
- 下载文章中的所有图片
- 下载文章封面图
- 支持限制下载文章数量

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 单篇文章下载

```bash
python download_wechat_images.py <微信公众号文章链接>
```

### 公众号所有文章下载

```bash
python download_all_articles.py <微信公众号文章链接> [最大文章数]
```

### 示例

```bash
# 下载单篇文章的所有图片
python download_wechat_images.py https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw

# 下载公众号所有文章（默认最多100篇）
python download_all_articles.py https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw

# 下载公众号最近20篇文章
python download_all_articles.py https://mp.weixin.qq.com/s/Jv7IU_ps6H1qzN7Es82UFw 20
```

### 高级用法

#### 单篇文章下载 - 指定输出目录

```python
from download_wechat_images import WeChatImageDownloader

downloader = WeChatImageDownloader(output_dir="my_images")
downloader.download_all_images("https://mp.weixin.qq.com/s/xxxxx")
```

#### 公众号所有文章下载 - 指定输出目录和文章数量

```python
from download_all_articles import WeChatArticleDownloader

downloader = WeChatArticleDownloader(output_dir="my_articles")
downloader.download_all_articles("https://mp.weixin.qq.com/s/xxxxx", max_articles=50)
```

## 输出

### 单篇文章下载
- 图片默认保存在 `downloaded_images` 目录中
- 文件名格式：`序号_原始文件名` 或 `序号_哈希值.扩展名`
- 控制台显示下载进度和统计信息

### 公众号所有文章下载
- 文章默认保存在 `wechat_articles` 目录中
- 每篇文章创建独立文件夹（以文章标题命名）
- 每个文章文件夹包含：
  - `content.txt`: 文字内容（标题、作者、发布时间、正文）
  - `images/`: 文章中的所有图片
  - `cover/`: 文章封面图（如果有）

## 注意事项

1. **网络连接**：需要稳定的网络连接来访问微信服务器
2. **反爬虫机制**：微信可能有反爬虫机制，脚本已设置适当的User-Agent和延迟
3. **图片质量**：下载的是文章中显示的图片，可能是压缩版本
4. **版权问题**：请尊重图片版权，仅用于个人学习研究
5. **链接有效性**：确保提供的链接是有效的微信公众号文章链接
6. **文章列表获取**：由于微信API限制，公众号所有文章下载功能可能无法获取完整文章列表，建议手动提供多个文章链接
7. **编码问题**：在Windows系统上可能会遇到编码问题，脚本已使用ASCII字符替代Unicode符号

## 故障排除

### 问题：无法获取页面内容
- 检查网络连接
- 确认链接是否正确
- 尝试使用VPN或代理

### 问题：找不到图片
- 微信公众号文章可能使用JavaScript动态加载图片
- 尝试使用浏览器开发者工具手动提取图片URL

### 问题：下载失败
- 检查是否有足够的磁盘空间
- 确认目标目录有写入权限
- 查看错误信息并尝试重新下载

### 问题：无法获取公众号所有文章
- 微信API有访问限制，可能无法获取完整文章列表
- 尝试手动提供多个文章链接
- 使用单篇文章下载功能逐个下载

### 问题：编码错误
- 在Windows系统上可能会遇到GBK编码错误
- 脚本已使用ASCII字符替代Unicode符号
- 如果仍有问题，尝试在Linux/macOS上运行

## 技术细节

### 支持的图片源

1. `<img>` 标签的 `src` 属性
2. `<img>` 标签的 `data-src` 属性（微信懒加载）
3. CSS样式中的背景图片（`url()`）
4. `<source>` 标签的 `srcset` 属性
5. 微信CDN域名（mmbiz.qpic.cn）的图片

### 文件命名规则

- 优先使用URL中的原始文件名
- 如果无法提取，使用URL的MD5哈希值
- 添加序号前缀确保顺序

## 项目结构

```
wechat_downloader/
├── download_wechat_images.py    # 单篇文章图片下载器
├── download_all_articles.py     # 公众号所有文章下载器
├── example.py                   # 单篇文章下载示例
├── example_all_articles.py      # 公众号所有文章下载示例
├── test_script.py               # 测试脚本
├── requirements.txt             # Python依赖包
├── README.md                    # 使用说明文档
├── downloaded_images/           # 单篇文章下载的图片
└── wechat_articles/             # 公众号所有文章下载
    └── 文章标题/                # 每篇文章独立文件夹
        ├── content.txt          # 文字内容
        ├── images/              # 文章中的图片
        └── cover/               # 封面图
```

## 许可证

MIT License - 仅供学习研究使用

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。