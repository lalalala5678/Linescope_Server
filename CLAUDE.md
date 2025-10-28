# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Linescope_Server 是一个高性能现代化的智能线缆监测系统，基于Flask框架构建。该系统集成了实时数据采集、图像识别、智能预警和可视化展示功能，为电力线缆监测提供全面的解决方案。

### 系统架构
整个系统采用分布式架构，由四个核心组件协同工作：
- **STM32传感器集群**: 温度、湿度、晃动、气压、光照传感器数据采集
- **4G监控模块**: 数据远程传输和图像获取
- **香橙派处理器**: 图像识别和数据处理
- **Flask服务器端**: Web界面展示、API接口服务、实时可视化

### 核心特性
- 现代化玻璃拟态UI设计，深色主题视觉效果
- 模块化Flask架构，采用工厂模式和蓝图路由
- 高性能前端优化：Service Worker缓存、GPU加速、模块化JavaScript
- 智能缓存系统：文件修改时间缓存、内存缓存策略
- 实时视频流：MJPEG流传输，支持多并发连接
- RESTful API设计：完善的错误处理和响应格式
- 生产环境部署：Docker容器化、Kubernetes支持

## 最新更新记录 (2025-08-29)

### CSV导出中文编码问题修复
**问题背景**: 系统中的CSV导出功能存在中文字符乱码问题，特别是在Excel中打开时，中文列标题和数据值显示为乱码。

**解决方案**:
- **异物检测监控页面** (`templates/result.html:1127-1170`): 完整重构CSV导出功能
  - 添加UTF-8 BOM (`\uFEFF`) 确保Excel正确识别中文字符编码
  - 实现符合RFC 4180标准的 `escapeCsvField()` 函数，处理包含逗号、引号或换行符的字段
  - 修复换行符问题：从 `\\n` 改为 `\n`，确保Excel中每条记录独占一行

- **数据仪表盘历史记录** (`static/js/app.js:884-929`): 统一CSV导出标准
  - 在 `exportToCSV()` 函数中添加相同的UTF-8 BOM和字段转义机制
  - 确保中文列标题（时间戳、晃动速度(°/s)、温度(°C)等）和状态值（有异物/正常）正确显示
  - 所有数据字段都经过适当的CSV转义处理

**技术实现**:
```javascript
// UTF-8 BOM用于Excel中文字符识别
const BOM = '\uFEFF';

// RFC 4180标准的CSV字段转义
const escapeCsvField = (field) => {
  if (field === null || field === undefined) return '';
  const str = String(field);
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
};
```

**验证结果**: Excel中完美显示所有中文字符，数据格式规范，每条记录独占一行。

### 自动数据更新系统修复
- 修复 `wire_foreign_object` 字段 None 值解析错误
- 实现时间依赖的异物检测数据生成算法
- 解决5:30自动更新任务失败问题

## 架构重构与优化成果 (2025-08-24)

### 核心架构改进

**1. 模块化Flask应用结构**
- 从单一 `app.py` 重构为 `core/factory.py` 的模块化架构
- 路由分离: `routes/main.py` (页面路由) 和 `routes/api.py` (API路由)
- 增强错误处理：全局404/500错误处理器
- 修复Flask模板/静态文件夹路径配置问题
- 实现应用工厂模式，支持多环境配置

**2. 前端现代化重构**
- **HTML模板系统**: 完全重新设计的现代化玻璃拟态UI
  - `templates/index.html`: 交互式仪表盘，实时度量显示
  - `templates/dashboard.html`: 高级数据可视化，集成AG-Grid
  - `templates/result.html`: 专业视频流监控界面
- **CSS框架**: Tailwind CSS + 自定义玻璃拟态主题
- **JavaScript架构**: ES6+基于类的模块化架构，现代API集成
- **组件库**: ECharts图表、AG-Grid表格、Lucide图标、AOS动画

**3. 性能与可靠性优化**
- `DataRead.py` 增加文件修改时间缓存机制
- 渐进式增强策略: WebSocket → SSE → Polling 降级方案
- 错误恢复能力：重试机制和优雅降级处理
- 现代浏览器API集成：Performance Observer、Intersection Observer
- Service Worker 离线支持和智能缓存
- GPU加速CSS动画和渲染优化

