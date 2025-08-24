# 背景图像优化指南

## 当前状态

- 原始图片：`images.jpg` (3.87 MB)
- 需要生成优化版本以提升性能

## 需要生成的图像文件

### 1. WebP 格式优化版本

```bash
# 使用 cwebp 工具转换
cwebp -q 80 images.jpg -o images.webp
cwebp -q 70 -resize 800 600 images.jpg -o images-mobile.webp
cwebp -q 60 -resize 400 300 images.jpg -o images-thumbnail.jpg
```

### 2. AVIF 格式（下一代图像格式）

```bash
# 使用 avif 编码器
avifenc --min 20 --max 60 images.jpg images.avif
```

### 3. 响应式版本

- `images-mobile.jpg` - 移动端版本 (800x600, 质量70%)
- `images-thumbnail.jpg` - 缩略图版本 (400x300, 质量60%)

## 推荐的图像处理流程

### 使用 ImageMagick

```bash
# 生成 WebP 版本
magick images.jpg -quality 80 images.webp

# 生成移动端版本
magick images.jpg -resize 800x600^ -gravity center -extent 800x600 -quality 70 images-mobile.jpg
magick images.jpg -resize 800x600^ -gravity center -extent 800x600 -quality 70 images-mobile.webp

# 生成缩略图
magick images.jpg -resize 400x300^ -gravity center -extent 400x300 -quality 60 images-thumbnail.jpg
```

### 使用在线工具

1. **Squoosh.app** - Google 开发的在线图像压缩工具
2. **TinyPNG** - PNG/JPEG 压缩服务
3. **Convertio** - 格式转换服务

## 预期优化效果

| 文件                   | 原始大小    | 优化后大小   | 节省空间 |
| -------------------- | ------- | ------- | ---- |
| images.jpg           | 3.87 MB | 3.87 MB | 0%   |
| images.webp          | -       | ~2.3 MB | ~40% |
| images.avif          | -       | ~1.8 MB | ~53% |
| images-mobile.jpg    | -       | ~800 KB | ~79% |
| images-mobile.webp   | -       | ~500 KB | ~87% |
| images-thumbnail.jpg | -       | ~150 KB | ~96% |

## CSS 中的现代化实现

已在 `styles.css` 中实现：

- `image-set()` 语法支持多格式
- 响应式图像选择
- 网络连接感知优化
- 懒加载占位符系统
- GPU 加速渲染

## 部署后验证

1. **开发者工具检查**：
   
   - Network 标签查看实际加载的图像格式
   - Performance 标签测量 LCP (最大内容绘制)

2. **性能指标**：
   
   - First Contentful Paint (FCP) < 1.8s
   - Largest Contentful Paint (LCP) < 2.5s
   - Total Blocking Time (TBT) < 200ms

3. **浏览器兼容性测试**：
   
   - Chrome 85+: WebP + AVIF
   - Firefox 93+: WebP + AVIF
   - Safari 16+: WebP + AVIF
   - 老版本浏览器: JPEG 降级

## 自动化脚本

可以使用以下 Python 脚本自动生成优化图像：

```python
# generate_optimized_images.py
from PIL import Image
import os

def optimize_images():
    source = "images.jpg"

    # 生成不同尺寸版本
    with Image.open(source) as img:
        # 移动端版本
        mobile = img.resize((800, 600), Image.Resampling.LANCZOS)
        mobile.save("images-mobile.jpg", "JPEG", quality=70, optimize=True)

        # 缩略图版本
        thumb = img.resize((400, 300), Image.Resampling.LANCZOS)
        thumb.save("images-thumbnail.jpg", "JPEG", quality=60, optimize=True)

        # WebP 版本
        img.save("images.webp", "WEBP", quality=80)
        mobile.save("images-mobile.webp", "WEBP", quality=70)

if __name__ == "__main__":
    optimize_images()
    print("图像优化完成！")
```