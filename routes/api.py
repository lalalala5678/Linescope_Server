import logging
from flask import Flask, jsonify, request

from utils.DataRead import read_sensor_data


def register_api_routes(app: Flask) -> None:
    """注册 API 路由"""
    
    @app.route("/api/sensor-data")
    def api_sensor_data():
        """
        为 dashboard.html 提供 REST 风格接口。
        返回 DataRead.py 的原始结构（list[dict]），字段含义详见接口文档。
        """
        try:
            data = read_sensor_data()
            return jsonify(data)
        except FileNotFoundError as e:
            logging.getLogger(__name__).error(f"Data file not found: {e}")
            return jsonify({"error": "Data file not found"}), 404
        except Exception as e:
            logging.getLogger(__name__).error(f"Error reading sensor data: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/sensors")
    def api_sensors_compat():
        """
        兼容首页：GET /api/sensors?limit=96
        返回最近 limit 条（默认全量）数据；数据结构与 /api/sensor-data 一致
        """
        try:
            data = read_sensor_data()
            try:
                limit = int(request.args.get("limit", "0"))
                if limit < 0:
                    limit = 0
            except ValueError:
                limit = 0
            if limit > 0:
                data = data[-limit:]
            return jsonify({"rows": data, "count": len(data)})
        except FileNotFoundError as e:
            logging.getLogger(__name__).error(f"Data file not found: {e}")
            return jsonify({"error": "Data file not found"}), 404
        except Exception as e:
            logging.getLogger(__name__).error(f"Error reading sensor data: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/sensors/latest")
    def api_sensors_latest_compat():
        """
        兼容首页：GET /api/sensors/latest
        返回最新一条记录；没有数据则返回 204
        """
        try:
            data = read_sensor_data()
            if not data:
                return ("", 204)
            return jsonify(data[-1])
        except FileNotFoundError as e:
            logging.getLogger(__name__).error(f"Data file not found: {e}")
            return jsonify({"error": "Data file not found"}), 404
        except Exception as e:
            logging.getLogger(__name__).error(f"Error reading sensor data: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/healthz")
    def healthz():
        """健康检查接口"""
        return jsonify({"status": "ok"})