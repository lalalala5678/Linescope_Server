import json
import logging
from flask import Flask, render_template, url_for, Response, send_from_directory
from typing import List, Dict, Any

from utils.DataRead import read_sensor_data
from core.streaming import mjpeg_generator


def register_main_routes(app: Flask) -> None:
    """注册主要页面路由"""
    
    @app.route("/")
    def index():
        """
        首页（可在 templates/index.html 放置入口按钮/链接）
        """
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        """
        图表页。这里直接把数据塞给模板（也可在前端 fetch /api/sensor-data）。
        """
        try:
            data: List[Dict[str, Any]] = read_sensor_data()
            # 将 data 以 JSON 字符串形式传到模板，便于前端直接使用
            return render_template("dashboard.html", data_json=json.dumps(data, ensure_ascii=False))
        except FileNotFoundError as e:
            logging.getLogger(__name__).error(f"Data file not found: {e}")
            return render_template("dashboard.html", data_json=json.dumps([], ensure_ascii=False))
        except Exception as e:
            logging.getLogger(__name__).exception("read_sensor_data failed: %s", e)
            return render_template("dashboard.html", data_json=json.dumps([], ensure_ascii=False))

    @app.route("/result")
    def result_page():
        """
        结果页。模板中放一个 <img src="{{ url_for('video_stream') }}"> 即可显示视频流。
        """
        stream_url = url_for("video_stream")
        return render_template("result.html", stream_url=stream_url)

    @app.route("/stream.mjpg")
    def video_stream():
        """
        将 GetImage.get_processed_image() 连续输出为 MJPEG（multipart/x-mixed-replace）。
        任何支持 MJPEG 的 <img> 标签或 <video> 标签均可播放。
        """
        try:
            return Response(
                mjpeg_generator(frame_interval=app.config["APP_CFG"].stream_frame_interval_sec),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error in video stream: {e}")
            # 返回一个空的响应或错误页面
            return Response("Video stream error", status=500, mimetype="text/plain")
    
    @app.route('/sw.js')
    def service_worker():
        """
        Service Worker 文件路由
        需要从根路径提供以确保正确的 scope
        """
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    
    @app.route('/manifest.json') 
    def manifest():
        """
        PWA Manifest 文件路由
        """
        return send_from_directory('static', 'manifest.json', mimetype='application/json')