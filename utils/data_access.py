# utils/data_access.py
"""
数据访问抽象层
定义统一的数据访问接口，支持文件和SQL数据源
为未来升级提供良好的兼容性
"""
from __future__ import annotations

import csv
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging


class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def read_all_data(self) -> List[Dict[str, Any]]:
        """
        读取所有传感器数据
        
        Returns:
            传感器数据列表，每个元素包含以下字段：
            - timestamp_Beijing: str
            - sway_speed_dps: float  
            - temperature_C: float
            - humidity_RH: float
            - pressure_hPa: float
            - lux: float
        """
        pass
    
    @abstractmethod
    def read_latest_data(self) -> Optional[Dict[str, Any]]:
        """
        读取最新的一条传感器数据
        
        Returns:
            最新的传感器数据记录，如果没有数据则返回None
        """
        pass
    
    @abstractmethod
    def get_data_count(self) -> int:
        """
        获取数据总数
        
        Returns:
            数据记录总数
        """
        pass
    
    @abstractmethod
    def read_recent_data(self, limit: int) -> List[Dict[str, Any]]:
        """
        读取最近N条传感器数据
        
        Args:
            limit: 要获取的记录数量
            
        Returns:
            最近的传感器数据列表
        """
        pass
    
    @abstractmethod
    def is_data_updated(self) -> bool:
        """
        检查数据是否已更新（相比上次检查）
        
        Returns:
            如果数据有更新则返回True
        """
        pass
    
    @abstractmethod
    def get_data_info(self) -> Dict[str, Any]:
        """
        获取数据源信息
        
        Returns:
            数据源相关信息
        """
        pass


