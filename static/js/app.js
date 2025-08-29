/**
 * 高性能主应用管理模块
 * 协调各个功能模块，管理应用状态
 * 版本: 2.0.0 - 性能优化版
 */

// 性能优化的模块加载器
class ModuleLoader {
  constructor() {
    this.loadedModules = new Map();
    this.loadPromises = new Map();
    this.performance = window.performance || {};
  }

  /**
   * 动态导入模块，支持缓存和错误处理
   */
  async importModule(path, name) {
    const startTime = this.performance.now?.() || Date.now();
    
    if (this.loadedModules.has(path)) {
      console.log(`📦 Module cached: ${name}`);
      return this.loadedModules.get(path);
    }

    if (this.loadPromises.has(path)) {
      console.log(`⏳ Module loading: ${name}`);
      return this.loadPromises.get(path);
    }

    const loadPromise = import(path)
      .then(module => {
        const loadTime = (this.performance.now?.() || Date.now()) - startTime;
        console.log(`✅ Module loaded: ${name} (${loadTime.toFixed(2)}ms)`);
        this.loadedModules.set(path, module);
        this.loadPromises.delete(path);
        return module;
      })
      .catch(error => {
        console.error(`❌ Module failed: ${name}`, error);
        this.loadPromises.delete(path);
        throw error;
      });

    this.loadPromises.set(path, loadPromise);
    return loadPromise;
  }

  /**
   * 预加载模块（非阻塞）
   */
  async preloadModule(path, name) {
    if (this.loadedModules.has(path) || this.loadPromises.has(path)) {
      return;
    }

    console.log(`🔄 Preloading: ${name}`);
    try {
      await this.importModule(path, name);
    } catch (error) {
      console.warn(`⚠️ Preload failed: ${name}`, error);
    }
  }
}

// 全局模块加载器实例
const moduleLoader = new ModuleLoader();

// 核心模块静态导入（关键路径）
import { ApiManager } from './api.js';
import { Utils } from './utils.js';

// 全局辅助函数 (用于AG-Grid等需要全局访问的地方)
function formatNumber(num, precision = 2) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  return Number(num).toFixed(precision);
}

