import os
import logging
from flask import Flask

from config import AppConfig, configure_logging
from routes import register_main_routes, register_api_routes
from core.jobs import PeriodicJob
from utils import DataStore


def run_datastore_main() -> None:
    """
    调用 utils/DataStore.py 的 main()。
    该函数会打印/返回需要的信息；我们抓异常并写日志即可。
    """
    logging.getLogger(__name__).info("Running DataStore.main() ...")
    DataStore.main()
    logging.getLogger(__name__).info("DataStore.main() finished.")


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    cfg = AppConfig()
    configure_logging(cfg)
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["APP_CFG"] = cfg
    app.config["JOBS_STARTED"] = False

    # 注册路由
    register_main_routes(app)
    register_api_routes(app)

    # 后台任务：每 30 分钟执行一次 DataStore.main()
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
        datastore_job = PeriodicJob(interval_seconds=interval, target=run_datastore_main, name="DataStoreJob")
        datastore_job.start()
        # 把句柄挂到 app，便于将来优雅关闭（如需的话）
        app.config["DATASTORE_JOB"] = datastore_job
        app.config["JOBS_STARTED"] = True
        logger.info("Background job started: DataStore.main() every %s minutes", cfg.datastore_interval_minutes)

    return app