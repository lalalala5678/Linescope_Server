/**
 * API数据管理模块
 * 处理所有与后端API的通信
 */

export class ApiManager {
  constructor(config = {}) {
    this.config = {
      baseUrl: '',
      timeout: 10000,
      retryAttempts: 3,
      ...config
    };
  }

  /**
   * 带重试机制的fetch请求
   */
  async fetchWithRetry(url, options = {}, retries = this.config.retryAttempts) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
    
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
      
      if (retries > 0 && error.name !== 'AbortError') {
        console.warn(`请求失败，重试中... (${retries} 次剩余)`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        return this.fetchWithRetry(url, options, retries - 1);
      }
      
      throw error;
    }
  }

  /**
   * 获取所有传感器数据
   */
  async getSensorData() {
    try {
      const data = await this.fetchWithRetry('/api/sensor-data');
      console.log(`获取到 ${data.length} 条传感器数据`);
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error('获取传感器数据失败:', error);
      return [];
    }
  }

  /**
   * 获取最新传感器数据
   */
  async getLatestSensorData() {
    try {
      const data = await this.fetchWithRetry('/api/sensors/latest');
      console.log('获取到最新传感器数据:', data);
      return data;
    } catch (error) {
      console.error('获取最新传感器数据失败:', error);
      return null;
    }
  }

  /**
   * 获取指定数量的传感器数据
   */
  async getSensorDataWithLimit(limit) {
    try {
      const data = await this.fetchWithRetry(`/api/sensors?limit=${limit}`);
      const rows = data.rows || data;
      console.log(`获取到 ${rows.length} 条限制数据`);
      return Array.isArray(rows) ? rows : [];
    } catch (error) {
      console.error('获取限制传感器数据失败:', error);
      return [];
    }
  }

  /**
   * 健康检查
   */
  async healthCheck() {
    try {
      await this.fetchWithRetry('/healthz');
      return true;
    } catch (error) {
      console.error('健康检查失败:', error);
      return false;
    }
  }
}