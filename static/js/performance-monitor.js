/**
 * 高级性能监控系统
 * Linescope Server 性能优化版本
 * 提供实时性能数据收集、分析和报告
 */

export class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.observers = [];
    this.isEnabled = true;
    this.reportInterval = 30000; // 30秒报告间隔
    this.performanceBuffer = [];
    this.maxBufferSize = 100;
    
    this.init();
  }

  /**
   * 初始化性能监控
   */
  init() {
    if (!this.isSupported()) {
      console.warn('[PerformanceMonitor] Performance API not fully supported');
      this.isEnabled = false;
      return;
    }

    console.log('[PerformanceMonitor] 启动性能监控系统');
    
    // 设置各种性能观察器
    this.setupPerformanceObserver();
    this.setupResourceObserver();
    this.setupLayoutObserver();
    this.setupLongTaskObserver();
    
    // 监控核心Web Vitals
    this.setupWebVitalsMonitoring();
    
    // 定期报告
    this.startPeriodicReporting();
    
    // 页面卸载时的性能报告
    this.setupUnloadReporting();
  }

  /**
   * 检查浏览器支持
   */
  isSupported() {
    return !!(
      window.performance &&
      window.performance.timing &&
      window.performance.getEntriesByType &&
      window.PerformanceObserver
    );
  }

  /**
   * 设置基础性能观察器
   */
  setupPerformanceObserver() {
    if (!window.PerformanceObserver) return;

    try {
      // 导航性能观察器
      const navObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.processNavigationEntry(entry);
        }
      });
      navObserver.observe({ entryTypes: ['navigation'] });
      this.observers.push(navObserver);

      // 绘制性能观察器
      const paintObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.processPaintEntry(entry);
        }
      });
      paintObserver.observe({ entryTypes: ['paint'] });
      this.observers.push(paintObserver);

    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to setup performance observer:', error);
    }
  }

  /**
   * 设置资源性能观察器
   */
  setupResourceObserver() {
    if (!window.PerformanceObserver) return;

    try {
      const resourceObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.processResourceEntry(entry);
        }
      });
      resourceObserver.observe({ entryTypes: ['resource'] });
      this.observers.push(resourceObserver);

    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to setup resource observer:', error);
    }
  }

  /**
   * 设置布局偏移观察器
   */
  setupLayoutObserver() {
    if (!window.PerformanceObserver) return;

    try {
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.processLayoutShiftEntry(entry);
        }
      });
      clsObserver.observe({ entryTypes: ['layout-shift'] });
      this.observers.push(clsObserver);

    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to setup layout observer:', error);
    }
  }

  /**
   * 设置长任务观察器
   */
  setupLongTaskObserver() {
    if (!window.PerformanceObserver) return;

    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.processLongTaskEntry(entry);
        }
      });
      longTaskObserver.observe({ entryTypes: ['longtask'] });
      this.observers.push(longTaskObserver);

    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to setup long task observer:', error);
    }
  }

  /**
   * 设置Core Web Vitals监控
   */
  setupWebVitalsMonitoring() {
    // Largest Contentful Paint (LCP)
    this.observeLCP();
    
    // First Input Delay (FID)
    this.observeFID();
    
    // Cumulative Layout Shift (CLS)
    this.observeCLS();
  }

  /**
   * 观察 LCP
   */
  observeLCP() {
    if (!window.PerformanceObserver) return;

    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        
        this.metrics.lcp = {
          value: lastEntry.startTime,
          rating: this.rateLCP(lastEntry.startTime),
          timestamp: Date.now(),
          element: lastEntry.element?.tagName
        };
        
        console.log('[PerformanceMonitor] LCP:', this.metrics.lcp);
      });
      
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      this.observers.push(lcpObserver);
      
    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to observe LCP:', error);
    }
  }

  /**
   * 观察 FID
   */
  observeFID() {
    if (!window.PerformanceObserver) return;

    try {
      const fidObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.metrics.fid = {
            value: entry.processingStart - entry.startTime,
            rating: this.rateFID(entry.processingStart - entry.startTime),
            timestamp: Date.now(),
            eventType: entry.name
          };
          
          console.log('[PerformanceMonitor] FID:', this.metrics.fid);
        }
      });
      
      fidObserver.observe({ entryTypes: ['first-input'] });
      this.observers.push(fidObserver);
      
    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to observe FID:', error);
    }
  }

  /**
   * 观察 CLS
   */
  observeCLS() {
    this.clsScore = 0;
    this.sessionEntries = [];
    
    if (!window.PerformanceObserver) return;

    try {
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            this.sessionEntries.push(entry);
            this.clsScore += entry.value;
          }
        }
        
        this.metrics.cls = {
          value: this.clsScore,
          rating: this.rateCLS(this.clsScore),
          timestamp: Date.now(),
          entryCount: this.sessionEntries.length
        };
      });
      
      clsObserver.observe({ entryTypes: ['layout-shift'] });
      this.observers.push(clsObserver);
      
    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to observe CLS:', error);
    }
  }

  /**
   * 处理导航性能条目
   */
  processNavigationEntry(entry) {
    this.metrics.navigation = {
      domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
      loadComplete: entry.loadEventEnd - entry.loadEventStart,
      timeToFirstByte: entry.responseStart - entry.requestStart,
      domInteractive: entry.domInteractive - entry.navigationStart,
      timestamp: Date.now()
    };
    
    console.log('[PerformanceMonitor] Navigation:', this.metrics.navigation);
  }

  /**
   * 处理绘制性能条目
   */
  processPaintEntry(entry) {
    if (!this.metrics.paint) this.metrics.paint = {};
    
    this.metrics.paint[entry.name.replace('-', '_')] = {
      value: entry.startTime,
      rating: entry.name === 'first-contentful-paint' ? 
        this.rateFCP(entry.startTime) : 'good',
      timestamp: Date.now()
    };
    
    console.log(`[PerformanceMonitor] ${entry.name}:`, entry.startTime);
  }

  /**
   * 处理资源性能条目
   */
  processResourceEntry(entry) {
    // 只监控关键资源
    if (this.isKeyResource(entry.name)) {
      const resourceMetric = {
        name: entry.name,
        duration: entry.duration,
        size: entry.transferSize || 0,
        type: this.getResourceType(entry),
        timestamp: Date.now()
      };
      
      this.addToBuffer('resources', resourceMetric);
    }
  }

  /**
   * 处理布局偏移条目
   */
  processLayoutShiftEntry(entry) {
    if (!entry.hadRecentInput) {
      const shiftMetric = {
        value: entry.value,
        sources: entry.sources?.map(source => ({
          element: source.node?.tagName,
          rect: source.currentRect
        })),
        timestamp: Date.now()
      };
      
      this.addToBuffer('layoutShifts', shiftMetric);
    }
  }

  /**
   * 处理长任务条目
   */
  processLongTaskEntry(entry) {
    const longTaskMetric = {
      duration: entry.duration,
      startTime: entry.startTime,
      attribution: entry.attribution?.map(attr => ({
        name: attr.name,
        type: attr.entryType,
        startTime: attr.startTime
      })),
      timestamp: Date.now()
    };
    
    this.addToBuffer('longTasks', longTaskMetric);
    console.warn('[PerformanceMonitor] Long task detected:', entry.duration, 'ms');
  }

  /**
   * 添加到性能缓冲区
   */
  addToBuffer(category, data) {
    if (!this.performanceBuffer[category]) {
      this.performanceBuffer[category] = [];
    }
    
    this.performanceBuffer[category].push(data);
    
    // 保持缓冲区大小
    if (this.performanceBuffer[category].length > this.maxBufferSize) {
      this.performanceBuffer[category] = this.performanceBuffer[category].slice(-this.maxBufferSize);
    }
  }

  /**
   * 性能评级方法
   */
  rateLCP(value) {
    if (value <= 2500) return 'good';
    if (value <= 4000) return 'needs-improvement';
    return 'poor';
  }

  rateFCP(value) {
    if (value <= 1800) return 'good';
    if (value <= 3000) return 'needs-improvement';
    return 'poor';
  }

  rateFID(value) {
    if (value <= 100) return 'good';
    if (value <= 300) return 'needs-improvement';
    return 'poor';
  }

  rateCLS(value) {
    if (value <= 0.1) return 'good';
    if (value <= 0.25) return 'needs-improvement';
    return 'poor';
  }

  /**
   * 判断是否为关键资源
   */
  isKeyResource(url) {
    const keyPatterns = [
      /\.js$/,
      /\.css$/,
      /api\/.*$/,
      /\.woff2?$/,
      /\.webp$|\.jpg$|\.png$/
    ];
    
    return keyPatterns.some(pattern => pattern.test(url));
  }

  /**
   * 获取资源类型
   */
  getResourceType(entry) {
    if (entry.initiatorType) return entry.initiatorType;
    
    const url = entry.name.toLowerCase();
    if (url.includes('.js')) return 'script';
    if (url.includes('.css')) return 'stylesheet';
    if (url.includes('api/')) return 'fetch';
    if (url.includes('.woff')) return 'font';
    if (url.match(/\.(webp|jpg|png|gif)$/)) return 'image';
    
    return 'other';
  }

  /**
   * 定期性能报告
   */
  startPeriodicReporting() {
    setInterval(() => {
      this.generatePerformanceReport();
    }, this.reportInterval);
  }

  /**
   * 页面卸载时的性能报告
   */
  setupUnloadReporting() {
    window.addEventListener('beforeunload', () => {
      this.generatePerformanceReport(true);
    });
  }

  /**
   * 生成性能报告
   */
  generatePerformanceReport(isFinal = false) {
    const report = {
      timestamp: new Date().toISOString(),
      session: this.generateSessionId(),
      final: isFinal,
      metrics: this.metrics,
      buffer: this.performanceBuffer,
      summary: this.generateSummary()
    };

    // 输出到控制台
    console.group(`[PerformanceMonitor] 性能报告 ${isFinal ? '(最终)' : ''}`);
    console.log('Core Web Vitals:', {
      LCP: this.metrics.lcp,
      FID: this.metrics.fid,
      CLS: this.metrics.cls
    });
    console.log('导航性能:', this.metrics.navigation);
    console.log('绘制性能:', this.metrics.paint);
    console.log('性能摘要:', report.summary);
    console.groupEnd();

    // 发送到服务器（如果需要）
    if (this.shouldSendToServer()) {
      this.sendPerformanceReport(report);
    }

    return report;
  }

  /**
   * 生成会话ID
   */
  generateSessionId() {
    return this.sessionId || (this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9));
  }

  /**
   * 生成性能摘要
   */
  generateSummary() {
    return {
      overallRating: this.calculateOverallRating(),
      criticalIssues: this.identifyCriticalIssues(),
      recommendations: this.generateRecommendations()
    };
  }

  /**
   * 计算总体评级
   */
  calculateOverallRating() {
    const ratings = [];
    
    if (this.metrics.lcp) ratings.push(this.metrics.lcp.rating);
    if (this.metrics.fid) ratings.push(this.metrics.fid.rating);
    if (this.metrics.cls) ratings.push(this.metrics.cls.rating);

    const poorCount = ratings.filter(r => r === 'poor').length;
    const needsImprovementCount = ratings.filter(r => r === 'needs-improvement').length;

    if (poorCount > 0) return 'poor';
    if (needsImprovementCount > 0) return 'needs-improvement';
    return 'good';
  }

  /**
   * 识别关键问题
   */
  identifyCriticalIssues() {
    const issues = [];
    
    if (this.metrics.lcp?.rating === 'poor') {
      issues.push('LCP超过4秒，需要优化最大内容绘制');
    }
    
    if (this.performanceBuffer.longTasks?.length > 5) {
      issues.push('检测到多个长任务，可能阻塞主线程');
    }
    
    if (this.metrics.cls?.value > 0.25) {
      issues.push('布局偏移过大，影响用户体验');
    }

    return issues;
  }

  /**
   * 生成优化建议
   */
  generateRecommendations() {
    const recommendations = [];
    
    if (this.metrics.lcp?.value > 2500) {
      recommendations.push('优化图像加载和服务器响应时间');
    }
    
    if (this.performanceBuffer.longTasks?.length > 0) {
      recommendations.push('拆分长任务，使用requestIdleCallback');
    }
    
    if (this.metrics.cls?.value > 0.1) {
      recommendations.push('为图像和动态内容预留空间');
    }

    return recommendations;
  }

  /**
   * 判断是否发送到服务器
   */
  shouldSendToServer() {
    // 在生产环境中可能需要发送性能数据到监控服务
    return false; // 目前只在本地记录
  }

  /**
   * 发送性能报告到服务器
   */
  async sendPerformanceReport(report) {
    try {
      await fetch('/api/performance-metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(report)
      });
    } catch (error) {
      console.warn('[PerformanceMonitor] Failed to send performance report:', error);
    }
  }

  /**
   * 手动记录性能标记
   */
  mark(name) {
    if (window.performance?.mark) {
      performance.mark(name);
    }
  }

  /**
   * 手动测量性能
   */
  measure(name, startMark, endMark) {
    if (window.performance?.measure) {
      try {
        performance.measure(name, startMark, endMark);
        const entry = performance.getEntriesByName(name)[0];
        console.log(`[PerformanceMonitor] ${name}:`, entry.duration, 'ms');
        return entry.duration;
      } catch (error) {
        console.warn('[PerformanceMonitor] Failed to measure:', error);
      }
    }
  }

  /**
   * 销毁监控器
   */
  destroy() {
    console.log('[PerformanceMonitor] 销毁性能监控系统');
    
    // 断开所有观察器
    this.observers.forEach(observer => {
      try {
        observer.disconnect();
      } catch (error) {
        console.warn('Failed to disconnect observer:', error);
      }
    });
    
    this.observers = [];
    this.performanceBuffer = [];
    this.metrics = {};
    this.isEnabled = false;
  }
}

// 全局性能监控器实例
window.performanceMonitor = new PerformanceMonitor();

console.log('[PerformanceMonitor] 性能监控系统已加载');