# utils/cache_manager.py
"""
Redis缓存管理器
提供统一的缓存接口，支持任何数据源类型
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Redis缓存管理器，支持降级策略"""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True,
        key_prefix: str = "linescope"
    ):
        """
        初始化Redis缓存管理器
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: Redis数据库编号
            password: Redis密码
            decode_responses: 是否自动解码响应
            socket_connect_timeout: 连接超时时间
            socket_timeout: 操作超时时间
            retry_on_timeout: 超时是否重试
            key_prefix: 缓存键前缀
        """
        self.key_prefix = key_prefix
        self.logger = logging.getLogger(__name__)
        self._redis_client = None
        self._connection_params = {
            "host": host,
            "port": port,
            "db": db,
            "password": password,
            "decode_responses": decode_responses,
            "socket_connect_timeout": socket_connect_timeout,
            "socket_timeout": socket_timeout,
            "retry_on_timeout": retry_on_timeout
        }
        
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis module not available. Cache will be disabled.")
            return
            
        self._connect()
    
    def _connect(self) -> None:
        """建立Redis连接"""
        if not REDIS_AVAILABLE:
            return
            
        try:
            self._redis_client = redis.Redis(**self._connection_params)
            # 测试连接
            self._redis_client.ping()
            self.logger.info(f"Redis connection established: {self._connection_params['host']}:{self._connection_params['port']}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self._redis_client = None
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键"""
        return f"{self.key_prefix}:{key}"
    
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not REDIS_AVAILABLE or self._redis_client is None:
            return False
            
        try:
            self._redis_client.ping()
            return True
        except Exception as e:
            self.logger.warning(f"Redis ping failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或Redis不可用则返回None
        """
        if not self.is_available():
            return None
            
        try:
            full_key = self._make_key(key)
            data = self._redis_client.get(full_key)
            if data is None:
                return None
                
            # 尝试JSON反序列化
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接返回字符串
                return data
                
        except Exception as e:
            self.logger.error(f"Cache get error for key '{key}': {e}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 生存时间（秒），None表示永不过期
            nx: 只在键不存在时设置
            xx: 只在键存在时设置
            
        Returns:
            是否设置成功
        """
        if not self.is_available():
            return False
            
        try:
            full_key = self._make_key(key)
            
            # 序列化数据
            if isinstance(value, (str, int, float, bool)):
                serialized_value = value
            else:
                serialized_value = json.dumps(value, ensure_ascii=False)
            
            # 设置缓存
            result = self._redis_client.set(
                full_key, 
                serialized_value, 
                ex=ttl,
                nx=nx,
                xx=xx
            )
            
            if result:
                self.logger.debug(f"Cache set successful for key '{key}' (TTL: {ttl}s)")
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Cache set error for key '{key}': {e}")
            return False
    
    def get_or_set(
        self, 
        key: str, 
        loader_func: Callable[[], Any], 
        ttl: int = 1800
    ) -> Any:
        """
        获取缓存数据，如果不存在则调用加载函数并设置缓存
        
        Args:
            key: 缓存键
            loader_func: 数据加载函数
            ttl: 生存时间（秒）
            
        Returns:
            缓存或加载的数据
        """
        # 尝试从缓存获取
        cached_data = self.get(key)
        if cached_data is not None:
            self.logger.debug(f"Cache hit for key '{key}'")
            return cached_data
        
        # 缓存未命中，调用加载函数
        self.logger.debug(f"Cache miss for key '{key}', loading data")
        try:
            data = loader_func()
            
            # 设置缓存
            if self.is_available():
                self.set(key, data, ttl)
                self.logger.debug(f"Data cached for key '{key}'")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Data loader error for key '{key}': {e}")
            raise
    
    def delete(self, key: str) -> bool:
        """
        删除缓存键
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self.is_available():
            return False
            
        try:
            full_key = self._make_key(key)
            result = self._redis_client.delete(full_key)
            self.logger.debug(f"Cache delete for key '{key}': {result}")
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Cache delete error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存键
        
        Args:
            pattern: 键匹配模式（支持通配符*）
            
        Returns:
            删除的键数量
        """
        if not self.is_available():
            return 0
            
        try:
            full_pattern = self._make_key(pattern)
            keys = self._redis_client.keys(full_pattern)
            
            if not keys:
                return 0
                
            result = self._redis_client.delete(*keys)
            self.logger.info(f"Cache pattern delete '{pattern}': {result} keys removed")
            return result
            
        except Exception as e:
            self.logger.error(f"Cache pattern delete error for pattern '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.is_available():
            return False
            
        try:
            full_key = self._make_key(key)
            return bool(self._redis_client.exists(full_key))
            
        except Exception as e:
            self.logger.error(f"Cache exists check error for key '{key}': {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        获取缓存键的剩余生存时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余TTL（秒），-1表示永不过期，-2表示不存在
        """
        if not self.is_available():
            return -2
            
        try:
            full_key = self._make_key(key)
            return self._redis_client.ttl(full_key)
            
        except Exception as e:
            self.logger.error(f"Cache TTL check error for key '{key}': {e}")
            return -2
    
    def invalidate_data_cache(self) -> int:
        """
        失效所有数据相关的缓存
        
        Returns:
            删除的缓存键数量
        """
        patterns = ["data:*", "meta:*"]
        total_deleted = 0
        
        for pattern in patterns:
            deleted = self.delete_pattern(pattern)
            total_deleted += deleted
            
        self.logger.info(f"Data cache invalidation completed: {total_deleted} keys deleted")
        return total_deleted
    
    def warm_up_cache(self, loader_funcs: Dict[str, Callable[[], Any]], ttl: int = 1800) -> None:
        """
        预热缓存
        
        Args:
            loader_funcs: 键到加载函数的映射
            ttl: 缓存生存时间
        """
        if not self.is_available():
            self.logger.warning("Redis not available, skipping cache warm-up")
            return
            
        self.logger.info("Starting cache warm-up")
        
        for key, loader_func in loader_funcs.items():
            try:
                if not self.exists(key):
                    data = loader_func()
                    self.set(key, data, ttl)
                    self.logger.debug(f"Cache warmed up for key '{key}'")
                else:
                    self.logger.debug(f"Cache key '{key}' already exists, skipping")
                    
            except Exception as e:
                self.logger.error(f"Cache warm-up failed for key '{key}': {e}")
        
        self.logger.info("Cache warm-up completed")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息和统计
        
        Returns:
            缓存信息字典
        """
        info = {
            "available": self.is_available(),
            "redis_available": REDIS_AVAILABLE,
            "key_prefix": self.key_prefix,
            "connection_params": {
                k: v for k, v in self._connection_params.items() 
                if k != "password"  # 不返回密码
            }
        }
        
        if self.is_available():
            try:
                # 获取当前项目的缓存键数量
                pattern = self._make_key("*")
                keys = self._redis_client.keys(pattern)
                info["cache_keys_count"] = len(keys)
                info["sample_keys"] = keys[:10]  # 前10个键作为样本
                
                # Redis服务器信息
                redis_info = self._redis_client.info()
                info["redis_version"] = redis_info.get("redis_version")
                info["used_memory_human"] = redis_info.get("used_memory_human")
                info["connected_clients"] = redis_info.get("connected_clients")
                
            except Exception as e:
                self.logger.error(f"Error getting cache info: {e}")
                info["error"] = str(e)
        
        return info


# 全局缓存管理器实例（懒加载）
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager(**kwargs) -> CacheManager:
    """
    获取全局缓存管理器实例
    
    Args:
        **kwargs: CacheManager的初始化参数
        
    Returns:
        CacheManager实例
    """
    global _global_cache_manager
    
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(**kwargs)
    
    return _global_cache_manager


def clear_global_cache_manager() -> None:
    """清除全局缓存管理器实例（主要用于测试）"""
    global _global_cache_manager
    _global_cache_manager = None


if __name__ == "__main__":
    # 测试代码
    import time
    
    # 创建缓存管理器
    cache = CacheManager()
    
    print("Cache Manager Test")
    print("=" * 50)
    
    # 测试缓存信息
    info = cache.get_cache_info()
    print(f"Cache available: {info['available']}")
    print(f"Redis available: {info['redis_available']}")
    
    if cache.is_available():
        # 测试基本操作
        test_key = "test:data"
        test_data = {"message": "Hello Redis", "timestamp": datetime.now().isoformat()}
        
        # 设置缓存
        success = cache.set(test_key, test_data, ttl=60)
        print(f"Set cache: {success}")
        
        # 获取缓存
        cached = cache.get(test_key)
        print(f"Get cache: {cached}")
        
        # 测试get_or_set
        def load_test_data():
            print("Loading data from source...")
            return {"loaded": True, "time": time.time()}
        
        data1 = cache.get_or_set("test:loader", load_test_data, ttl=30)
        print(f"First call (should load): {data1}")
        
        data2 = cache.get_or_set("test:loader", load_test_data, ttl=30)
        print(f"Second call (should cache): {data2}")
        
        # 测试删除
        deleted = cache.delete(test_key)
        print(f"Delete cache: {deleted}")
        
        # 验证删除
        after_delete = cache.get(test_key)
        print(f"After delete: {after_delete}")
        
    else:
        print("Redis not available, testing fallback behavior")
        
        def loader():
            return {"fallback": True}
            
        # 应该直接调用loader
        result = cache.get_or_set("test", loader)
        print(f"Fallback result: {result}")