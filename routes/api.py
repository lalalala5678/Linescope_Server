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
        data = read_sensor_data()
        return jsonify(data)

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
        """健康检查接口"""
        return jsonify({"status": "ok"})