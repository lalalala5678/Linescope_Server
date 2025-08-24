/**
 * 主应用管理模块
 * 协调各个功能模块，管理应用状态
 */

import { ApiManager } from './api.js';
import { ChartManager } from './charts.js';
import { Utils } from './utils.js';

export class LineScopeApp {
  constructor() {
    this.api = new ApiManager();
    this.chartManager = new ChartManager();
    
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
   * 检测当前页面类型
   */
  detectCurrentPage() {
    if (document.getElementById('preview-chart')) return 'home';
    if (document.getElementById('environmental-chart')) return 'dashboard';
    if (document.querySelector('.video-container')) return 'video';
    return 'unknown';
  }

  /**
   * 初始化应用
   */
  async init() {
    console.log(`🚀 LineScopeApp 初始化开始 - 页面类型: ${this.state.currentPage}`);
    
    try {
      // 初始化页面特定功能
      await this.initPageSpecific();
      
      // 设置事件监听器
      this.setupEventListeners();
      
      // 启动定期更新
      this.startPeriodicUpdates();
      
      console.log('✅ LineScopeApp 初始化完成');
    } catch (error) {
      console.error('❌ LineScopeApp 初始化失败:', error);
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
      this.state.sensorData = window.initialData;
      console.log(`使用服务端数据: ${this.state.sensorData.length} 条记录`);
    }
    
    // 如果没有数据，从API加载
    if (this.state.sensorData.length === 0) {
      await this.loadSensorData();
    }
    
    // 更新UI
    if (this.state.sensorData.length > 0) {
      this.updateKPIs();
      await this.updateDashboardCharts();
      this.updateDataGrid();
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
   * 加载图表数据（首页用）
   */
  async loadChartData() {
    try {
      const chartData = await this.api.getSensorDataWithLimit(48); // 24小时数据
      if (chartData.length > 0) {
        await this.chartManager.createPreviewChart('preview-chart', chartData);
      }
    } catch (error) {
      console.error('加载图表数据失败:', error);
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
        element.textContent = Utils.formatNumber(metric.value) + metric.unit;
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
   * 更新仪表盘图表
   */
  async updateDashboardCharts() {
    if (this.state.sensorData.length === 0) return;

    try {
      await Promise.all([
        this.chartManager.createEnvironmentalChart('environmental-chart', this.state.sensorData),
        this.chartManager.createSwayChart('sway-chart', this.state.sensorData),
        this.updateMiniCharts()
      ]);
    } catch (error) {
      console.error('更新仪表盘图表失败:', error);
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
        const chart = await this.chartManager.createChart(metric.id);
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
        currentElement.textContent = Utils.formatNumber(current) + metric.unit;
      }

      // 更新趋势
      const trend = Utils.calculateTrend(current, prev);
      this.updateTrendIndicator(`${metric.id}-trend`, trend);

      // 计算范围
      const values = this.state.sensorData.map(d => d[metric.key]).filter(v => v !== null && !isNaN(v));
      if (values.length > 0) {
        const min = Math.min(...values);
        const max = Math.max(...values);
        const rangeElement = document.getElementById(`${metric.id}-range`);
        if (rangeElement) {
          rangeElement.textContent = `${Utils.formatNumber(min)} ~ ${Utils.formatNumber(max)}${metric.unit}`;
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
      return;
    }

    const gridDiv = document.querySelector('#data-grid');
    if (!gridDiv) return;

    const columnDefs = [
      { 
        field: 'timestamp_Beijing', 
        headerName: '时间戳', 
        width: 180,
        pinned: 'left',
        cellRenderer: (params) => `<code>${params.value}</code>`
      },
      { 
        field: 'sway_speed_dps', 
        headerName: '晃动速度 (°/s)', 
        width: 140,
        type: 'numericColumn',
        cellRenderer: (params) => {
          const isAlert = params.value > 60;
          const className = isAlert ? 'text-red-400 font-bold' : 'text-white';
          return `<span class="${className}">${Utils.formatNumber(params.value)}</span>`;
        }
      },
      { 
        field: 'temperature_C', 
        headerName: '温度 (°C)', 
        width: 120,
        type: 'numericColumn',
        cellRenderer: (params) => Utils.formatNumber(params.value)
      },
      { 
        field: 'humidity_RH', 
        headerName: '湿度 (%)', 
        width: 120,
        type: 'numericColumn',
        cellRenderer: (params) => Utils.formatNumber(params.value)
      },
      { 
        field: 'pressure_hPa', 
        headerName: '气压 (hPa)', 
        width: 130,
        type: 'numericColumn',
        cellRenderer: (params) => Utils.formatNumber(params.value)
      },
      { 
        field: 'lux', 
        headerName: '光照 (Lux)', 
        width: 120,
        type: 'numericColumn',
        cellRenderer: (params) => Utils.formatNumber(params.value, 0)
      }
    ];

    const gridOptions = {
      columnDefs: columnDefs,
      rowData: this.state.sensorData.slice().reverse(),
      defaultColDef: {
        sortable: true,
        filter: true,
        resizable: true
      },
      pagination: true,
      paginationPageSize: 20,
      animateRows: true,
      getRowStyle: (params) => {
        if (params.data.sway_speed_dps > 60) {
          return { backgroundColor: 'rgba(239, 68, 68, 0.1)' };
        }
        return null;
      }
    };

    try {
      new agGrid.Grid(gridDiv, gridOptions);
      
      const totalRowsElement = document.getElementById('total-rows');
      if (totalRowsElement) {
        totalRowsElement.textContent = this.state.sensorData.length;
      }
    } catch (error) {
      console.error('更新数据表格失败:', error);
    }
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    // 窗口大小调整
    window.addEventListener('resize', Utils.debounce(() => {
      this.chartManager.resizeAllCharts();
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

    const headers = ['时间戳', '晃动速度(°/s)', '温度(°C)', '湿度(%)', '气压(hPa)', '光照(Lux)'];
    const csvContent = [
      headers.join(','),
      ...this.state.sensorData.map(row => [
        row.timestamp_Beijing,
        Utils.formatNumber(row.sway_speed_dps),
        Utils.formatNumber(row.temperature_C),
        Utils.formatNumber(row.humidity_RH),
        Utils.formatNumber(row.pressure_hPa),
        Utils.formatNumber(row.lux, 0)
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
   * 清理资源
   */
  cleanup() {
    this.pauseUpdates();
    this.chartManager.disposeAllCharts();
    console.log('🧹 应用资源已清理');
  }
}

// 全局初始化
window.addEventListener('DOMContentLoaded', async () => {
  // 等待外部库加载
  await new Promise(resolve => setTimeout(resolve, 100));
  
  // 初始化应用
  window.lineScopeApp = new LineScopeApp();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
  if (window.lineScopeApp) {
    window.lineScopeApp.cleanup();
  }
});