class FileDataSource(DataSource):
    """基于CSV文件的数据源实现"""
    
    # 期望的列名
    EXPECTED_COLUMNS = [
        "timestamp_Beijing",
        "sway_speed_dps", 
        "temperature_C",
        "humidity_RH",
        "pressure_hPa",
        "lux",
        "wire_foreign_object",
    ]
    
    def __init__(self, file_path: Optional[str] = None):
        """
        初始化文件数据源
        
        Args:
            file_path: CSV文件路径，默认为 utils/data/data.txt
        """
        self.logger = logging.getLogger(__name__)
        
        # 设置默认文件路径
        if file_path is None:
            file_path = str(Path(__file__).resolve().parent / "data" / "data.txt")
            
        self.file_path = Path(file_path)
        self._last_mtime = 0
        
        # 验证文件存在性
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"数据文件不存在：{self.file_path}\n"
                f"请确保文件路径正确或数据文件已创建"
            )
    
    def _get_file_mtime(self) -> float:
        """获取文件修改时间"""
        try:
            return os.path.getmtime(self.file_path)
        except OSError:
            return 0
    
    def _parse_csv_data(self) -> List[Dict[str, Any]]:
        """解析CSV文件数据"""
        rows = []
        
        try:
            with self.file_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                
                # 验证表头
                if reader.fieldnames is None:
                    raise ValueError("无法读取CSV表头，请检查文件格式")
                    
                missing_columns = [col for col in self.EXPECTED_COLUMNS if col not in reader.fieldnames]
                if missing_columns:
                    raise ValueError(f"CSV文件缺少必需的列：{missing_columns}")
                
                # 解析数据行
                for row_num, row in enumerate(reader, 1):
                    try:
                        parsed_row = self._parse_data_row(row)
                        rows.append(parsed_row)
                    except (KeyError, ValueError, TypeError) as e:
                        self.logger.error(f"解析第{row_num}行数据失败: {row} - 错误: {e}")
                        continue  # 跳过错误行，继续处理
                        
        except FileNotFoundError:
            raise FileNotFoundError(f"数据文件不存在：{self.file_path}")
        except Exception as e:
            raise RuntimeError(f"读取CSV文件失败：{e}")
            
        return rows
    
    def _parse_data_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """解析单行数据"""
        parsed = {
            "timestamp_Beijing": row["timestamp_Beijing"].strip(),
            "sway_speed_dps": float(row["sway_speed_dps"]),
            "temperature_C": float(row["temperature_C"]),
            "humidity_RH": float(row["humidity_RH"]),
            "pressure_hPa": float(row["pressure_hPa"]),
            "lux": float(row["lux"]),
        }
        
        # 兼容性处理：如果存在异物检测字段则解析，否则默认为0
        if "wire_foreign_object" in row:
            parsed["wire_foreign_object"] = int(float(row["wire_foreign_object"]))
        else:
            parsed["wire_foreign_object"] = 0
            
        return parsed
    
    def read_all_data(self) -> List[Dict[str, Any]]:
        """读取所有传感器数据"""
        try:
            data = self._parse_csv_data()
            self.logger.debug(f"Successfully read {len(data)} records from {self.file_path}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to read all data: {e}")
            raise
    
    def read_latest_data(self) -> Optional[Dict[str, Any]]:
        """读取最新的一条传感器数据"""
        try:
            data = self.read_all_data()
            if not data:
                return None
            return data[-1]  # 返回最后一条记录
        except Exception as e:
            self.logger.error(f"Failed to read latest data: {e}")
            raise
    
    def get_data_count(self) -> int:
        """获取数据总数"""
        try:
            data = self.read_all_data()
            return len(data)
        except Exception as e:
            self.logger.error(f"Failed to get data count: {e}")
            return 0
    
    def read_recent_data(self, limit: int) -> List[Dict[str, Any]]:
        """读取最近N条传感器数据"""
        try:
            data = self.read_all_data()
            if limit <= 0:
                return data
            return data[-limit:]  # 返回最后N条记录
        except Exception as e:
            self.logger.error(f"Failed to read recent data (limit={limit}): {e}")
            raise
    
    def is_data_updated(self) -> bool:
        """检查数据是否已更新"""
        current_mtime = self._get_file_mtime()
        if current_mtime > self._last_mtime:
            self._last_mtime = current_mtime
            return True
        return False
    
    def get_data_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        info = {
            "source_type": "file",
            "file_path": str(self.file_path),
            "file_exists": self.file_path.exists(),
            "file_size": self.file_path.stat().st_size if self.file_path.exists() else 0,
            "last_modified": self._get_file_mtime(),
        }
        
        try:
            data_count = self.get_data_count()
            info["record_count"] = data_count
            info["status"] = "healthy"
        except Exception as e:
            info["record_count"] = 0
            info["status"] = "error"
            info["error"] = str(e)
            
        return info