## 项目架构详解

### 核心应用模块 (`core/`)
**`core/factory.py`** - Flask应用工厂
- 实现Flask应用工厂模式，支持多环境配置
- 后台任务调度器：每30分钟执行DataStore数据存储操作
- 全局错误处理器和结构化日志配置
- 模块化路由注册系统

**`core/jobs.py`** - 后台任务管理
- 周期性任务调度，支持异步处理
- 任务状态监控和错误处理

**`core/streaming.py`** - 高性能视频流处理
- MJPEG流生成和优化
- 多并发连接支持

### 路由系统 (`routes/`)
**`routes/main.py`** - 页面渲染路由
- `/`: 现代化响应式首页
- `/dashboard`: 数据可视化仪表盘
- `/result`: 实时视频监控页面
- `/stream.mjpg`: MJPEG视频流端点
- PWA支持：Service Worker和Manifest路由

**`routes/api.py`** - RESTful API端点
- `/api/sensor-data`: 获取所有传感器数据
- `/api/sensors`: 分页查询传感器数据
- `/api/sensors/latest`: 获取最新数据记录
- `/healthz`: 应用健康检查端点
- 完善的错误处理和JSON响应格式

### 工具模块 (`utils/`)
**`DataRead.py`** - 高性能数据读取
- 增强内存缓存和文件修改时间跟踪
- CSV数据解析和类型转换优化
- 缓存机制减少磁盘I/O操作

**`DataStore.py`** - 智能数据存储管理
- 滚动窗口数据存储，30分钟间隔更新
- 自动时间戳生成和数据补齐机制
- 支持北京时区的时间处理

**`GetImage.py`** - 实时图像处理
- OpenCV图像处理和帧计数器
- 图像增强：数字叠加、半透明效果
- JPEG编码优化和二进制输出

**`GetSensorData.py`** - 传感器数据生成
- 智能随机数据生成器
- 支持昼夜节律的真实数据模拟
- 时区兼容性处理（ZoneInfo/timezone降级）

### 前端架构 (`static/`)
**JavaScript模块化系统**:
- `static/js/app.js`: 主应用管理模块 (361行)
- `static/js/api.js`: API管理模块 (91行)
- `static/js/charts.js`: 图表管理模块 (245行)
- `static/js/utils.js`: 工具函数模块 (67行)
- `static/js/performance-monitor.js`: 性能监控系统

**样式系统**:
- `static/css/styles.css`: 高性能CSS，GPU加速优化
- CSS Containment API性能隔离
- 现代CSS变量系统和玻璃拟态效果

**PWA支持**:
- `static/sw.js`: Service Worker离线缓存
- `static/manifest.json`: PWA应用清单
- 响应式设计，移动优先方法

## Technology Stack

### Backend
- **Flask**: Web framework with modular structure
- **Python 3.9+**: Modern Python features
- **APScheduler**: Background job scheduling
- **Logging**: Structured logging with rotation

### Frontend
- **Tailwind CSS**: Utility-first CSS framework
- **Apache ECharts**: Advanced data visualization with WebGL
- **AG-Grid**: Enterprise-grade data tables
- **Lucide Icons**: Modern icon system
- **AOS**: Animate On Scroll library

### Development Tools
- **Flask Debug Mode**: Auto-reload and detailed error pages
- **Browser DevTools**: Performance monitoring and debugging
- **Modern JavaScript**: ES6+ features, async/await, modules

## 开发命令

### 服务器启动
**推荐启动方式 (模块化架构)**:
```bash
# 开发环境启动（支持热重载和调试）
python -m flask --app core/factory.py run --debug --host=0.0.0.0 --port=5000

# 生产环境启动
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gthread --threads 2 'core.factory:create_app()'
```

**兼容性启动方式**:
```bash
python app.py  # 传统单文件入口
```

### 依赖管理
```bash
# 开发环境依赖安装
pip install -r requirements.txt

# 生产环境依赖安装
pip install -r requirements-production.txt

# 虚拟环境创建
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 模块测试
```bash
# 传感器数据读取测试（缓存功能）
python utils/DataRead.py

