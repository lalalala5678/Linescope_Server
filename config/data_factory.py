# config/data_factory.py
"""
数据服务工厂模块
基于配置创建相应的数据源和服务实例
支持配置驱动的架构切换
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from utils.data_access import DataSource, FileDataSource, SQLDataSource, create_data_source
from utils.cache_manager import CacheManager, get_cache_manager
from utils.sensor_service import SensorService
from config.settings import AppConfig


class DataFactory:
    """数据服务工厂类"""
    
    def __init__(self, config: AppConfig):
        """
        初始化数据工厂
        
        Args:
            config: 应用配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._data_source: Optional[DataSource] = None
        self._cache_manager: Optional[CacheManager] = None
        self._sensor_service: Optional[SensorService] = None
    
    def get_data_source(self) -> DataSource:
        """
        获取数据源实例（单例模式）
        
        Returns:
            配置的数据源实例
        """
        if self._data_source is None:
            self._data_source = self._create_data_source()
            self.logger.info(f"Created data source: {self._data_source.__class__.__name__}")
        
        return self._data_source
    
    def get_cache_manager(self) -> Optional[CacheManager]:
        """
        获取缓存管理器实例（单例模式）
        
        Returns:
            缓存管理器实例，如果缓存未启用则返回None
        """
        if not self.config.cache_enabled:
            return None
            
        if self._cache_manager is None:
            self._cache_manager = self._create_cache_manager()
            if self._cache_manager:
                self.logger.info("Created cache manager")
            else:
                self.logger.warning("Failed to create cache manager")
        
        return self._cache_manager
    
    def get_sensor_service(self) -> SensorService:
        """
        获取传感器服务实例（单例模式）
        
        Returns:
            传感器服务实例
        """
        if self._sensor_service is None:
            data_source = self.get_data_source()
            cache_manager = self.get_cache_manager()
            
            self._sensor_service = SensorService(
                data_source=data_source,
                cache_manager=cache_manager,
                default_cache_ttl=self.config.cache_ttl
            )
            
            self.logger.info("Created sensor service")
        
        return self._sensor_service
    
    def _create_data_source(self) -> DataSource:
        """根据配置创建数据源"""
        source_type = self.config.data_source_type.lower()
        
        try:
            if source_type == "file":
                return self._create_file_data_source()
            elif source_type == "sql":
                return self._create_sql_data_source()
            else:
                raise ValueError(f"Unsupported data source type: {source_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to create data source ({source_type}): {e}")
            # 降级到文件数据源
            if source_type != "file":
                self.logger.info("Falling back to file data source")
                return self._create_file_data_source()
            else:
                raise
    
    def _create_file_data_source(self) -> FileDataSource:
        """创建文件数据源"""
        file_path = self.config.data_file_path
        
        # 支持相对路径（相对于项目根目录）
        if not os.path.isabs(file_path):
            from config.settings import PROJECT_ROOT
            file_path = os.path.join(PROJECT_ROOT, file_path)
        
        return FileDataSource(file_path)
    
    def _create_sql_data_source(self) -> SQLDataSource:
        """创建SQL数据源"""
        if not self.config.db_connection_string:
            raise ValueError("Database connection string is required for SQL data source")
        
        return SQLDataSource(
            connection_string=self.config.db_connection_string,
            table_name=self.config.db_table_name,
            pool_size=self.config.db_pool_size
        )
    
    def _create_cache_manager(self) -> Optional[CacheManager]:
        """创建缓存管理器"""
        try:
            # 从环境变量获取Redis配置（优先级高于配置文件）
            redis_host = os.getenv("REDIS_HOST", self.config.redis_host)
            redis_port = int(os.getenv("REDIS_PORT", self.config.redis_port))
            redis_db = int(os.getenv("REDIS_DB", self.config.redis_db))
            redis_password = os.getenv("REDIS_PASSWORD", self.config.redis_password)
            
            return CacheManager(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                key_prefix=self.config.cache_key_prefix
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create cache manager: {e}")
            return None
    
    def health_check(self) -> dict:
        """
        执行健康检查
        
        Returns:
            包含各组件健康状态的字典
        """
        health_info = {
            "timestamp": self._get_current_timestamp(),
            "data_source": {"status": "unknown"},
            "cache": {"status": "unknown"},
            "service": {"status": "unknown"}
        }
        
        # 检查数据源
        try:
            data_source = self.get_data_source()
            data_info = data_source.get_data_info()
            health_info["data_source"] = {
                "status": "healthy" if data_info.get("status") != "error" else "unhealthy",
                "type": data_info.get("source_type"),
                "records": data_info.get("record_count", 0),
                "details": data_info
            }
        except Exception as e:
            health_info["data_source"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # 检查缓存
        try:
            cache_manager = self.get_cache_manager()
            if cache_manager:
                cache_info = cache_manager.get_cache_info()
                health_info["cache"] = {
                    "status": "healthy" if cache_info["available"] else "unhealthy",
                    "enabled": True,
                    "details": cache_info
                }
            else:
                health_info["cache"] = {
                    "status": "disabled",
                    "enabled": False,
                    "message": "Cache is disabled in configuration"
                }
        except Exception as e:
            health_info["cache"] = {
                "status": "unhealthy",
                "enabled": True,
                "error": str(e)
            }
        
        # 检查服务
        try:
            service = self.get_sensor_service()
            service_info = service.get_service_info()
            health_info["service"] = {
                "status": service_info.get("health", "unknown"),
                "data_available": service_info.get("data_available", False),
                "cache_ttl": service_info.get("cache_ttl"),
                "details": service_info
            }
        except Exception as e:
            health_info["service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # 计算总体健康状态
        component_statuses = [
            health_info["data_source"]["status"],
            health_info["cache"]["status"] if health_info["cache"]["status"] != "disabled" else "healthy",
            health_info["service"]["status"]
        ]
        
        if all(status == "healthy" for status in component_statuses):
            health_info["overall_status"] = "healthy"
        elif any(status == "unhealthy" for status in component_statuses):
            health_info["overall_status"] = "unhealthy"  
        else:
            health_info["overall_status"] = "degraded"
        
        return health_info
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def reset(self) -> None:
        """重置工厂实例（主要用于配置更改后的重新初始化）"""
        self._data_source = None
        self._cache_manager = None
        self._sensor_service = None
        self.logger.info("Data factory reset completed")


# 全局工厂实例（懒加载）
_global_data_factory: Optional[DataFactory] = None


def get_data_factory(config: Optional[AppConfig] = None) -> DataFactory:
    """
    获取全局数据工厂实例
    
    Args:
        config: 应用配置，仅在首次调用时需要
        
    Returns:
        DataFactory实例
    """
    global _global_data_factory
    
    if _global_data_factory is None:
        if config is None:
            # 如果没有提供配置，创建默认配置
            config = AppConfig()
        
        _global_data_factory = DataFactory(config)
    
    return _global_data_factory


def clear_global_data_factory() -> None:
    """清除全局工厂实例（主要用于测试或配置变更）"""
    global _global_data_factory
    _global_data_factory = None


def create_sensor_service_from_config(config: Optional[AppConfig] = None) -> SensorService:
    """
    便捷函数：根据配置创建传感器服务
    
    Args:
        config: 应用配置
        
    Returns:
        配置好的SensorService实例
    """
    factory = get_data_factory(config)
    return factory.get_sensor_service()


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.append('..')
    
    from pprint import pprint
    
    print("Data Factory Test")
    print("=" * 50)
    
    try:
        # 创建测试配置
        config = AppConfig()
        config.cache_enabled = True
        config.cache_ttl = 60
        
        # 创建工厂实例
        factory = DataFactory(config)
        
        print("Factory Configuration:")
        print(f"  Data source type: {config.data_source_type}")
        print(f"  Cache enabled: {config.cache_enabled}")
        print(f"  Cache TTL: {config.cache_ttl}s")
        print()
        
        # 测试数据源创建
        print("Creating data source...")
        data_source = factory.get_data_source()
        print(f"  Created: {data_source.__class__.__name__}")
        
        # 测试缓存管理器创建
        print("Creating cache manager...")
        cache_manager = factory.get_cache_manager()
        if cache_manager:
            print(f"  Created: {cache_manager.__class__.__name__}")
            print(f"  Available: {cache_manager.is_available()}")
        else:
            print("  Cache manager not created (disabled or failed)")
        print()
        
        # 测试服务创建
        print("Creating sensor service...")
        service = factory.get_sensor_service()
        print(f"  Created: {service.__class__.__name__}")
        print()
        
        # 执行健康检查
        print("Health Check Results:")
        health = factory.health_check()
        print(f"  Overall Status: {health['overall_status']}")
        print(f"  Data Source: {health['data_source']['status']}")
        print(f"  Cache: {health['cache']['status']}")
        print(f"  Service: {health['service']['status']}")
        
        if health['data_source']['status'] == 'healthy':
            print(f"  Records Available: {health['data_source']['records']}")
        
        print()
        
        # 测试服务功能
        if health['overall_status'] in ['healthy', 'degraded']:
            print("Testing service functionality...")
            
            try:
                # 测试数据获取
                latest = service.get_latest_data()
                if latest:
                    print(f"  Latest record: {latest['timestamp_Beijing']}")
                
                count = service.get_data_count()
                print(f"  Total records: {count}")
                
                recent = service.get_recent_data(5)
                print(f"  Recent records: {len(recent)}")
                
            except Exception as e:
                print(f"  Service test error: {e}")
        
    except Exception as e:
        print(f"Factory test error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nData factory test completed!")