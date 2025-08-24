# Linescope Server - 贵州线镜项目服务器端

## 项目概述

Linescope Server 是贵州线镜项目的服务器端应用，采用 Python Flask 框架构建。本项目为线路监控系统提供数据接收、处理、存储和可视化功能。

整个系统由四个主要组件构成：

1. **STM32 传感器集群** - 传感器通过 STM32F4 连接，负责数据采集和汇总
2. **4G 监控模块** - 负责数据传输和远程监控
3. **香橙派** - 处理数据并进行图像识别
4. **服务器** - 接收数据并提供 Web 界面展示

## 系统架构与数据流

### 数据处理流程

1. **数据采集**: STM32F4 收集传感器数据并通过数传模块发送到香橙派
2. **数据传输**: 香橙派每30分钟通过4G模块向服务器发送数据
3. **图像处理**: 4G监控模块获取图像，香橙派进行图像识别后传输结果
4. **数据展示**: 服务器接收数据并在Web界面实时展示

### 技术栈

- **后端框架**: Flask 3.1.2
- **图像处理**: OpenCV 4.12.0
- **数据处理**: NumPy 2.2.6
- **前端**: HTML5 + CSS3 + JavaScript
- **部署**: 支持 Gunicorn/Waitress

## 项目结构（重构后）

```
Linescope_Server/
├── app.py                    # 主应用入口文件
├── app_old.py               # 重构前的备份文件
├── requirements.txt          # 项目依赖
├── app.log                  # 应用日志文件
├── config/                  # 配置模块
│   ├── __init__.py
│   └── settings.py          # 应用配置和日志设置
├── core/                    # 核心功能模块
│   ├── __init__.py
│   ├── factory.py           # Flask 应用工厂
│   ├── jobs.py              # 后台任务管理
│   └── streaming.py         # 视频流处理
├── routes/                  # 路由模块
│   ├── __init__.py
│   ├── main.py              # 主页面路由
│   └── api.py               # API 接口路由
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── DataRead.py          # 数据读取
│   ├── DataStore.py         # 数据存储
│   ├── GetImage.py          # 图像获取
│   ├── GetSensorData.py     # 传感器数据获取
│   └── data/                # 数据文件目录
├── templates/               # HTML 模板
│   ├── index.html           # 首页
│   ├── dashboard.html       # 数据仪表板
│   └── result.html          # 图像识别结果页
└── static/                  # 静态资源
    ├── css/
    │   └── styles.css       # 样式文件
    ├── js/
    │   └── script.js        # 前端脚本
    ├── images/              # 图片资源
    └── favicon.ico          # 网站图标
```

## 重构说明

本次重构主要完成了以下优化：

### 1. 模块化架构
- **配置分离**: 将配置相关代码移至 `config/` 模块
- **核心功能解耦**: 将应用工厂、后台任务、流媒体处理分离到 `core/` 模块  
- **路由分离**: 将页面路由和API路由分别组织到 `routes/` 模块

### 2. 代码组织改进
- **app.py 简化**: 从286行代码简化至21行，仅保留应用入口逻辑
- **职责单一**: 每个模块职责明确，便于维护和测试
- **导入优化**: 统一模块导入和依赖管理

### 3. 可维护性提升
- **配置集中管理**: 所有配置参数集中在 `AppConfig` 类中
- **日志标准化**: 统一的日志配置和格式
- **错误处理**: 完善的异常处理和日志记录

## 安装与运行

### 环境要求

- Python 3.7+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

#### 开发模式
```bash
python app.py
```

#### 生产模式 (推荐)
```bash
# 使用 Gunicorn (Linux/macOS)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 使用 Waitress (Windows)
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

应用将在 `http://localhost:5000` 启动。

## API 接口

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 应用首页 |
| `/dashboard` | GET | 数据仪表板页面 |
| `/result` | GET | 图像识别结果页面 |
| `/stream.mjpg` | GET | MJPEG 视频流 |
| `/api/sensor-data` | GET | 获取传感器数据 |
| `/api/sensors?limit=N` | GET | 获取最近N条传感器数据 |
| `/api/sensors/latest` | GET | 获取最新传感器数据 |
| `/healthz` | GET | 健康检查 |

### 数据格式

传感器数据接口返回 JSON 格式的数组，每个元素包含：

```json
[
  {
    "timestamp": "2024-08-24T10:30:00",
    "sensor_id": "001",
    "temperature": 25.6,
    "humidity": 65.2,
    "voltage": 3.3
  }
]
```

## 配置说明

应用配置位于 `config/settings.py` 中的 `AppConfig` 类：

- `datastore_interval_minutes`: 数据存储间隔（分钟，默认30）
- `stream_frame_interval_sec`: 视频流帧间隔（秒，默认0.2）
- `log_file`: 日志文件路径
- `log_max_bytes`: 日志文件最大大小（字节）
- `log_backup_count`: 日志备份文件数量

## 开发指南

### 添加新路由

1. 在 `routes/main.py` 添加页面路由
2. 在 `routes/api.py` 添加 API 路由
3. 在对应的注册函数中添加路由装饰器

### 修改配置

1. 在 `config/settings.py` 的 `AppConfig` 类中添加新配置项
2. 在需要使用的模块中通过 `app.config["APP_CFG"]` 访问

### 添加后台任务

1. 在 `core/jobs.py` 中定义任务函数
2. 在 `core/factory.py` 中使用 `PeriodicJob` 类创建定时任务

## 故障排查

### 常见问题

1. **模块导入错误**: 确保项目根目录在 Python 路径中
2. **依赖缺失**: 运行 `pip install -r requirements.txt` 安装依赖
3. **端口占用**: 修改 `app.py` 中的端口号或停止占用进程
4. **权限错误**: 确保日志文件目录有写入权限

### 日志查看

应用日志保存在 `app.log` 文件中，使用滚动日志机制：

```bash
# 查看最新日志
tail -f app.log

# 查看错误日志
grep ERROR app.log
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目仓库: [GitHub Repository URL]
- 邮箱: [contact@example.com]

---

*最后更新: 2024年8月*