import os
import logging
from flask import Flask, jsonify

from config import AppConfig, configure_logging
from routes import register_main_routes, register_api_routes
from core.jobs import PeriodicJob
from utils import DataStore
from utils.i1 import initialize_i1_data_store, start_i1_tcp_server


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

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config["APP_CFG"] = cfg
    app.config["JOBS_STARTED"] = False

    werkzeug_flag = os.environ.get("WERKZEUG_RUN_MAIN")
    should_start_services = (werkzeug_flag == "true") or (werkzeug_flag is None and not app.debug)

    if cfg.data_source_type.lower() == "i1":
        store = initialize_i1_data_store(
            max_records=cfg.i1_max_records,
            line_temp_alert_threshold=cfg.i1_line_temp_alert_threshold,
            line_temp_alert_timeout=cfg.i1_line_temp_alert_timeout,
        )
        if should_start_services and cfg.i1_server_enabled:
            start_i1_tcp_server(cfg.i1_listen_host, cfg.i1_listen_port, store)
            logger.info("I1 TCP server listening on %s:%s", cfg.i1_listen_host, cfg.i1_listen_port)
        elif not should_start_services:
            logger.info("Skip starting I1 TCP server in reloader parent process")
        else:
            logger.info("I1 data source enabled; TCP server disabled by configuration")

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    register_main_routes(app)
    register_api_routes(app)

    if should_start_services and not app.config.get("JOBS_STARTED", False):
        if cfg.data_source_type.lower() != "i1":
            interval = cfg.datastore_interval_minutes * 60
            datastore_job = PeriodicJob(interval_seconds=interval, target=run_datastore_main, name="DataStoreJob")
            datastore_job.start()
            app.config["DATASTORE_JOB"] = datastore_job
            app.config["JOBS_STARTED"] = True
            logger.info("Background job started: DataStore.main() every %s minutes", cfg.datastore_interval_minutes)
        else:
            logger.info("I1 data source active; skip legacy DataStore refresh job")

    return app
