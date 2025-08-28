# utils/sensor_service.py
"""
传感器数据服务层
统一的业务逻辑层，整合数据源和缓存管理
为上层API提供高性能的数据访问接口
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .data_access import DataSource
from .cache_manager import CacheManager


class SensorService:
    """传感器数据服务类"""
    
    # 缓存键常量
    CACHE_KEY_ALL_DATA = "data:all"
    CACHE_KEY_LATEST = "data:latest"
    CACHE_KEY_COUNT = "meta:count"
    CACHE_KEY_RECENT_PREFIX = "data:recent"
    CACHE_KEY_LAST_UPDATE = "meta:last_update"
    
    def __init__(
        self, 
        data_source: DataSource, 
        cache_manager: Optional[CacheManager] = None,
        default_cache_ttl: int = 1800  # 30分钟
    ):
        """
        初始化传感器数据服务
        
        Args:
            data_source: 数据源实例
            cache_manager: 缓存管理器实例
            default_cache_ttl: 默认缓存TTL（秒）
        """
        self.data_source = data_source
        self.cache_manager = cache_manager
        self.default_cache_ttl = default_cache_ttl
        self.logger = logging.getLogger(__name__)
        
        # 记录服务初始化信息
        data_info = self.data_source.get_data_info()
        cache_info = self.cache_manager.get_cache_info() if self.cache_manager else {"available": False}
        
        self.logger.info(
            f"SensorService initialized - "
            f"DataSource: {data_info['source_type']}, "
            f"Cache: {'enabled' if cache_info['available'] else 'disabled'}, "
            f"Records: {data_info.get('record_count', 'unknown')}"
        )
    
    def get_all_data(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有传感器数据
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            所有传感器数据列表
        """
        if use_cache and self.cache_manager:
            # 使用缓存的get_or_set方法
            def data_loader():
                self.logger.debug("Loading all data from data source")
                return self.data_source.read_all_data()
            
            data = self.cache_manager.get_or_set(
                self.CACHE_KEY_ALL_DATA,
                data_loader,
                ttl=self.default_cache_ttl
            )
            
            self.logger.debug(f"Retrieved {len(data)} records (cache: {use_cache})")
            return data
        else:
            # 直接从数据源读取
            self.logger.debug("Loading all data directly from data source")
            data = self.data_source.read_all_data()
            self.logger.debug(f"Retrieved {len(data)} records from data source")
            return data
    
    def get_latest_data(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取最新的传感器数据
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            最新的传感器数据，如果没有数据则返回None
        """
        if use_cache and self.cache_manager:
            def data_loader():
                self.logger.debug("Loading latest data from data source")
                return self.data_source.read_latest_data()
            
            data = self.cache_manager.get_or_set(
                self.CACHE_KEY_LATEST,
                data_loader,
                ttl=self.default_cache_ttl
            )
            
            self.logger.debug(f"Retrieved latest record: {data is not None}")
            return data
        else:
            # 直接从数据源读取
            self.logger.debug("Loading latest data directly from data source")
            data = self.data_source.read_latest_data()
            self.logger.debug(f"Retrieved latest record from data source: {data is not None}")
            return data
    
    def get_recent_data(self, limit: int, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取最近N条传感器数据
        
        Args:
            limit: 记录数量限制
            use_cache: 是否使用缓存
            
        Returns:
            最近N条传感器数据列表
        """
        if limit <= 0:
            return self.get_all_data(use_cache)
        
        cache_key = f"{self.CACHE_KEY_RECENT_PREFIX}:{limit}"
        
        if use_cache and self.cache_manager:
            def data_loader():
                self.logger.debug(f"Loading recent {limit} records from data source")
                return self.data_source.read_recent_data(limit)
            
            data = self.cache_manager.get_or_set(
                cache_key,
                data_loader,
                ttl=self.default_cache_ttl
            )
            
            self.logger.debug(f"Retrieved {len(data)} recent records (limit: {limit})")
            return data
        else:
            # 直接从数据源读取
            self.logger.debug(f"Loading recent {limit} records directly from data source")
            data = self.data_source.read_recent_data(limit)
            self.logger.debug(f"Retrieved {len(data)} recent records from data source")
            return data
    
    def get_data_count(self, use_cache: bool = True) -> int:
        """
        获取数据总数
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            数据记录总数
        """
        if use_cache and self.cache_manager:
            def data_loader():
                self.logger.debug("Loading data count from data source")
                return self.data_source.get_data_count()
            
            count = self.cache_manager.get_or_set(
                self.CACHE_KEY_COUNT,
                data_loader,
                ttl=self.default_cache_ttl
            )
            
            self.logger.debug(f"Retrieved data count: {count}")
            return count
        else:
            # 直接从数据源读取
            self.logger.debug("Loading data count directly from data source")
            count = self.data_source.get_data_count()
            self.logger.debug(f"Retrieved data count from data source: {count}")
            return count
    
    def get_data_stats(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            包含统计信息的字典
        """
        cache_key = "stats:overview"
        
        if use_cache and self.cache_manager:
            def stats_loader():
                self.logger.debug("Computing data statistics")
                return self._compute_data_stats()
            
            stats = self.cache_manager.get_or_set(
                cache_key,
                stats_loader,
                ttl=self.default_cache_ttl
            )
            
            return stats
        else:
            # 直接计算统计信息
            return self._compute_data_stats()
    
    def _compute_data_stats(self) -> Dict[str, Any]:
        """计算数据统计信息"""
        try:
            data = self.data_source.read_all_data()
            
            if not data:
                return {
                    "total_records": 0,
                    "latest_timestamp": None,
                    "oldest_timestamp": None,
                    "temperature": {"min": None, "max": None, "avg": None},
                    "humidity": {"min": None, "max": None, "avg": None},
                    "pressure": {"min": None, "max": None, "avg": None},
                    "lux": {"min": None, "max": None, "avg": None},
                    "sway_speed": {"min": None, "max": None, "avg": None}
                }
            
            # 提取数值字段
            temperatures = [record["temperature_C"] for record in data]
            humidity_values = [record["humidity_RH"] for record in data]
            pressure_values = [record["pressure_hPa"] for record in data]
            lux_values = [record["lux"] for record in data]
            sway_values = [record["sway_speed_dps"] for record in data]
            
            stats = {
                "total_records": len(data),
                "latest_timestamp": data[-1]["timestamp_Beijing"] if data else None,
                "oldest_timestamp": data[0]["timestamp_Beijing"] if data else None,
                "temperature": {
                    "min": min(temperatures),
                    "max": max(temperatures),
                    "avg": sum(temperatures) / len(temperatures)
                },
                "humidity": {
                    "min": min(humidity_values),
                    "max": max(humidity_values),
                    "avg": sum(humidity_values) / len(humidity_values)
                },
                "pressure": {
                    "min": min(pressure_values),
                    "max": max(pressure_values),
                    "avg": sum(pressure_values) / len(pressure_values)
                },
                "lux": {
                    "min": min(lux_values),
                    "max": max(lux_values),
                    "avg": sum(lux_values) / len(lux_values)
                },
                "sway_speed": {
                    "min": min(sway_values),
                    "max": max(sway_values),
                    "avg": sum(sway_values) / len(sway_values)
                },
                "computed_at": datetime.now().isoformat()
            }
            
            self.logger.debug(f"Computed statistics for {len(data)} records")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error computing data statistics: {e}")
            return {
                "error": str(e),
                "computed_at": datetime.now().isoformat()
            }
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """
        失效缓存
        
        Args:
            pattern: 缓存键模式，None表示失效所有相关缓存
            
        Returns:
            失效的缓存键数量
        """
        if not self.cache_manager:
            self.logger.warning("Cache manager not available, cannot invalidate cache")
            return 0
        
        if pattern:
            deleted = self.cache_manager.delete_pattern(pattern)
            self.logger.info(f"Invalidated cache pattern '{pattern}': {deleted} keys")
        else:
            # 失效所有数据相关的缓存
            deleted = self.cache_manager.invalidate_data_cache()
            self.logger.info(f"Invalidated all data cache: {deleted} keys")
        
        return deleted
    
    def refresh_cache(self, warm_up: bool = True) -> None:
        """
        刷新缓存数据
        
        Args:
            warm_up: 是否预热常用缓存
        """
        if not self.cache_manager:
            self.logger.warning("Cache manager not available, cannot refresh cache")
            return
        
        # 首先失效现有缓存
        self.invalidate_cache()
        
        if warm_up:
            self.logger.info("Warming up cache...")
            
            # 预热常用数据
            warm_up_funcs = {
                self.CACHE_KEY_ALL_DATA: lambda: self.data_source.read_all_data(),
                self.CACHE_KEY_LATEST: lambda: self.data_source.read_latest_data(),
                self.CACHE_KEY_COUNT: lambda: self.data_source.get_data_count(),
                f"{self.CACHE_KEY_RECENT_PREFIX}:100": lambda: self.data_source.read_recent_data(100),
                f"{self.CACHE_KEY_RECENT_PREFIX}:50": lambda: self.data_source.read_recent_data(50),
                "stats:overview": lambda: self._compute_data_stats()
            }
            
            self.cache_manager.warm_up_cache(warm_up_funcs, ttl=self.default_cache_ttl)
            self.logger.info("Cache warm-up completed")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息
        
        Returns:
            服务状态信息
        """
        data_info = self.data_source.get_data_info()
        cache_info = self.cache_manager.get_cache_info() if self.cache_manager else None
        
        service_info = {
            "service_name": "SensorService",
            "data_source": data_info,
            "cache": cache_info,
            "cache_ttl": self.default_cache_ttl,
            "timestamp": datetime.now().isoformat()
        }
        
        # 尝试获取服务健康状态
        try:
            count = self.get_data_count(use_cache=False)  # 直接检查数据源
            service_info["health"] = "healthy"
            service_info["data_available"] = count > 0
        except Exception as e:
            service_info["health"] = "unhealthy"
            service_info["error"] = str(e)
            service_info["data_available"] = False
        
        return service_info
    
    def check_data_freshness(self) -> bool:
        """
        检查数据是否有更新
        如果有更新，自动刷新相关缓存
        
        Returns:
            数据是否有更新
        """
        try:
            if self.data_source.is_data_updated():
                self.logger.info("Data source updated, refreshing cache")
                self.refresh_cache(warm_up=False)  # 不预热，只是失效现有缓存
                
                # 更新最后更新时间缓存
                if self.cache_manager:
                    self.cache_manager.set(
                        self.CACHE_KEY_LAST_UPDATE,
                        datetime.now().isoformat(),
                        ttl=86400  # 24小时TTL
                    )
                
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking data freshness: {e}")
            return False


# 全局服务实例（懒加载）
_global_sensor_service: Optional[SensorService] = None


def get_sensor_service(
    data_source: Optional[DataSource] = None,
    cache_manager: Optional[CacheManager] = None,
    **kwargs
) -> SensorService:
    """
    获取全局传感器服务实例
    
    Args:
        data_source: 数据源实例
        cache_manager: 缓存管理器实例
        **kwargs: SensorService的其他参数
        
    Returns:
        SensorService实例
    """
    global _global_sensor_service
    
    if _global_sensor_service is None:
        if data_source is None:
            raise ValueError("Data source is required for first-time initialization")
        
        _global_sensor_service = SensorService(
            data_source=data_source,
            cache_manager=cache_manager,
            **kwargs
        )
    
    return _global_sensor_service


def clear_global_sensor_service() -> None:
    """清除全局服务实例（主要用于测试）"""
    global _global_sensor_service
    _global_sensor_service = None


if __name__ == "__main__":
    # 测试代码
    import time
    from .data_access import FileDataSource
    from .cache_manager import CacheManager
    from pprint import pprint
    
    print("Sensor Service Test")
    print("=" * 60)
    
    try:
        # 创建数据源和缓存管理器
        data_source = FileDataSource()
        cache_manager = CacheManager()
        
        # 创建服务实例
        service = SensorService(data_source, cache_manager, default_cache_ttl=60)
        
        # 获取服务信息
        print("Service Info:")
        pprint(service.get_service_info())
        print()
        
        # 测试数据获取（第一次调用，应该从数据源加载）
        print("Testing data retrieval...")
        
        start_time = time.time()
        all_data = service.get_all_data()
        first_call_time = time.time() - start_time
        print(f"First call (from source): {len(all_data)} records in {first_call_time:.3f}s")
        
        # 第二次调用（应该从缓存获取）
        start_time = time.time()
        cached_data = service.get_all_data()
        second_call_time = time.time() - start_time
        print(f"Second call (from cache): {len(cached_data)} records in {second_call_time:.3f}s")
        
        # 性能提升
        if first_call_time > 0:
            improvement = (first_call_time - second_call_time) / first_call_time * 100
            print(f"Performance improvement: {improvement:.1f}%")
        
        print()
        
        # 测试其他方法
        latest = service.get_latest_data()
        if latest:
            print(f"Latest record: {latest['timestamp_Beijing']} - {latest['temperature_C']}°C")
        
        recent_5 = service.get_recent_data(5)
        print(f"Recent 5 records: {len(recent_5)} found")
        
        count = service.get_data_count()
        print(f"Total count: {count}")
        
        print()
        
        # 测试统计信息
        print("Data Statistics:")
        stats = service.get_data_stats()
        if "error" not in stats:
            print(f"  Temperature: {stats['temperature']['min']:.1f}°C ~ {stats['temperature']['max']:.1f}°C (avg: {stats['temperature']['avg']:.1f}°C)")
            print(f"  Humidity: {stats['humidity']['min']:.1f}% ~ {stats['humidity']['max']:.1f}% (avg: {stats['humidity']['avg']:.1f}%)")
            print(f"  Records: {stats['total_records']}")
        else:
            print(f"  Error: {stats['error']}")
        
        print()
        
        # 测试缓存失效和刷新
        print("Testing cache operations...")
        invalidated = service.invalidate_cache()
        print(f"Invalidated {invalidated} cache keys")
        
        # 测试数据新鲜度检查
        updated = service.check_data_freshness()
        print(f"Data updated: {updated}")
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nSensor service test completed!")