class SQLDataSource(DataSource):
    """基于SQL数据库的数据源实现（预留接口）"""
    
    def __init__(
        self, 
        connection_string: str,
        table_name: str = "sensor_data",
        pool_size: int = 10
    ):
        """
        初始化SQL数据源
        
        Args:
            connection_string: 数据库连接字符串
            table_name: 表名
            pool_size: 连接池大小
        """
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.table_name = table_name
        self.pool_size = pool_size
        self._last_check_time = 0
        
        # 注意：这里暂时不实现实际的数据库连接
        # 在实际部署SQL时需要添加具体的数据库操作代码
        self.logger.info(f"SQLDataSource initialized (table: {table_name})")
    
    def read_all_data(self) -> List[Dict[str, Any]]:
        """读取所有传感器数据（SQL实现）"""
        # TODO: 实现SQL查询
        # SELECT * FROM sensor_data ORDER BY timestamp_Beijing
        raise NotImplementedError("SQL data source will be implemented in future deployment")
    
    def read_latest_data(self) -> Optional[Dict[str, Any]]:
        """读取最新的一条传感器数据（SQL实现）"""
        # TODO: 实现SQL查询
        # SELECT * FROM sensor_data ORDER BY timestamp_Beijing DESC LIMIT 1
        raise NotImplementedError("SQL data source will be implemented in future deployment")
    
    def get_data_count(self) -> int:
        """获取数据总数（SQL实现）"""
        # TODO: 实现SQL查询
        # SELECT COUNT(*) FROM sensor_data
        raise NotImplementedError("SQL data source will be implemented in future deployment")
    
    def read_recent_data(self, limit: int) -> List[Dict[str, Any]]:
        """读取最近N条传感器数据（SQL实现）"""
        # TODO: 实现SQL查询  
        # SELECT * FROM sensor_data ORDER BY timestamp_Beijing DESC LIMIT ?
        raise NotImplementedError("SQL data source will be implemented in future deployment")
    
    def is_data_updated(self) -> bool:
        """检查数据是否已更新（SQL实现）"""
        # TODO: 实现更新检查逻辑
        # 可以基于最大timestamp或触发器实现
        raise NotImplementedError("SQL data source will be implemented in future deployment")
    
    def get_data_info(self) -> Dict[str, Any]:
        """获取数据源信息（SQL实现）"""
        return {
            "source_type": "sql",
            "connection_string": self.connection_string.replace(
                self.connection_string.split("@")[0].split("//")[-1], "***"
            ) if "@" in self.connection_string else self.connection_string,
            "table_name": self.table_name,
            "pool_size": self.pool_size,
            "status": "not_implemented",
            "message": "SQL data source will be implemented in future deployment"
        }


def create_data_source(
    source_type: str = "file",
    file_path: Optional[str] = None,
    connection_string: Optional[str] = None,
    **kwargs
) -> DataSource:
    """
    数据源工厂函数
    
    Args:
        source_type: 数据源类型，"file" 或 "sql"
        file_path: 文件路径（用于file类型）
        connection_string: 数据库连接字符串（用于sql类型）
        **kwargs: 其他参数
        
    Returns:
        DataSource实例
    """
    if source_type.lower() == "file":
        return FileDataSource(file_path)
    elif source_type.lower() == "sql":
        if not connection_string:
            raise ValueError("SQL data source requires connection_string")
        return SQLDataSource(connection_string, **kwargs)
    else:
        raise ValueError(f"Unsupported data source type: {source_type}")


if __name__ == "__main__":
    # 测试代码
    import time
    from pprint import pprint
    
    print("Data Access Layer Test")
    print("=" * 50)
    
    try:
        # 测试文件数据源
        file_source = FileDataSource()
        
        # 获取数据源信息
        print("Data source info:")
        pprint(file_source.get_data_info())
        
        # 测试数据读取
        print(f"\nTotal records: {file_source.get_data_count()}")
        
        # 读取最新数据
        latest = file_source.read_latest_data()
        if latest:
            print(f"\nLatest record:")
            pprint(latest)
        
        # 读取最近5条数据
        recent = file_source.read_recent_data(5)
        print(f"\nRecent 5 records: {len(recent)} found")
        for i, record in enumerate(recent, 1):
            print(f"  {i}. {record['timestamp_Beijing']} - Temp: {record['temperature_C']}°C")
        
        # 测试数据更新检查
        print(f"\nData updated: {file_source.is_data_updated()}")
        print(f"Data updated again: {file_source.is_data_updated()}")  # 应该返回False
        
    except Exception as e:
        print(f"Error testing file data source: {e}")
    
    print("\n" + "=" * 50)
    
    # 测试SQL数据源（预期失败）
    try:
        sql_source = SQLDataSource("sqlite:///test.db")
        info = sql_source.get_data_info()
        print("SQL source info:")
        pprint(info)
        
        # 尝试读取数据（会抛出NotImplementedError）
        try:
            sql_source.read_all_data()
        except NotImplementedError as e:
            print(f"Expected error: {e}")
            
    except Exception as e:
        print(f"Error testing SQL data source: {e}")
    
    print("\nData access layer test completed!")