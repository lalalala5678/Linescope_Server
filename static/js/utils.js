/**
 * 工具函数模块
 * 提供通用的数据处理、格式化等功能
 */

export class Utils {
  /**
   * 格式化数字
   */
  static formatNumber(num, precision = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toFixed(precision);
  }

  /**
   * 防抖函数
   */
  static debounce(func, wait) {
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

  /**
   * 节流函数
   */
  static throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  /**
   * 休眠函数
   */
  static sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 计算趋势
   */
  static calculateTrend(current, previous) {
    if (!previous || previous === 0) return { percentage: 0, direction: 'stable' };
    const change = ((current - previous) / previous) * 100;
    const direction = Math.abs(change) < 1 ? 'stable' : change > 0 ? 'up' : 'down';
    return { percentage: Math.abs(change), direction };
  }

  /**
   * 日期格式化
   */
  static formatDate(date, format = 'YYYY-MM-DD HH:mm') {
    if (!date) return '--';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return format
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hours)
      .replace('mm', minutes);
  }
}