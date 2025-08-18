# app.py
from __future__ import annotations

import os
import sys
import time
import json
import logging
import threading
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Generator, List, Dict, Any, Optional

from flask import Flask, Response, jsonify, render_template, url_for , request

# 将项目根目录加入 sys.path，确保 utils 可被导入（在某些部署结构下有用）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# === 业务模块导入（按照你给的接口文档） ===
from utils.DataRead import read_sensor_data  # -> List[Dict[str, Any]]
from utils.GetImage import get_processed_image  # -> np.ndarray (BGR, uint8)
from utils import DataStore  # 我们只需要用到 DataStore.main()

# OpenCV 用于 JPEG 编码
import cv2
import numpy as np


# =========================
# 配置与封装
# =========================

@dataclass(frozen=True)
class AppConfig:
    """应用运行期配置（可扩展为从环境变量或文件加载）"""
    datastore_interval_minutes: int = 30
    stream_frame_interval_sec: float = 0.2  # 约 5 FPS（按需调整）
    log_file: str = os.path.join(PROJECT_ROOT, "app.log")
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3
    # 注意：开发模式下 Flask 的自动重载会启动两次进程；我们在 create_app 里防止重复启动后台线程。


class PeriodicJob:
    """简单的周期性任务封装（基于线程 + Event），易读、轻量"""
    def __init__(self, interval_seconds: int, target, name: str = "PeriodicJob"):
        self.interval_seconds = int(interval_seconds)
        self._target = target
        self._name = name
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        logger = logging.getLogger(__name__)
        logger.info("[%s] started; interval=%ss", self._name, self.interval_seconds)
        # 先立即执行一次，再进入周期睡眠（如果希望启动后等一个间隔再跑，可以把下面两行对调）
        self._execute_once(logger)
        while not self._stop_evt.wait(self.interval_seconds):
            self._execute_once(logger)
        logger.info("[%s] stopped", self._name)

    def _execute_once(self, logger: logging.Logger) -> None:
        try:
            self._target()
        except Exception as e:
            logger.exception("[%s] execution error: %s", self._name, e)

    def stop(self) -> None:
        self._stop_evt.set()


def configure_logging(cfg: AppConfig) -> None:
    os.makedirs(os.path.dirname(cfg.log_file), exist_ok=True)
    handler = RotatingFileHandler(
        cfg.log_file, maxBytes=cfg.log_max_bytes, backupCount=cfg.log_backup_count, encoding="utf-8"
    )
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # 同时把 INFO 以上日志打到控制台，便于开发
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)


def create_app() -> Flask:
    cfg = AppConfig()
    configure_logging(cfg)
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["APP_CFG"] = cfg
    app.config["JOBS_STARTED"] = False

    # ===========
    # 路由定义
    # ===========

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
        except Exception as e:
            logging.getLogger(__name__).exception("read_sensor_data failed: %s", e)
            data = []
        # 将 data 以 JSON 字符串形式传到模板，便于前端直接使用
        return render_template("dashboard.html", data_json=json.dumps(data, ensure_ascii=False))

    @app.route("/api/sensor-data")
    def api_sensor_data():
        """
        为 dashboard.html 提供 REST 风格接口。
        返回 DataRead.py 的原始结构（list[dict]），字段含义详见接口文档。
        """
        data = read_sensor_data()
        return jsonify(data)

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
        return Response(
            _mjpeg_generator(frame_interval=app.config["APP_CFG"].stream_frame_interval_sec),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    

    @app.route("/api/sensors")
    def api_sensors_compat():
        """
        兼容首页：GET /api/sensors?limit=96
        返回最近 limit 条（默认全量）数据；数据结构与 /api/sensor-data 一致
        """
        data = read_sensor_data()
        try:
            limit = int(request.args.get("limit", "0"))
        except ValueError:
            limit = 0
        if limit > 0:
            data = data[-limit:]
        return jsonify(data)

    @app.route("/api/sensors/latest")
    def api_sensors_latest_compat():
        """
        兼容首页：GET /api/sensors/latest
        返回最新一条记录；没有数据则返回 204
        """
        data = read_sensor_data()
        if not data:
            return ("", 204)
        return jsonify(data[-1])

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    # ===========
    # 后台任务：每 30 分钟执行一次 DataStore.main()
    # ===========

    # 防止 Flask debug reloader 导致的多次启动后台线程
    should_start_jobs = True
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # 这是 reloader 的子进程；只在该分支中启动任务
        should_start_jobs = True
    elif os.environ.get("WERKZEUG_RUN_MAIN") is None:
        # 非 debug（生产）模式：也需要启动
        should_start_jobs = True

    if should_start_jobs and not app.config.get("JOBS_STARTED", False):
        interval = cfg.datastore_interval_minutes * 60
        datastore_job = PeriodicJob(interval_seconds=interval, target=_run_datastore_main, name="DataStoreJob")
        datastore_job.start()
        # 把句柄挂到 app，便于将来优雅关闭（如需的话）
        app.config["DATASTORE_JOB"] = datastore_job
        app.config["JOBS_STARTED"] = True
        logger.info("Background job started: DataStore.main() every %s minutes", cfg.datastore_interval_minutes)

    return app


# =========================
# 具体实现函数
# =========================

def _run_datastore_main() -> None:
    """
    调用 utils/DataStore.py 的 main()。
    该函数会打印/返回需要的信息；我们抓异常并写日志即可。
    """
    logging.getLogger(__name__).info("Running DataStore.main() ...")
    DataStore.main()
    logging.getLogger(__name__).info("DataStore.main() finished.")


def _mjpeg_generator(frame_interval: float = 0) -> Generator[bytes, None, None]:
    """
    MJPEG 生成器：持续获取一帧图片 -> JPEG 编码 -> multipart chunk。
    - frame_interval: 帧间隔（秒），避免 CPU 占用过高
    """
    logger = logging.getLogger(__name__)
    boundary = b"--frame"
    while True:
        try:
            # 1) 获取一帧图像（BGR, uint8, HxWx3）
            frame: np.ndarray = get_processed_image()
            if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
                logger.warning("get_processed_image returned unexpected array shape: %s", getattr(frame, "shape", None))
                time.sleep(frame_interval)
                continue

            # 2) OpenCV JPEG 编码
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                logger.warning("cv2.imencode('.jpg', frame) failed")
                time.sleep(frame_interval)
                continue

            jpg: bytes = buf.tobytes()

            # 3) multipart/x-mixed-replace chunk
            yield (
                boundary
                + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(jpg)}\r\n\r\n".encode("utf-8")
                + jpg
                + b"\r\n"
            )

            # 控制输出频率
            time.sleep(frame_interval)

        except GeneratorExit:
            # 客户端断开，生成器被关闭
            logger.info("Client disconnected from MJPEG stream.")
            break
        except Exception as e:
            logger.exception("Error in MJPEG generator: %s", e)
            time.sleep(max(0.5, frame_interval))


# =========================
# 主入口
# =========================

app = create_app()

if __name__ == "__main__":
    # 注意：开发时可开启 debug；生产建议由 WSGI/Gunicorn/Uvicorn 托管
    app.run(host="0.0.0.0", port=5000, debug=True)