# 图像处理功能测试
python utils/GetImage.py

# 数据存储操作测试
python utils/DataStore.py

# 测试传感器数据生成
python utils/GetSensorData.py
```

### 前端开发
- **实时重载**: Debug模式下自动启用
- **调试工具**: 浏览器DevTools JavaScript调试
- **API测试**: Network选项卡监控API端点
- **错误监控**: Console错误日志跟踪
- **性能分析**: Performance Monitor集成
- **缓存管理**: Service Worker缓存状态监控

## Key Endpoints

### Page Routes
- `/` - Modern interactive homepage with live metrics
- `/dashboard` - Advanced data visualization dashboard with AG-Grid
- `/result` - Professional video streaming interface
- `/stream.mjpg` - MJPEG video stream for real-time image display

### API Routes (Enhanced)
- `/api/sensor-data` - REST API for all sensor data with error handling
- `/api/sensors?limit=N` - Get latest N sensor readings with pagination
- `/api/sensors/latest` - Get most recent sensor reading
- `/healthz` - Health check endpoint

## 数据格式规范

### 传感器数据结构 (增强版)
```python
{
    "timestamp_Beijing": "2025-08-24 23:30",  # 北京时区时间戳
    "sway_speed_dps": 30.87,                  # 晃动速度（度/秒）
    "temperature_C": 22.79,                   # 温度（摄氏度）
    "humidity_RH": 71.19,                     # 相对湿度（%）
    "pressure_hPa": 1014.81,                  # 气压（百帕）
    "lux": 8603.65                            # 光照强度（勒克斯）
}
```

### API响应格式标准
**单条记录响应**:
```json
{
    "timestamp_Beijing": "2025-08-24 23:30",
    "sway_speed_dps": 30.87,
    "temperature_C": 22.79,
    "humidity_RH": 71.19,
    "pressure_hPa": 1014.81,
    "lux": 8603.65
}
```

**多条记录响应**:
```json
{
    "rows": [                    // 传感器数据数组
        { /* sensor record 1 */ },
        { /* sensor record 2 */ }
    ],
    "count": 672,                // 总记录数
    "cache_hit": true,          // 缓存命中状态（可选）
    "response_time": "15ms"     // 响应时间（可选）
}
```

**错误响应格式**:
```json
{
    "error": "具体错误信息",     // 错误描述
    "code": "DATA_NOT_FOUND",   // 错误代码（可选）
    "timestamp": "2025-08-24 23:30:00"  // 错误时间戳（可选）
}
```

### 数据文件格式
**CSV数据文件** (`utils/data/data.txt`):
```csv
timestamp_Beijing,sway_speed_dps,temperature_C,humidity_RH,pressure_hPa,lux
2025-08-24 23:30,30.87,22.79,71.19,1014.81,8603.65
```

**图像计数文件** (`utils/data/TestImageNumber.txt`):
```
42  # 当前帧计数值（0-99循环）
```

## Configuration

**Timing Settings** (Enhanced in `AppConfig`):
- DataStore interval: 30 minutes (configurable via `datastore_interval_minutes`)
- Video stream frame rate: ~5 FPS (configurable via `stream_frame_interval_sec`)
- API cache timeout: Based on file modification time
- Frontend refresh: 5 minutes for data, 30 seconds for charts

**Frontend Configuration**:
- Chart refresh interval: 30 seconds
- Connection timeout: 10 seconds
- Retry attempts: 3
- Debounce delay: 300ms

**File Locations**:
- Sensor data: `utils/data/data.txt`
- Test images: `utils/data/test_image.jpg`
- Image counter: `utils/data/TestImageNumber.txt`
- Application logs: `app.log`
- Static assets: `static/css/`, `static/js/`, `static/images/`

## Error Handling & Logging

**Backend Error Handling**:
- Global 404/500 error handlers with JSON responses
- Try-catch blocks in all API endpoints
- File not found handling with graceful fallbacks
- Structured logging with timestamps and levels

**Frontend Error Handling**:
- API call retry mechanisms with exponential backoff
- Graceful degradation when services are unavailable
- User-friendly error notifications
- Console logging for debugging

**Logging Strategy**:
- Application logs: `app.log` with rotation (5MB, 3 backups)
- Console output in development mode
- Structured log messages with context
- Error tracking for monitoring

## Performance Optimizations

**Backend Performance**:
- File modification time caching in `DataRead.py`
- Background job scheduling to prevent blocking
- Efficient CSV reading with type conversion
- Memory-based caching for frequently accessed data

**Frontend Performance**:
- WebGL-accelerated charts for better rendering
- Lazy loading with Intersection Observer
- Debounced resize handlers
- Progressive enhancement (WebSocket → SSE → Polling)
- Resource cleanup and memory management

**Network Optimizations**:
- CDN usage for external libraries
- Efficient API endpoint design
- Proper HTTP status codes and error responses
- Connection pooling and timeout handling

## Security Considerations

**Backend Security**:
- Input validation and sanitization
- Proper error handling without information leakage
- File path validation to prevent directory traversal
- Resource limits and timeout configurations

**Frontend Security**:
- Content Security Policy ready
- XSS prevention through proper data handling
- Secure API communication patterns
- No sensitive data exposure in client-side code

## Browser Support

**Modern Browser Features**:
- ES6+ JavaScript (Chrome 61+, Firefox 55+, Safari 11+)
- CSS Grid and Flexbox layouts
- WebGL for chart acceleration
- Service Worker API (for future PWA features)
- Modern JavaScript APIs (fetch, Promise, async/await)

**Graceful Degradation**:
- Fallbacks for older browsers
- Progressive enhancement patterns
- Feature detection before usage
- Alternative layouts for unsupported features

## Troubleshooting

**Common Issues & Solutions**:

1. **Tailwind CSS not working**:
   - Ensure `<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp"></script>` is loaded
   - Check browser console for script loading errors