function calculateTrend(current, previous) {
  if (!previous || previous === 0) return { percentage: 0, direction: 'stable' };
  const change = ((current - previous) / previous) * 100;
  const direction = Math.abs(change) < 1 ? 'stable' : change > 0 ? 'up' : 'down';
  return { percentage: Math.abs(change), direction };
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 性能监控集成
const performanceMonitor = window.performanceMonitor;

// 延迟导入 ChartManager（非关键路径）
let ChartManager = null;
const loadChartManager = () => {
  if (!ChartManager) {
    return moduleLoader.importModule('./charts.js', 'ChartManager')
      .then(module => {
        ChartManager = module.ChartManager;
        return ChartManager;
      });
  }
  return Promise.resolve(ChartManager);
};

export class LineScopeApp {
  constructor() {
    this.api = new ApiManager();
    this.chartManager = null; // 延迟加载
    
    this.state = {
      currentPage: this.detectCurrentPage(),
      sensorData: [],
      isLoading: false,
      lastUpdate: null
    };

    this.config = {
      updateInterval: 30000, // 30秒
      chartUpdateInterval: 300000 // 5分钟
    };

    this.intervals = [];
    this.init();
  }

  /**
   * 格式化数字 (本地方法，避免Utils依赖问题)
   */
  formatNumber(num, precision = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toFixed(precision);
  }

  /**
   * 检测当前页面类型
   */
  detectCurrentPage() {
    if (document.getElementById('preview-chart')) return 'home';
    if (document.getElementById('environmental-chart')) return 'dashboard';
    if (document.querySelector('.video-container')) return 'video';
    return 'unknown';
  }

  /**
   * 获取 ChartManager 实例（延迟加载）
   */
  async getChartManager() {
    if (!this.chartManager) {
      const ChartManagerClass = await loadChartManager();
      this.chartManager = new ChartManagerClass();
    }
    return this.chartManager;
  }

  /**
   * 初始化应用
   */
  async init() {
    performanceMonitor?.mark('app-init-start');
    console.log(`LineScopeApp 初始化开始 - 页面类型: ${this.state.currentPage}`);
    
    try {
      // 初始化页面特定功能
      performanceMonitor?.mark('page-specific-init-start');
      await this.initPageSpecific();
      performanceMonitor?.mark('page-specific-init-end');
      performanceMonitor?.measure('page-specific-init', 'page-specific-init-start', 'page-specific-init-end');
      
      // 设置事件监听器
      this.setupEventListeners();
      
      // 启动定期更新
      this.startPeriodicUpdates();
      
      performanceMonitor?.mark('app-init-end');
      performanceMonitor?.measure('app-init-total', 'app-init-start', 'app-init-end');
      
      console.log('LineScopeApp 初始化完成');
    } catch (error) {
      console.error('LineScopeApp 初始化失败:', error);
    }
  }

  /**
   * 初始化页面特定功能
   */
  async initPageSpecific() {
    switch (this.state.currentPage) {
      case 'home':
        await this.initHomePage();
        break;
      case 'dashboard':
        await this.initDashboardPage();
        break;
      case 'video':
        await this.initVideoPage();
        break;
      default:
        console.warn('未知页面类型，跳过特定初始化');
    }
  }

  /**
   * 初始化首页
   */
  async initHomePage() {
    console.log('初始化首页...');
    
    // 加载最新数据
    await this.loadLatestData();
    
    // 加载图表数据
    await this.loadChartData();
  }

  /**
   * 初始化仪表盘页面
   */
  async initDashboardPage() {
    console.log('初始化仪表盘页面...');
    
    // 尝试使用服务端数据
    if (typeof window.initialData !== 'undefined' && window.initialData) {
      console.log('发现服务端数据:', window.initialData);
      if (Array.isArray(window.initialData) && window.initialData.length > 0) {
        this.state.sensorData = window.initialData;
        console.log(`使用服务端数据: ${this.state.sensorData.length} 条记录`);
        console.log('数据示例:', this.state.sensorData[0]);
      } else {
        console.warn('服务端数据格式不正确或为空');
      }
    } else {
      console.log('未找到服务端数据，将从API加载');
    }
    
    // 如果没有数据，从API加载
    if (this.state.sensorData.length === 0) {
      console.log('开始从API加载数据...');
      await this.loadSensorData();
    }
    
    // 更新UI
    if (this.state.sensorData.length > 0) {
      console.log('开始更新仪表盘UI...');
      this.updateKPIs();
      await this.updateDashboardCharts();
      this.updateDataGrid();
      console.log('仪表盘初始化完成');
    } else {
      console.error('没有可用的数据，仪表盘无法初始化');
      // 显示无数据提示
      const gridDiv = document.querySelector('#data-grid');
      if (gridDiv) {
        gridDiv.innerHTML = `
          <div class="flex flex-col items-center justify-center h-full text-yellow-400">
            <div class="text-lg font-semibold mb-2">📊 暂无数据</div>
            <div class="text-sm text-gray-400">请检查数据源或稍后重试</div>
          </div>`;
      }
    }
  }

  /**
   * 初始化视频页面
   */
  async initVideoPage() {
    console.log('初始化视频页面...');
    // 视频页面特定初始化逻辑
  }

  /**
   * 加载传感器数据
   */
  async loadSensorData() {
    if (this.state.isLoading) return;
    
    this.state.isLoading = true;
    try {
      this.state.sensorData = await this.api.getSensorData();
      this.state.lastUpdate = new Date();
      console.log(`数据加载完成: ${this.state.sensorData.length} 条记录`);
    } catch (error) {
      console.error('加载传感器数据失败:', error);
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * 加载最新数据（首页用）
   */
  async loadLatestData() {
    try {
      const latestData = await this.api.getLatestSensorData();
      if (latestData) {
        this.updateHomeMetrics(latestData);
      }
    } catch (error) {
      console.error('加载最新数据失败:', error);
    }
  }

  /**
   * 加载图表数据（首页用 - 优化版）
   */
  async loadChartData() {
    performanceMonitor?.mark('chart-load-start');
    
    try {
      // 只在需要时加载图表数据和管理器
      const chartElement = document.getElementById('preview-chart');
      if (!chartElement) {
        console.log('跳过图表加载：图表容器不存在');
        return;
      }

      console.log('开始加载图表数据...');
      
      performanceMonitor?.mark('chart-data-fetch-start');
      const [chartData, chartManager] = await Promise.all([
        this.api.getSensorDataWithLimit(48), // 24小时数据
        this.getChartManager()
      ]);
      performanceMonitor?.mark('chart-data-fetch-end');
      performanceMonitor?.measure('chart-data-fetch', 'chart-data-fetch-start', 'chart-data-fetch-end');

      if (chartData.length > 0) {
        performanceMonitor?.mark('chart-render-start');
        await chartManager.createPreviewChart('preview-chart', chartData);
        performanceMonitor?.mark('chart-render-end');
        performanceMonitor?.measure('chart-render', 'chart-render-start', 'chart-render-end');
        
        console.log('图表数据加载完成');
      } else {
        console.warn('没有可用的图表数据');
      }
    } catch (error) {
      console.error('加载图表数据失败:', error);
      // 提供回退UI
      const chartElement = document.getElementById('preview-chart');
      if (chartElement) {
        chartElement.innerHTML = '<div class="flex items-center justify-center h-full text-white/60">图表加载失败</div>';
      }
    } finally {
      performanceMonitor?.mark('chart-load-end');
      performanceMonitor?.measure('chart-load-total', 'chart-load-start', 'chart-load-end');
    }
  }

  /**
   * 更新首页指标
   */
  updateHomeMetrics(data) {
    if (!data) return;

    // 更新数值显示
    const metrics = [
      { id: 'temp-value', value: data.temperature_C, unit: '°C', max: 50 },
      { id: 'humidity-value', value: data.humidity_RH, unit: '%', max: 100 },
      { id: 'pressure-value', value: data.pressure_hPa, unit: ' hPa', max: 1050, min: 950 },
      { id: 'lux-value', value: data.lux, unit: ' Lux', max: 10000 },
      { id: 'sway-value', value: data.sway_speed_dps, unit: ' °/s', max: 200 }
    ];

    metrics.forEach(metric => {
      const element = document.getElementById(metric.id);
      if (element) {
        element.textContent = formatNumber(metric.value) + metric.unit;
      }

      // 更新进度条
      const progressId = metric.id.replace('-value', '-progress');
      const progressElement = document.getElementById(progressId);
      if (progressElement && metric.value !== null) {
        const min = metric.min || 0;
        const max = metric.max;
        const percentage = Math.min(100, Math.max(0, ((metric.value - min) / (max - min)) * 100));
        progressElement.style.width = percentage + '%';
      }
    });

    // 更新时间戳
    const timestampElement = document.getElementById('timestamp-value');
    if (timestampElement) {
      timestampElement.textContent = data.timestamp_Beijing || '--:--';
    }

    const statusElement = document.getElementById('status-text');
    if (statusElement) {
      statusElement.textContent = '数据正常更新';
    }
  }

  /**
   * 更新仪表盘图表（优化版 - 延迟加载）
   */
  async updateDashboardCharts() {
    if (this.state.sensorData.length === 0) return;

    try {
      console.log('开始更新仪表盘图表...');
      const chartManager = await this.getChartManager();
      
      await Promise.all([
        chartManager.createEnvironmentalChart('environmental-chart', this.state.sensorData),
        chartManager.createSwayChart('sway-chart', this.state.sensorData),
        this.updateMiniCharts()
      ]);
      
      console.log('仪表盘图表更新完成');
    } catch (error) {
      console.error('更新仪表盘图表失败:', error);
      // 提供错误回退
      const errorMessage = '图表加载失败，请刷新页面重试';
      ['environmental-chart', 'sway-chart'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
          element.innerHTML = `<div class="flex items-center justify-center h-full text-white/60">${errorMessage}</div>`;
        }
      });
    }
  }

  /**
   * 更新小图表
   */
  async updateMiniCharts() {
    const metrics = [
      { key: 'temperature_C', id: 'temp-mini-chart', color: '#60a5fa' },
      { key: 'humidity_RH', id: 'humidity-mini-chart', color: '#34d399' },
      { key: 'pressure_hPa', id: 'pressure-mini-chart', color: '#a78bfa' },
      { key: 'lux', id: 'lux-mini-chart', color: '#fbbf24' },
      { key: 'sway_speed_dps', id: 'sway-mini-chart', color: '#f87171' }
    ];

    const recentData = this.state.sensorData.slice(-20);
    
    for (const metric of metrics) {
      const container = document.getElementById(metric.id);
      if (!container) continue;

      try {
        const chartManager = await this.getChartManager();
        const chart = await chartManager.createChart(metric.id);
        if (chart) {
          const values = recentData.map(d => d[metric.key]);
          const times = recentData.map(d => d.timestamp_Beijing);

          chart.setOption({
            backgroundColor: 'transparent',
            grid: { left: 0, right: 0, top: 0, bottom: 0 },
            xAxis: { type: 'category', data: times, show: false },
            yAxis: { type: 'value', show: false },
            series: [{
              type: 'line',
              data: values,
              smooth: true,
              symbol: 'none',
              lineStyle: { color: metric.color, width: 2 },
              areaStyle: { color: metric.color, opacity: 0.1 }
            }]
          });
        }
      } catch (error) {
        console.warn(`更新小图表失败 ${metric.id}:`, error);
      }
    }
  }

  /**
   * 更新KPI指标
   */
  updateKPIs() {
    if (this.state.sensorData.length === 0) return;

    const latest = this.state.sensorData[this.state.sensorData.length - 1];
    const previous = this.state.sensorData.length > 1 ? this.state.sensorData[this.state.sensorData.length - 2] : null;

    const metrics = [
      { key: 'temperature_C', id: 'temp', unit: '°C' },
      { key: 'humidity_RH', id: 'humidity', unit: '%' },
      { key: 'pressure_hPa', id: 'pressure', unit: ' hPa' },
      { key: 'lux', id: 'lux', unit: ' Lux' },
      { key: 'sway_speed_dps', id: 'sway', unit: ' °/s' }
    ];

    metrics.forEach(metric => {
      const current = latest[metric.key];
      const prev = previous ? previous[metric.key] : null;

      // 更新当前值
      const currentElement = document.getElementById(`${metric.id}-current`);
      if (currentElement) {
        currentElement.textContent = formatNumber(current) + metric.unit;
      }

      // 更新趋势
      const trend = calculateTrend(current, prev);
      this.updateTrendIndicator(`${metric.id}-trend`, trend);

      // 计算范围
      const values = this.state.sensorData.map(d => d[metric.key]).filter(v => v !== null && !isNaN(v));
      if (values.length > 0) {
        const min = Math.min(...values);
        const max = Math.max(...values);
        const rangeElement = document.getElementById(`${metric.id}-range`);
        if (rangeElement) {
          rangeElement.textContent = `${formatNumber(min)} ~ ${formatNumber(max)}${metric.unit}`;
        }
      }
    });

    // 特殊处理晃动速度警告
    const swayCard = document.getElementById('sway-card');
    if (swayCard) {
      if (latest.sway_speed_dps > 60) {
        swayCard.classList.add('alert-high');
      } else {
        swayCard.classList.remove('alert-high');
      }
    }

    // 更新系统状态
    const totalRecordsElement = document.getElementById('total-records');
    if (totalRecordsElement) {
      totalRecordsElement.textContent = this.state.sensorData.length;
    }

    // 更新异物检测状态
    this.updateForeignObjectStatus();
  }

  /**
   * 更新异物检测状态
   */
  updateForeignObjectStatus() {
    if (this.state.sensorData.length === 0) return;

    const data = this.state.sensorData;
    const foreignObjectValues = data.map(d => d.wire_foreign_object || 0);
    const totalDetections = foreignObjectValues.reduce((sum, val) => sum + val, 0);
    const detectionRate = data.length > 0 ? (totalDetections / data.length * 100) : 0;
    const latestDetection = data[data.length - 1].wire_foreign_object || 0;

    // 更新检测率
    const detectionRateElement = document.getElementById('detection-rate');
    if (detectionRateElement) {
      detectionRateElement.textContent = `${detectionRate.toFixed(1)}%`;
    }

    // 更新异物检测状态
    const statusElement = document.getElementById('foreign-object-status');
    if (statusElement) {
      if (latestDetection === 1) {
        statusElement.textContent = '检测到异物';
        statusElement.className = 'metric-big text-red-400';
      } else {
        statusElement.textContent = '状态正常';
        statusElement.className = 'metric-big text-green-400';
      }
    }

    // 更新检测率显示
    const rateElement = document.getElementById('foreign-object-rate');
    if (rateElement) {
      rateElement.textContent = `${detectionRate.toFixed(1)}%`;
    }

    // 更新总检测次数
    const totalDetectionsElement = document.getElementById('total-detections');
    if (totalDetectionsElement) {
      totalDetectionsElement.textContent = data.length;
    }

    // 更新异物发现次数
    const foreignObjectCountElement = document.getElementById('foreign-object-count');
    if (foreignObjectCountElement) {
      foreignObjectCountElement.textContent = totalDetections;
    }

    // 更新最新状态指示器
    const indicatorElement = document.getElementById('foreign-object-indicator');
    const latestElement = document.getElementById('foreign-object-latest');
    if (indicatorElement && latestElement) {
      if (latestDetection === 1) {
        indicatorElement.className = 'w-2 h-2 rounded-full bg-red-500 status-indicator';
        latestElement.textContent = '发现异物';
        latestElement.className = 'font-semibold text-red-400';
      } else {
        indicatorElement.className = 'w-2 h-2 rounded-full bg-green-500';
        latestElement.textContent = '正常';
        latestElement.className = 'font-semibold text-green-400';
      }
    }

    // 更新趋势指示器
    const trendElement = document.getElementById('foreign-object-trend');
    if (trendElement) {
      if (detectionRate > 10) {
        trendElement.className = 'trend-indicator trend-up';
      } else if (detectionRate > 5) {
        trendElement.className = 'trend-indicator trend-stable';
      } else {
        trendElement.className = 'trend-indicator trend-down';
      }
    }

    // 更新卡片警告状态
    const foreignObjectCard = document.getElementById('foreign-object-card');
    if (foreignObjectCard) {
      if (latestDetection === 1) {
        foreignObjectCard.classList.add('alert-high');
      } else {
        foreignObjectCard.classList.remove('alert-high');
      }
    }
  }

  /**
   * 更新趋势指示器
   */
  updateTrendIndicator(elementId, trend) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const icons = {
      up: 'trending-up',
      down: 'trending-down',
      stable: 'minus'
    };

    element.className = `trend-indicator trend-${trend.direction}`;
    element.innerHTML = `
      <i data-lucide="${icons[trend.direction]}" class="w-3 h-3"></i>
      <span>${trend.percentage.toFixed(1)}%</span>
    `;

    // 重新初始化图标
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }

  /**
   * 更新数据表格
   */
  updateDataGrid() {
    if (typeof agGrid === 'undefined') {
      console.warn('AG-Grid 未加载，跳过表格更新');
      const gridDiv = document.querySelector('#data-grid');
      if (gridDiv) {
        gridDiv.innerHTML = '<div class="flex items-center justify-center h-full text-white/60">AG-Grid 库未加载</div>';
      }
      return;
    }

    const gridDiv = document.querySelector('#data-grid');
    if (!gridDiv) {
      console.error('数据表格容器未找到');
      return;
    }

    // 检查数据
    if (!this.state.sensorData || this.state.sensorData.length === 0) {
      gridDiv.innerHTML = '<div class="flex items-center justify-center h-full text-white/60">暂无数据</div>';
      return;
    }

    console.log(`正在创建数据表格，数据条数: ${this.state.sensorData.length}`);

    const columnDefs = [
      { 
        field: 'timestamp_Beijing', 
        headerName: '时间戳', 
        width: 180,
        pinned: 'left',
        cellStyle: { color: '#e2e8f0', fontFamily: 'monospace' }
      },
      { 
        field: 'sway_speed_dps', 
        headerName: '晃动速度 (°/s)', 
        width: 140,
        type: 'numericColumn',
        cellStyle: (params) => {
          const isAlert = params.value > 60;
          return {
            color: isAlert ? '#f87171' : '#e2e8f0',
            fontWeight: isAlert ? 'bold' : 'normal'
          };
        },
        valueFormatter: (params) => formatNumber(params.value)
      },
      { 
        field: 'temperature_C', 
        headerName: '温度 (°C)', 
        width: 120,
        type: 'numericColumn',
        cellStyle: { color: '#60a5fa' },
        valueFormatter: (params) => formatNumber(params.value)
      },
      { 
        field: 'humidity_RH', 
        headerName: '湿度 (%)', 
        width: 120,
        type: 'numericColumn',
        cellStyle: { color: '#34d399' },
        valueFormatter: (params) => formatNumber(params.value)
      },
      { 
        field: 'pressure_hPa', 
        headerName: '气压 (hPa)', 
        width: 130,
        type: 'numericColumn',
        cellStyle: { color: '#a78bfa' },
        valueFormatter: (params) => formatNumber(params.value)
      },
      { 
        field: 'lux', 
        headerName: '光照 (Lux)', 
        width: 120,
        type: 'numericColumn',
        cellStyle: { color: '#fbbf24' },
        valueFormatter: (params) => formatNumber(params.value, 0)
      },
      { 
        field: 'wire_foreign_object', 
        headerName: '异物检测', 
        width: 100,
        type: 'numericColumn',
        cellStyle: (params) => ({
          color: params.value === 1 ? '#f87171' : '#34d399',
          fontWeight: params.value === 1 ? 'bold' : 'normal'
        }),
        valueFormatter: (params) => params.value === 1 ? '有异物' : '正常'
      }
    ];

    const gridOptions = {
      columnDefs: columnDefs,
      rowData: this.state.sensorData.slice().reverse(), // 最新数据在前
      defaultColDef: {
        sortable: true,
        filter: true,
        resizable: true,
        cellStyle: { color: '#e2e8f0' }
      },
      pagination: true,
      paginationPageSize: 20,
      paginationPageSizeSelector: [10, 20, 50, 100],
      animateRows: true,
      rowHeight: 40,
      headerHeight: 45,
      getRowStyle: (params) => {
        // 优先级：异物检测 > 晃动速度
        if (params.data.wire_foreign_object === 1) {
          return { 
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            borderLeft: '4px solid #f87171'
          };
        } else if (params.data.sway_speed_dps > 60) {
          return { 
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderLeft: '3px solid #fbbf24'
          };
        }
        return null;
      },
      onGridReady: (params) => {
        console.log('AG-Grid 就绪，自动调整列宽');
        params.api.sizeColumnsToFit();
      },
      onFirstDataRendered: (params) => {
        console.log('AG-Grid 首次数据渲染完成');
      }
    };

    try {
      // 销毁之前的Grid实例（如果存在）
      if (this.gridApi && typeof this.gridApi.destroy === 'function') {
        this.gridApi.destroy();
      }
      
      // 清空容器
      gridDiv.innerHTML = '';
      
      // 创建新的Grid实例 (使用新版本AG-Grid API)
      this.gridApi = new agGrid.Grid(gridDiv, gridOptions);
      
      // 更新总行数显示
      const totalRowsElement = document.getElementById('total-rows');
      if (totalRowsElement) {
        totalRowsElement.textContent = this.state.sensorData.length;
      }
      
      console.log('数据表格创建成功');
    } catch (error) {
      console.error('更新数据表格失败:', error);
      gridDiv.innerHTML = `<div class="flex items-center justify-center h-full text-red-400">
        表格加载失败: ${error.message}
      </div>`;
    }
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    // 窗口大小调整
    window.addEventListener('resize', debounce(async () => {
      if (this.chartManager) {
        this.chartManager.resizeAllCharts();
      }
    }, 300));

    // 刷新按钮
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.handleRefresh());
    }

    // 导出按钮
    const exportBtn = document.getElementById('export-csv');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportToCSV());
    }

    // 页面可见性变化
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pauseUpdates();
      } else {
        this.resumeUpdates();
      }
    });
  }

  /**
   * 处理刷新操作
   */
  async handleRefresh() {
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
      refreshBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>加载中...</span>';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    try {
      await this.loadSensorData();
      
      if (this.state.currentPage === 'dashboard') {
        this.updateKPIs();
        await this.updateDashboardCharts();
        this.updateDataGrid();
      } else if (this.state.currentPage === 'home') {
        await this.loadLatestData();
        await this.loadChartData();
      }

      // 更新最后更新时间
      const lastUpdateElement = document.getElementById('last-update');
      if (lastUpdateElement) {
        lastUpdateElement.textContent = new Date().toLocaleTimeString();
      }
    } finally {
      if (refreshBtn) {
        refreshBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i><span>刷新数据</span>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    }
  }

  /**
   * 导出CSV
   */
  exportToCSV() {
    if (this.state.sensorData.length === 0) {
      alert('没有数据可导出');
      return;
    }

    const headers = ['时间戳', '晃动速度(°/s)', '温度(°C)', '湿度(%)', '气压(hPa)', '光照(Lux)', '异物检测'];
    const csvContent = [
      headers.join(','),
      ...this.state.sensorData.map(row => [
        row.timestamp_Beijing,
        formatNumber(row.sway_speed_dps),
        formatNumber(row.temperature_C),
        formatNumber(row.humidity_RH),
        formatNumber(row.pressure_hPa),
        formatNumber(row.lux, 0),
        (row.wire_foreign_object === 1 ? '有异物' : '正常')
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `sensor-data-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * 启动定期更新
   */
  startPeriodicUpdates() {
    // 清除现有的定时器
    this.intervals.forEach(interval => clearInterval(interval));
    this.intervals = [];

    // 根据页面类型设置不同的更新策略
    if (this.state.currentPage === 'home') {
      // 首页：每30秒更新最新数据，每5分钟更新图表
      this.intervals.push(
        setInterval(() => this.loadLatestData(), this.config.updateInterval),
        setInterval(() => this.loadChartData(), this.config.chartUpdateInterval)
      );
    } else if (this.state.currentPage === 'dashboard') {
      // 仪表盘：每5分钟全量更新
      this.intervals.push(
        setInterval(() => this.handleRefresh(), this.config.chartUpdateInterval)
      );
    }
  }

  /**
   * 暂停更新
   */
  pauseUpdates() {
    this.intervals.forEach(interval => clearInterval(interval));
    this.intervals = [];
    console.log('⏸️ 更新已暂停');
  }

  /**
   * 恢复更新
   */
  resumeUpdates() {
    this.startPeriodicUpdates();
    console.log('▶️ 更新已恢复');
  }

  /**
   * 清理资源（优化版）
   */
  cleanup() {
    this.pauseUpdates();
    if (this.chartManager) {
      this.chartManager.disposeAllCharts();
    }
    if (this.gridApi && typeof this.gridApi.destroy === 'function') {
      this.gridApi.destroy();
      this.gridApi = null;
    }
    console.log('应用资源已清理');
  }
}

// 高性能全局初始化系统
class AppBootstrap {
  static async init() {
    const startTime = performance.now?.() || Date.now();
    performanceMonitor?.mark('app-bootstrap-start');
    console.log('应用启动开始...');

    try {
      // 性能优化：预加载非关键模块
      performanceMonitor?.mark('module-preload-start');
      const preloadPromise = moduleLoader.preloadModule('./charts.js', 'ChartManager');
      
      // 等待DOM和外部库就绪
      performanceMonitor?.mark('dependencies-wait-start');
      await AppBootstrap.waitForDependencies();
      performanceMonitor?.mark('dependencies-wait-end');
      performanceMonitor?.measure('dependencies-wait', 'dependencies-wait-start', 'dependencies-wait-end');
      
      // 初始化应用
      performanceMonitor?.mark('app-instance-start');
      window.lineScopeApp = new LineScopeApp();
      performanceMonitor?.mark('app-instance-end');
      performanceMonitor?.measure('app-instance-creation', 'app-instance-start', 'app-instance-end');
      
      // 非阻塞预加载完成
      await preloadPromise;
      performanceMonitor?.mark('module-preload-end');
      performanceMonitor?.measure('module-preload', 'module-preload-start', 'module-preload-end');
      
      const loadTime = (performance.now?.() || Date.now()) - startTime;
      performanceMonitor?.mark('app-bootstrap-end');
      performanceMonitor?.measure('app-bootstrap-total', 'app-bootstrap-start', 'app-bootstrap-end');
      
      console.log(`应用启动完成 (${loadTime.toFixed(2)}ms)`);
      
      // 性能监控
      AppBootstrap.reportPerformanceMetrics();
      
    } catch (error) {
      console.error('应用启动失败:', error);
    }
  }

  static async waitForDependencies() {
    const maxWait = 5000; // 最多等待5秒
    const startTime = Date.now();
    
    // 等待关键外部库加载（非阻塞）
    const checkLibraries = () => {
      return new Promise(resolve => {
        const interval = setInterval(() => {
          const elapsed = Date.now() - startTime;
          
          // 超时或库已加载则继续
          if (elapsed > maxWait || 
              (typeof window.echarts !== 'undefined' || window.echartsLoadError)) {
            clearInterval(interval);
            resolve();
          }
        }, 50);
      });
    };
    
    await checkLibraries();
  }

  static reportPerformanceMetrics() {
    if (!window.performance) return;
    
    requestIdleCallback(() => {
      const metrics = {
        DOMContentLoaded: performance.timing?.domContentLoadedEventEnd - performance.timing?.navigationStart,
        FirstPaint: performance.getEntriesByType?.('paint')?.[0]?.startTime,
        FirstContentfulPaint: performance.getEntriesByType?.('paint')?.[1]?.startTime
      };
      
      console.log('性能指标:', metrics);
    });
  }
}

// 基于性能的初始化策略
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', AppBootstrap.init);
} else {
  // DOM已加载，立即初始化
  AppBootstrap.init();
}

// 智能清理系统
window.addEventListener('beforeunload', () => {
  if (window.lineScopeApp) {
    window.lineScopeApp.cleanup();
  }
});

// 页面可见性变化优化
document.addEventListener('visibilitychange', () => {
  if (!window.lineScopeApp) return;
  
  if (document.hidden) {
    console.log('页面隐藏，暂停更新');
    window.lineScopeApp.pauseUpdates();
  } else {
    console.log('页面显示，恢复更新');
    window.lineScopeApp.resumeUpdates();
  }
});