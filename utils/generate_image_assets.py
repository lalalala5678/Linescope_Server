#!/usr/bin/env python3
"""
图像资源生成脚本
为 Linescope Server 生成优化的背景图像资源

使用方法:
python utils/generate_image_assets.py
"""

import os
import sys
from pathlib import Path

def create_placeholder_images():
    """创建占位符图像文件（如果 PIL 不可用）"""
    images_dir = Path("static/images")
    
    # 创建简单的占位符文件，表示需要手动生成
    placeholders = [
        ("images.webp", "WebP 版本的主背景图 - 需要从 images.jpg 转换"),
        ("images.avif", "AVIF 版本的主背景图 - 需要从 images.jpg 转换"),
        ("images-mobile.jpg", "移动端背景图 (800x600) - 需要从 images.jpg 缩放"),
        ("images-mobile.webp", "移动端背景图 WebP 版本 - 需要从 images.jpg 转换"),
        ("images-thumbnail.jpg", "缩略图背景 (400x300) - 需要从 images.jpg 缩放"),
    ]
    
    print("Creating image placeholder files...")
    
    for filename, description in placeholders:
        placeholder_path = images_dir / filename
        
        if not placeholder_path.exists():
            # 创建占位符文本文件，说明需要生成的图像
            with open(f"{placeholder_path}.placeholder", "w", encoding="utf-8") as f:
                f.write(f"# Placeholder file\n")
                f.write(f"# Need to generate: {filename}\n")
                f.write(f"# Description: {description}\n")
                f.write(f"# Please refer to IMAGE_OPTIMIZATION_GUIDE.md to generate this image\n")
            
            print(f"  Created placeholder: {filename}.placeholder")
        else:
            print(f"  Already exists: {filename}")

def try_optimize_with_pil():
    """尝试使用 PIL 进行图像优化"""
    try:
        from PIL import Image, ImageFilter
        print("✅ 检测到 PIL/Pillow，开始生成优化图像...")
        
        images_dir = Path("static/images")
        source_path = images_dir / "images.jpg"
        
        if not source_path.exists():
            print("❌ 源图像文件不存在: static/images/images.jpg")
            return False
        
        with Image.open(source_path) as img:
            # 确保图像是 RGB 模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            print(f"📸 源图像信息: {img.size[0]}x{img.size[1]} 像素，模式: {img.mode}")
            
            # 生成移动端版本 (800x600)
            mobile_img = img.resize((800, 600), Image.Resampling.LANCZOS)
            mobile_path = images_dir / "images-mobile.jpg"
            mobile_img.save(mobile_path, "JPEG", quality=70, optimize=True)
            print(f"  ✅ 生成: {mobile_path}")
            
            # 生成缩略图版本 (400x300)
            thumb_img = img.resize((400, 300), Image.Resampling.LANCZOS)
            thumb_path = images_dir / "images-thumbnail.jpg"
            thumb_img.save(thumb_path, "JPEG", quality=60, optimize=True)
            print(f"  ✅ 生成: {thumb_path}")
            
            # 尝试生成 WebP 版本
            try:
                webp_path = images_dir / "images.webp"
                img.save(webp_path, "WEBP", quality=80, optimize=True)
                print(f"  ✅ 生成: {webp_path}")
                
                mobile_webp_path = images_dir / "images-mobile.webp"
                mobile_img.save(mobile_webp_path, "WEBP", quality=70, optimize=True)
                print(f"  ✅ 生成: {mobile_webp_path}")
                
            except Exception as e:
                print(f"  ⚠️  WebP 生成失败: {e}")
            
            return True
            
    except ImportError:
        print("⚠️  未检测到 PIL/Pillow 库")
        return False
    except Exception as e:
        print(f"❌ 图像处理失败: {e}")
        return False

def check_file_sizes():
    """检查生成文件的大小"""
    images_dir = Path("static/images")
    files_to_check = [
        "images.jpg",
        "images.webp", 
        "images-mobile.jpg",
        "images-mobile.webp",
        "images-thumbnail.jpg"
    ]
    
    print("\n📊 文件大小报告:")
    total_saved = 0
    original_size = 0
    
    for filename in files_to_check:
        file_path = images_dir / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            if filename == "images.jpg":
                original_size = size_bytes
            
            if size_mb >= 1:
                print(f"  📁 {filename}: {size_mb:.2f} MB")
            else:
                print(f"  📁 {filename}: {size_kb:.1f} KB")
                
            if filename != "images.jpg" and original_size > 0:
                saved = ((original_size - size_bytes) / original_size) * 100
                total_saved += saved
                print(f"     💾 节省空间: {saved:.1f}%")
        else:
            print(f"  ❌ {filename}: 未找到")

def main():
    """主函数"""
    print("Linescope Server Image Assets Generator")
    print("=" * 50)
    
    # 确保图像目录存在
    images_dir = Path("static/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 尝试使用 PIL 优化
    if not try_optimize_with_pil():
        print("\n📝 由于缺少 PIL 库，将创建占位符文件")
        print("   请安装 Pillow: pip install Pillow")
        print("   或者使用在线工具手动优化图像")
        create_placeholder_images()
    
    print("\n" + "=" * 50)
    check_file_sizes()
    
    print("\n✅ 图像资源处理完成!")
    print("💡 提示：查看 static/images/IMAGE_OPTIMIZATION_GUIDE.md 了解更多信息")

if __name__ == "__main__":
    # 确保在项目根目录运行
    if not Path("static").exists():
        print("❌ 错误：请在项目根目录运行此脚本")
        print("   正确路径应包含 static/ 目录")
        sys.exit(1)
    
    main()