2. **Data not displaying**:
   - Verify `utils/data/data.txt` exists and has valid CSV data
   - Check API endpoints: `/api/sensor-data`, `/api/sensors/latest`
   - Monitor browser console for JavaScript errors

3. **Charts not rendering**:
   - Ensure ECharts library is loaded
   - Check for JavaScript errors in browser console
   - Verify chart container elements exist in DOM

4. **AG-Grid not working**:
   - Use `new agGrid.Grid()` constructor (not `agGrid.createGrid`)
   - Ensure AG-Grid CSS files are loaded
   - Check for proper column definitions

**Development Tips**:
- Use Flask debug mode for auto-reload: `--debug`
- Monitor browser console for frontend errors
- Use Network tab to debug API calls
- Check `app.log` for backend error details

## Future Enhancements

**Planned Improvements**:
- WebSocket real-time data streaming
- Progressive Web App (PWA) features
- Advanced data export formats (Excel, PDF)
- User authentication and role-based access
- Mobile-optimized interfaces
- Database integration for better data persistence

**Monitoring & Analytics**:
- Performance monitoring dashboard
- Error tracking and alerting
- Usage analytics and reporting
- System health monitoring

## 重要开发注意事项

### 开发环境管理
- 使用虚拟环境 (venv) 管理项目依赖
- 生产部署前在开发模式下充分测试
- 定期更新依赖包确保安全性
- 保持开发和生产环境的一致性

### 代码质量标准
- 遵循 Python PEP 8 代码规范
- 使用现代 JavaScript ES6+ 特性
- 实现完善的错误处理机制
- 编写结构化日志便于调试分析
- 验证数据格式和 API 响应的正确性

### 前端开发规范
- 监控浏览器控制台 JavaScript 错误
- 测试不同屏幕尺寸的响应式效果
- 优化 Core Web Vitals 性能指标
- 确保跨浏览器兼容性

---

## 项目协作指南

### Claude Code 使用规范
- **精确执行**: 严格按照用户需求执行，不多不少
- **文件管理**: 除非绝对必要，避免创建新文件
- **编辑优先**: 优先编辑现有文件而非创建新文件
- **文档策略**: 仅在用户明确要求时创建文档文件

**项目维护者**: Linescope Team  
**最后更新**: 2025-08-29  
**文档版本**: v2.2.0