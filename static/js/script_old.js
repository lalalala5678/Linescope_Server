/**
 * Linescope Server - Modern JavaScript Module
 * Enhanced with ES6+ features, modern APIs, and advanced functionality
 */

// Modern module pattern with ES6 classes and async/await
class LineScopeApp {
  constructor() {
    this.config = {
      refreshInterval: 5 * 60 * 1000, // 5 minutes
      chartUpdateInterval: 30 * 1000, // 30 seconds
      connectionTimeout: 10000,
      retryAttempts: 3,
      debounceDelay: 300,
    };

    this.state = {
      isConnected: false,
      lastUpdate: null,
      sensorData: [],
      charts: new Map(),
      reconnectAttempts: 0,
      notifications: new Set(),
    };

    this.controllers = {
      fetchController: null,
      chartController: null,
    };

    this.eventListeners = new Map();
    this.observers = new Map();

    this.init();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      await this.setupEventListeners();
      await this.initializeServiceWorker();
      await this.detectPageType();
      await this.startPeriodicUpdates();
      
      console.info('🚀 LineScopeApp initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize LineScopeApp:', error);
      this.showNotification('初始化失败', 'error');
    }
  }

  /**
   * Detect current page type and initialize accordingly
   */
  async detectPageType() {
    const pageIndicators = [
      { selector: '#dashboard-root', type: 'dashboard', handler: this.initDashboard },
      { selector: '.video-container', type: 'video', handler: this.initVideoPage },
      { selector: '#preview-chart', type: 'home', handler: this.initHomePage },
    ];

    const currentPage = pageIndicators.find(({ selector }) => 
      document.querySelector(selector)
    );

    if (currentPage) {
      console.info(`📄 Detected page type: ${currentPage.type}`);
      await currentPage.handler.call(this);
    }
  }

  /**
   * Initialize Service Worker for caching and offline support
   */
  async initializeServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.info('✅ Service Worker registered:', registration);
      } catch (error) {
        console.warn('⚠️ Service Worker registration failed:', error);
      }
    }
  }

  /**
   * Initialize dashboard page with advanced features
   */
  async initDashboard() {
    this.dashboardState = {
      dataGrid: null,
      miniCharts: new Map(),
      kpiCards: new Map(),
      filters: {
        dateRange: 'last24h',
        metrics: ['all'],
      },
    };

    await this.setupDashboardComponents();
    await this.loadDashboardData();
    this.setupRealTimeUpdates();
    this.setupDataExport();
    this.setupAdvancedFiltering();
  }

  /**
   * Setup dashboard components with modern APIs
   */
  async setupDashboardComponents() {
    // Initialize advanced data grid
    await this.initializeAdvancedGrid();
    
    // Setup real-time charts with WebGL acceleration
    await this.initializeAdvancedCharts();
    
    // Initialize performance monitoring
    this.initializePerformanceMonitoring();
    
    // Setup intersection observer for lazy loading
    this.setupIntersectionObserver();
  }

  /**
   * Initialize advanced data grid with virtual scrolling
   */
  async initializeAdvancedGrid() {
    if (typeof agGrid === 'undefined') return;

    const gridDiv = document.querySelector('#data-grid');
    if (!gridDiv) return;

    const columnDefs = [
      {
        field: 'timestamp_Beijing',
        headerName: '时间戳',
        width: 180,
        pinned: 'left',
        cellRenderer: this.createTimestampRenderer(),
        sort: 'desc',
      },
      {
        field: 'sway_speed_dps',
        headerName: '晃动速度 (°/s)',
        width: 140,
        type: 'numericColumn',
        cellRenderer: this.createAlertRenderer(60),
        cellClass: this.createAlertCellClass(60),
      },
      {
        field: 'temperature_C',
        headerName: '温度 (°C)',
        width: 120,
        type: 'numericColumn',
        cellRenderer: this.createMetricRenderer('temperature'),
      },
      {
        field: 'humidity_RH',
        headerName: '湿度 (%RH)',
        width: 120,
        type: 'numericColumn',
        cellRenderer: this.createMetricRenderer('humidity'),
      },
      {
        field: 'pressure_hPa',
        headerName: '气压 (hPa)',
        width: 130,
        type: 'numericColumn',
        cellRenderer: this.createMetricRenderer('pressure'),
      },
      {
        field: 'lux',
        headerName: '光照 (Lux)',
        width: 120,
        type: 'numericColumn',
        cellRenderer: this.createMetricRenderer('light'),
      },
    ];

    const gridOptions = {
      columnDefs,
      defaultColDef: {
        sortable: true,
        filter: true,
        resizable: true,
        floatingFilter: true,
      },
      pagination: true,
      paginationPageSize: 50,
      paginationAutoPageSize: true,
      animateRows: true,
      enableRangeSelection: true,
      suppressScrollOnNewData: true,
      rowBuffer: 10,
      getRowStyle: this.createRowStyleFunction(),
      onGridReady: (params) => {
        this.dashboardState.dataGrid = params.api;
        params.api.sizeColumnsToFit();
      },
    };

    this.dashboardState.gridApi = agGrid.createGrid(gridDiv, gridOptions);
  }

  /**
   * Initialize advanced charts with modern charting library
   */
  async initializeAdvancedCharts() {
    if (typeof echarts === 'undefined') return;

    const chartConfigs = [
      {
        id: 'environmental-chart',
        type: 'multiAxis',
        series: ['temperature_C', 'humidity_RH', 'pressure_hPa'],
      },
      {
        id: 'sway-chart',
        type: 'threshold',
        series: ['sway_speed_dps'],
        threshold: 60,
      },
      {
        id: 'preview-chart',
        type: 'overview',
        series: ['temperature_C', 'humidity_RH', 'pressure_hPa'],
      },
    ];

    for (const config of chartConfigs) {
      const element = document.getElementById(config.id);
      if (element) {
        const chart = await this.createAdvancedChart(element, config);
        this.state.charts.set(config.id, chart);
      }
    }
  }

  /**
   * Create advanced chart with modern features
   */
  async createAdvancedChart(element, config) {
    const chart = echarts.init(element, 'dark', {
      renderer: 'webgl', // Use WebGL for better performance
      useDirtyRect: true, // Optimize rendering
    });

    const baseOption = {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 750,
      animationEasing: 'cubicOut',
      tooltip: this.createAdvancedTooltip(),
      legend: this.createAdvancedLegend(),
      grid: this.createResponsiveGrid(),
      dataZoom: this.createDataZoomComponent(),
      toolbox: this.createToolbox(),
      brush: config.type === 'overview' ? this.createBrushComponent() : undefined,
    };

    chart.setOption(baseOption);

    // Add resize observer
    const resizeObserver = new ResizeObserver(
      this.debounce(() => chart.resize(), this.config.debounceDelay)
    );
    resizeObserver.observe(element);
    this.observers.set(`chart-${config.id}`, resizeObserver);

    return chart;
  }

  /**
   * Setup real-time updates with WebSocket fallback
   */
  setupRealTimeUpdates() {
    // Try WebSocket first, fallback to Server-Sent Events, then polling
    this.initializeWebSocket()
      .catch(() => this.initializeSSE())
      .catch(() => this.initializePolling());
  }

  /**
   * Initialize WebSocket connection
   */
  async initializeWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.info('🔗 WebSocket connected');
        this.state.isConnected = true;
        resolve(ws);
      };
      
      ws.onerror = (error) => {
        console.warn('⚠️ WebSocket failed:', error);
        reject(error);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleRealtimeData(data);
        } catch (error) {
          console.error('❌ Failed to parse WebSocket data:', error);
        }
      };
      
      ws.onclose = () => {
        console.info('🔌 WebSocket disconnected');
        this.state.isConnected = false;
        // Implement reconnection logic
        setTimeout(() => this.initializeWebSocket().catch(() => {}), 5000);
      };
    });
  }

  /**
   * Initialize Server-Sent Events
   */
  async initializeSSE() {
    return new Promise((resolve, reject) => {
      const eventSource = new EventSource('/api/stream');
      
      eventSource.onopen = () => {
        console.info('📡 SSE connected');
        this.state.isConnected = true;
        resolve(eventSource);
      };
      
      eventSource.onerror = (error) => {
        console.warn('⚠️ SSE failed:', error);
        reject(error);
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleRealtimeData(data);
        } catch (error) {
          console.error('❌ Failed to parse SSE data:', error);
        }
      };
    });
  }

  /**
   * Initialize polling as fallback
   */
  initializePolling() {
    console.info('🔄 Using polling for updates');
    
    const poll = async () => {
      try {
        const data = await this.fetchWithRetry('/api/sensor-data');
        this.handleRealtimeData({ type: 'data', payload: data });
        this.state.isConnected = true;
      } catch (error) {
        console.error('❌ Polling failed:', error);
        this.state.isConnected = false;
      }
      
      setTimeout(poll, this.config.chartUpdateInterval);
    };
    
    poll();
  }

  /**
   * Handle real-time data updates
   */
  handleRealtimeData(data) {
    const { type, payload } = data;
    
    switch (type) {
      case 'data':
        this.updateSensorData(payload);
        break;
      case 'alert':
        this.handleAlert(payload);
        break;
      case 'status':
        this.updateSystemStatus(payload);
        break;
      default:
        console.warn('⚠️ Unknown data type:', type);
    }
    
    this.state.lastUpdate = new Date();
    this.updateConnectionStatus();
  }

  /**
   * Fetch data with retry mechanism
   */
  async fetchWithRetry(url, options = {}, retries = this.config.retryAttempts) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.connectionTimeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (retries > 0) {
        console.warn(`⚠️ Fetch failed, retrying... (${retries} attempts left)`);
        await this.sleep(1000 * (this.config.retryAttempts - retries + 1));
        return this.fetchWithRetry(url, options, retries - 1);
      }
      
      throw error;
    }
  }

  /**
   * Initialize video page with advanced streaming features
   */
  async initVideoPage() {
    this.videoState = {
      stream: null,
      isFullscreen: false,
      isRecording: false,
      stats: {
        fps: 0,
        bitrate: 0,
        latency: 0,
      },
    };

    await this.setupVideoStream();
    await this.setupVideoControls();
    await this.setupStreamAnalytics();
  }

  /**
   * Setup advanced video streaming
   */
  async setupVideoStream() {
    const videoElement = document.getElementById('video-stream');
    if (!videoElement) return;

    // Setup Intersection Observer for lazy loading
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          this.startVideoStream();
        } else {
          this.pauseVideoStream();
        }
      });
    });

    observer.observe(videoElement);
    this.observers.set('video-stream', observer);

    // Setup performance monitoring
    this.setupVideoPerformanceMonitoring();
  }

  /**
   * Initialize home page with modern features
   */
  async initHomePage() {
    this.homeState = {
      previewChart: null,
      liveMetrics: new Map(),
      updateInterval: null,
    };

    await this.setupHomeComponents();
    await this.startLiveMetricsUpdates();
  }

  /**
   * Setup modern event listeners
   */
  async setupEventListeners() {
    // Use modern event delegation
    document.addEventListener('click', this.handleGlobalClick.bind(this));
    document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));
    
    // Setup visibility change detection
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    
    // Setup connection monitoring
    window.addEventListener('online', this.handleConnectionChange.bind(this));
    window.addEventListener('offline', this.handleConnectionChange.bind(this));
    
    // Setup performance monitoring
    if ('PerformanceObserver' in window) {
      this.setupPerformanceObserver();
    }
  }

  /**
   * Global click handler with event delegation
   */
  handleGlobalClick(event) {
    const { target } = event;
    const action = target.dataset.action;
    
    if (!action) return;

    const handlers = {
      'refresh-data': () => this.refreshAllData(),
      'export-csv': () => this.exportDataAsCSV(),
      'toggle-fullscreen': () => this.toggleFullscreen(),
      'take-screenshot': () => this.takeScreenshot(),
      'clear-cache': () => this.clearApplicationCache(),
      'test-connection': () => this.testConnection(),
    };

    const handler = handlers[action];
    if (handler) {
      event.preventDefault();
      handler();
    }
  }

  /**
   * Global keyboard handler
   */
  handleGlobalKeydown(event) {
    const keyHandlers = {
      'F11': (e) => {
        e.preventDefault();
        this.toggleFullscreen();
      },
      'F5': (e) => {
        if (e.ctrlKey) {
          e.preventDefault();
          this.refreshAllData();
        }
      },
      'KeyS': (e) => {
        if (e.ctrlKey) {
          e.preventDefault();
          this.takeScreenshot();
        }
      },
      'KeyE': (e) => {
        if (e.ctrlKey) {
          e.preventDefault();
          this.exportDataAsCSV();
        }
      },
    };

    const handler = keyHandlers[event.code];
    if (handler) {
      handler(event);
    }
  }

  /**
   * Handle visibility changes for performance optimization
   */
  handleVisibilityChange() {
    if (document.hidden) {
      // Pause updates when tab is not visible
      this.pauseUpdates();
    } else {
      // Resume updates when tab becomes visible
      this.resumeUpdates();
    }
  }

  /**
   * Modern notification system
   */
  showNotification(message, type = 'info', options = {}) {
    const notification = {
      id: crypto.randomUUID(),
      message,
      type,
      timestamp: Date.now(),
      ...options,
    };

    this.state.notifications.add(notification);

    // Create notification element
    const element = this.createNotificationElement(notification);
    document.body.appendChild(element);

    // Auto-remove after duration
    setTimeout(() => {
      this.removeNotification(notification.id);
    }, options.duration || 5000);

    return notification.id;
  }

  /**
   * Create notification element
   */
  createNotificationElement(notification) {
    const element = document.createElement('div');
    element.className = `
      fixed top-4 right-4 z-50 max-w-sm w-full bg-white dark:bg-gray-800 
      shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 
      transform transition-all duration-300 ease-in-out
    `;
    element.dataset.notificationId = notification.id;

    const typeColors = {
      success: 'text-green-400',
      error: 'text-red-400',
      warning: 'text-yellow-400',
      info: 'text-blue-400',
    };

    const typeIcons = {
      success: 'check-circle',
      error: 'x-circle',
      warning: 'alert-triangle',
      info: 'info',
    };

    element.innerHTML = `
      <div class="p-4">
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <i data-lucide="${typeIcons[notification.type]}" class="h-6 w-6 ${typeColors[notification.type]}"></i>
          </div>
          <div class="ml-3 w-0 flex-1 pt-0.5">
            <p class="text-sm font-medium text-gray-900 dark:text-white">
              ${notification.message}
            </p>
          </div>
          <div class="ml-4 flex-shrink-0 flex">
            <button class="bg-white dark:bg-gray-800 rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
                    onclick="window.lineScopeApp.removeNotification('${notification.id}')">
              <i data-lucide="x" class="h-5 w-5"></i>
            </button>
          </div>
        </div>
      </div>
    `;

    // Initialize icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }

    return element;
  }

  /**
   * Remove notification
   */
  removeNotification(id) {
    const element = document.querySelector(`[data-notification-id="${id}"]`);
    if (element) {
      element.style.opacity = '0';
      element.style.transform = 'translateX(100%)';
      setTimeout(() => element.remove(), 300);
    }
    
    this.state.notifications.delete(
      [...this.state.notifications].find(n => n.id === id)
    );
  }

  /**
   * Advanced data export with multiple formats
   */
  async exportDataAsCSV(format = 'csv') {
    try {
      const data = this.state.sensorData;
      if (!data.length) {
        throw new Error('没有数据可导出');
      }

      const exporters = {
        csv: this.exportAsCSV,
        json: this.exportAsJSON,
        xlsx: this.exportAsExcel,
      };

      const exporter = exporters[format];
      if (exporter) {
        await exporter.call(this, data);
        this.showNotification(`数据已导出为 ${format.toUpperCase()}`, 'success');
      }
    } catch (error) {
      console.error('❌ Export failed:', error);
      this.showNotification('导出失败', 'error');
    }
  }

  /**
   * Export as CSV
   */
  exportAsCSV(data) {
    const headers = ['时间戳', '晃动速度(°/s)', '温度(°C)', '湿度(%)', '气压(hPa)', '光照(Lux)'];
    const rows = data.map(row => [
      row.timestamp_Beijing,
      this.formatNumber(row.sway_speed_dps),
      this.formatNumber(row.temperature_C),
      this.formatNumber(row.humidity_RH),
      this.formatNumber(row.pressure_hPa),
      this.formatNumber(row.lux, 0),
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    this.downloadFile(csvContent, 'text/csv', 'sensor-data.csv');
  }

  /**
   * Export as JSON
   */
  exportAsJSON(data) {
    const jsonContent = JSON.stringify(data, null, 2);
    this.downloadFile(jsonContent, 'application/json', 'sensor-data.json');
  }

  /**
   * Download file utility
   */
  downloadFile(content, mimeType, filename) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up
    setTimeout(() => URL.revokeObjectURL(url), 100);
  }

  /**
   * Utility functions
   */
  formatNumber(num, precision = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toFixed(precision);
  }

  debounce(func, wait) {
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

  throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Performance monitoring
   */
  setupPerformanceObserver() {
    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (entry.entryType === 'measure') {
          console.debug(`⏱️ Performance: ${entry.name} took ${entry.duration.toFixed(2)}ms`);
        }
      });
    });

    observer.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    // Clear intervals
    Object.values(this.controllers).forEach(controller => {
      if (controller && controller.abort) {
        controller.abort();
      }
    });

    // Disconnect observers
    this.observers.forEach(observer => observer.disconnect());
    
    // Clear charts
    this.state.charts.forEach(chart => chart.dispose());
    
    // Clear notifications
    this.state.notifications.forEach(notification => {
      this.removeNotification(notification.id);
    });

    console.info('🧹 LineScopeApp cleaned up');
  }

  /**
   * Placeholder methods for complex features
   * These would be implemented based on specific requirements
   */
  
  // Chart creation helpers
  createTimestampRenderer() { return (params) => `<code>${params.value}</code>`; }
  createAlertRenderer(threshold) { 
    return (params) => {
      const isAlert = params.value > threshold;
      const className = isAlert ? 'text-red-400 font-bold' : 'text-white';
      return `<span class="${className}">${this.formatNumber(params.value)}</span>`;
    };
  }
  createMetricRenderer(type) { return (params) => this.formatNumber(params.value); }
  createAlertCellClass(threshold) { 
    return (params) => params.value > threshold ? 'bg-red-900/20' : '';
  }
  createRowStyleFunction() { 
    return (params) => params.data.sway_speed_dps > 60 ? { backgroundColor: 'rgba(239, 68, 68, 0.1)' } : null;
  }

  // Chart configuration helpers
  createAdvancedTooltip() { return { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)' }; }
  createAdvancedLegend() { return { textStyle: { color: '#fff' } }; }
  createResponsiveGrid() { return { left: '3%', right: '4%', bottom: '3%', containLabel: true }; }
  createDataZoomComponent() { return [{ type: 'inside' }, { type: 'slider' }]; }
  createToolbox() { return { feature: { saveAsImage: {}, dataZoom: {}, restore: {} } }; }
  createBrushComponent() { return { toolbox: ['rect', 'polygon', 'clear'] }; }

  // Placeholder implementations
  async loadDashboardData() { /* Load dashboard data */ }
  async setupHomeComponents() { /* Setup home components */ }
  async startLiveMetricsUpdates() { /* Start live updates */ }
  async setupVideoControls() { /* Setup video controls */ }
  async setupStreamAnalytics() { /* Setup stream analytics */ }
  setupVideoPerformanceMonitoring() { /* Setup video monitoring */ }
  setupAdvancedFiltering() { /* Setup filtering */ }
  setupDataExport() { /* Setup export functionality */ }
  initializePerformanceMonitoring() { /* Initialize performance monitoring */ }
  setupIntersectionObserver() { /* Setup intersection observer */ }
  startVideoStream() { /* Start video stream */ }
  pauseVideoStream() { /* Pause video stream */ }
  updateSensorData(data) { this.state.sensorData = data; }
  handleAlert(alert) { this.showNotification(alert.message, 'warning'); }
  updateSystemStatus(status) { this.state.isConnected = status.connected; }
  updateConnectionStatus() { /* Update connection status */ }
  refreshAllData() { /* Refresh all data */ }
  toggleFullscreen() { /* Toggle fullscreen */ }
  takeScreenshot() { /* Take screenshot */ }
  clearApplicationCache() { /* Clear cache */ }
  testConnection() { /* Test connection */ }
  pauseUpdates() { /* Pause updates */ }
  resumeUpdates() { /* Resume updates */ }
  startPeriodicUpdates() { /* Start periodic updates */ }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.lineScopeApp = new LineScopeApp();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
  if (window.lineScopeApp) {
    window.lineScopeApp.cleanup();
  }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LineScopeApp;
}