#!/usr/bin/env python3
"""
Simple image assets generator for Linescope Server
Creates placeholder files for optimized background images
"""

import os
import sys
from pathlib import Path

def create_placeholder_files():
    """Create placeholder files for optimized images"""
    images_dir = Path("static/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Files that need to be created
    placeholders = [
        ("images.webp", "WebP version of main background - convert from images.jpg"),
        ("images.avif", "AVIF version of main background - convert from images.jpg"),
        ("images-mobile.jpg", "Mobile background (800x600) - resize from images.jpg"),
        ("images-mobile.webp", "Mobile background WebP version - convert from images.jpg"),
        ("images-thumbnail.jpg", "Thumbnail background (400x300) - resize from images.jpg"),
    ]
    
    print("Creating image optimization placeholders...")
    
    for filename, description in placeholders:
        placeholder_path = images_dir / f"{filename}.placeholder"
        
        if not placeholder_path.exists():
            with open(placeholder_path, "w", encoding="utf-8") as f:
                f.write(f"# Placeholder for {filename}\n")
                f.write(f"# Description: {description}\n")
                f.write(f"# See IMAGE_OPTIMIZATION_GUIDE.md for generation instructions\n")
                f.write(f"# This file can be deleted after creating the actual image\n")
            
            print(f"  Created: {filename}.placeholder")
        else:
            print(f"  Exists: {filename}.placeholder")

def check_current_images():
    """Check what image files currently exist"""
    images_dir = Path("static/images")
    
    print("\nCurrent image files:")
    for file_path in images_dir.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.avif']:
            size_kb = file_path.stat().st_size / 1024
            print(f"  {file_path.name}: {size_kb:.1f} KB")

def main():
    print("Linescope Server Image Assets Setup")
    print("=" * 40)
    
    # Check if in correct directory
    if not Path("static").exists():
        print("Error: Please run from project root directory")
        sys.exit(1)
    
    check_current_images()
    create_placeholder_files()
    
    print("\nNext steps:")
    print("1. Install Pillow: pip install Pillow")
    print("2. Run: python utils/generate_image_assets.py")
    print("3. Or manually optimize images using tools mentioned in IMAGE_OPTIMIZATION_GUIDE.md")

if __name__ == "__main__":
    main()