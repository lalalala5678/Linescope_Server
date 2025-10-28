#!/usr/bin/env python3
"""
Linescope Server - 贵州线镜项目服务器端
重构后的主应用入口文件
"""
import sys
import os

# 将项目根目录加入 sys.path，确保 utils 可被导入
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import create_app

# 创建 Flask 应用实例
app = create_app()

if __name__ == "__main__":
    # 注意：开发时可开启 debug；生产建议由 WSGI/Gunicorn/Uvicorn 托管
    while 1:
        app.run(host="0.0.0.0", port=5000, debug=False)