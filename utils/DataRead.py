# DataRead.py
# 读取同目录下 data/data.txt，并返回解析结果。
# 若直接运行本文件，则打印读取结果到控制台。
# 
# 新架构集成：现在支持Redis缓存和统一服务架构
# 保持向后兼容性，原有API接口不变

from __future__ import annotations
import csv
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# 期望的列名（与生成脚本保持一致）
_EXPECTED_COLUMNS = [
    "timestamp_Beijing",
    "sway_speed_dps",
    "temperature_C",
    "humidity_RH",
    "pressure_hPa",
    "lux",
    "wire_foreign_object",
]

# 简单的内存缓存（向后兼容）
_cache = {
    "data": None,
    "mtime": 0,
    "file_path": None
}

# 新架构服务实例（懒加载）
_sensor_service = None
_use_new_architecture = True  # 可以通过环境变量控制

def _get_sensor_service():
    """获取传感器服务实例（懒加载）"""
    global _sensor_service
    
    if _sensor_service is None:
        try:
            from config.data_factory import create_sensor_service_from_config
            from config.settings import AppConfig
            
            # 从环境变量控制是否使用新架构
            use_new_arch = os.getenv("USE_NEW_ARCHITECTURE", str(_use_new_architecture)).lower() in ("true", "1", "yes")
            
            if use_new_arch:
                config = AppConfig()
                _sensor_service = create_sensor_service_from_config(config)
                logging.getLogger(__name__).info("Initialized new architecture with caching support")
            else:
                _sensor_service = None
                logging.getLogger(__name__).info("Using legacy architecture without caching")
                
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize new architecture, falling back to legacy: {e}")
            _sensor_service = None
    
    return _sensor_service


def read_sensor_data(file_path: Optional[str] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    读取与 DataRead.py 同一文件夹下 data/data.txt（或传入的 file_path）中的内容，
    返回列表[dict]，字段如下：
        - timestamp_Beijing: str  (例: '2025-08-18 23:30')
        - sway_speed_dps:   float
        - temperature_C:    float
        - humidity_RH:      float
        - pressure_hPa:     float
        - lux:              float
        - wire_foreign_object: int (0=无异物, 1=有异物)
    
    Args:
        file_path: 文件路径，默认为 data/data.txt
        use_cache: 是否使用缓存，默认True
        
    新架构优化：
        - 如果启用新架构，将使用Redis缓存和优化的数据访问层
        - 如果新架构不可用，自动降级到原有的内存缓存实现
        - API保持完全兼容，上层调用代码无需修改
    """
    # 尝试使用新架构
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            # 新架构路径：使用服务层获取数据
            # 注意：新架构目前不支持自定义file_path，使用配置的默认路径
            if file_path is None:
                return sensor_service.get_all_data(use_cache=use_cache)
            else:
                # 如果指定了file_path，降级到原实现以保持兼容性
                logging.getLogger(__name__).debug(f"Custom file_path specified ({file_path}), using legacy implementation")
                return _read_sensor_data_legacy(file_path, use_cache)
                
        except Exception as e:
            logging.getLogger(__name__).error(f"New architecture failed, falling back to legacy: {e}")
            # 降级到原实现
            return _read_sensor_data_legacy(file_path, use_cache)
    else:
        # 直接使用原实现
        return _read_sensor_data_legacy(file_path, use_cache)


def _read_sensor_data_legacy(file_path: Optional[str] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
    """原有的数据读取实现（向后兼容）"""
    # 默认路径：<当前文件所在目录>/data/data.txt
    if file_path is None:
        file_path = str(Path(__file__).resolve().parent / "data" / "data.txt")

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(
            f"未找到数据文件：{p}\n"
            "请确认 DataRead.py 同目录下存在 data/data.txt，或传入正确的 file_path。"
        )
    
    # 检查缓存
    if use_cache:
        try:
            current_mtime = os.path.getmtime(file_path)
            if (_cache["file_path"] == file_path and 
                _cache["data"] is not None and 
                _cache["mtime"] == current_mtime):
                return _cache["data"]
        except OSError:
            pass  # 文件不存在或无法访问，继续读取

    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # 简单字段校验
        if reader.fieldnames is None:
            raise ValueError("无法读取表头，请检查文件内容是否为 CSV 并包含表头行。")
        missing = [c for c in _EXPECTED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"表头缺失字段：{missing}，请检查文件格式是否正确。")

        for row in reader:
            # 类型转换：保留时间戳为 str，数值转换为 float，异物检测转换为 int
            try:
                parsed = {
                    "timestamp_Beijing": row["timestamp_Beijing"],
                    "sway_speed_dps": float(row["sway_speed_dps"]),
                    "temperature_C":   float(row["temperature_C"]),
                    "humidity_RH":     float(row["humidity_RH"]),
                    "pressure_hPa":    float(row["pressure_hPa"]),
                    "lux":             float(row["lux"]),
                }
                
                # 兼容性处理：如果存在异物检测字段且值有效则解析，否则默认为0
                if "wire_foreign_object" in row and row["wire_foreign_object"] not in (None, ""):
                    parsed["wire_foreign_object"] = int(float(row["wire_foreign_object"]))
                else:
                    parsed["wire_foreign_object"] = 0
            except (KeyError, ValueError) as e:
                raise ValueError(f"解析行失败：{row}\n错误：{e}")
            rows.append(parsed)
    
    # 更新缓存
    if use_cache:
        try:
            _cache["data"] = rows
            _cache["mtime"] = os.path.getmtime(file_path)
            _cache["file_path"] = file_path
        except OSError:
            pass  # 无法获取文件修改时间，不缓存

    return rows


def clear_cache() -> None:
    """清空缓存，强制重新读取文件"""
    global _cache, _sensor_service
    
    # 清空传统缓存
    _cache = {
        "data": None,
        "mtime": 0,
        "file_path": None
    }
    
    # 清空新架构缓存
    if _sensor_service is not None:
        try:
            _sensor_service.invalidate_cache()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to clear new architecture cache: {e}")


def get_latest_sensor_data() -> Optional[Dict[str, Any]]:
    """
    获取最新的传感器数据（新架构优化）
    
    Returns:
        最新的传感器数据记录，如果没有数据则返回None
    """
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            return sensor_service.get_latest_data()
        except Exception as e:
            logging.getLogger(__name__).error(f"New architecture get_latest failed, falling back to legacy: {e}")
    
    # 降级实现
    data = read_sensor_data()
    return data[-1] if data else None


def get_recent_sensor_data(limit: int) -> List[Dict[str, Any]]:
    """
    获取最近N条传感器数据（新架构优化）
    
    Args:
        limit: 要获取的记录数量
        
    Returns:
        最近N条传感器数据列表
    """
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            return sensor_service.get_recent_data(limit)
        except Exception as e:
            logging.getLogger(__name__).error(f"New architecture get_recent failed, falling back to legacy: {e}")
    
    # 降级实现
    data = read_sensor_data()
    if limit <= 0:
        return data
    return data[-limit:]


def get_sensor_data_count() -> int:
    """
    获取传感器数据总数（新架构优化）
    
    Returns:
        数据记录总数
    """
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            return sensor_service.get_data_count()
        except Exception as e:
            logging.getLogger(__name__).error(f"New architecture get_count failed, falling back to legacy: {e}")
    
    # 降级实现
    data = read_sensor_data()
    return len(data)


def get_data_source_info() -> Dict[str, Any]:
    """
    获取数据源信息和统计
    
    Returns:
        包含数据源信息和缓存统计的字典
    """
    info = {
        "architecture": "legacy",
        "cache_enabled": False,
        "timestamp": time.time()
    }
    
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            service_info = sensor_service.get_service_info()
            info.update({
                "architecture": "new",
                "cache_enabled": service_info.get("cache", {}).get("available", False),
                "data_source": service_info.get("data_source", {}),
                "cache_info": service_info.get("cache", {}),
                "service_health": service_info.get("health", "unknown"),
                "service_info": service_info
            })
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to get service info: {e}")
            info["error"] = str(e)
    
    # 添加传统架构信息
    try:
        data = _read_sensor_data_legacy()
        info["legacy_record_count"] = len(data)
        info["legacy_cache_hit"] = _cache["data"] is not None
    except Exception as e:
        info["legacy_error"] = str(e)
    
    return info


def refresh_cache() -> Dict[str, Any]:
    """
    刷新缓存并返回操作结果
    
    Returns:
        包含刷新操作结果的字典
    """
    result = {
        "timestamp": time.time(),
        "legacy_cache_cleared": False,
        "new_cache_refreshed": False,
        "errors": []
    }
    
    # 清空传统缓存
    try:
        global _cache
        _cache = {
            "data": None,
            "mtime": 0,
            "file_path": None
        }
        result["legacy_cache_cleared"] = True
    except Exception as e:
        result["errors"].append(f"Legacy cache clear failed: {e}")
    
    # 刷新新架构缓存
    sensor_service = _get_sensor_service()
    if sensor_service is not None:
        try:
            sensor_service.refresh_cache()
            result["new_cache_refreshed"] = True
        except Exception as e:
            result["errors"].append(f"New cache refresh failed: {e}")
    
    return result


if __name__ == "__main__":
    # 直接运行则打印读取结果
    data = read_sensor_data()
    # 直接打印列表（672 行会较长，如需只看前几行可自行切片）
    from pprint import pprint
    pprint(data)
