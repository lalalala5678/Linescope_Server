/**
 * 图表管理模块
 * 处理所有ECharts相关功能
 */

import { Utils } from './utils.js';

export class ChartManager {
  constructor() {
    this.charts = new Map();
    this.isEChartsReady = false;
    this.checkEChartsReady();
  }

  /**
   * 检查ECharts是否就绪
   */
  async checkEChartsReady() {
    if (typeof echarts !== 'undefined') {
      this.isEChartsReady = true;
      console.log('ECharts 已就绪');
      return true;
    }

    // 等待ECharts加载
    let attempts = 0;
    const maxAttempts = 50; // 5秒最大等待时间

    while (attempts < maxAttempts) {
      await Utils.sleep(100);
      if (typeof echarts !== 'undefined') {
        this.isEChartsReady = true;
        console.log('ECharts 加载完成');
        return true;
      }
      attempts++;
    }

    console.error('ECharts 加载超时');
    return false;
  }

  /**
   * 创建图表实例
   */
  async createChart(containerId, config = {}) {
    if (!this.isEChartsReady) {
      await this.checkEChartsReady();
    }

    if (!this.isEChartsReady) {
      console.error('ECharts 未就绪，无法创建图表');
      return null;
    }

    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`图表容器未找到: ${containerId}`);
      return null;
    }

    // 销毁已存在的图表
    if (this.charts.has(containerId)) {
      this.charts.get(containerId).dispose();
    }

    try {
      const chart = echarts.init(container, 'dark', {
        renderer: 'canvas', // 使用canvas渲染以确保兼容性
        useDirtyRect: true
      });

      this.charts.set(containerId, chart);
      console.log(`图表创建成功: ${containerId}`);
      
      return chart;
    } catch (error) {
      console.error(`创建图表失败 ${containerId}:`, error);
      return null;
    }
  }

  /**
   * 创建预览图表（首页用）
   */
  async createPreviewChart(containerId, data) {
    const chart = await this.createChart(containerId);
    if (!chart || !data || data.length === 0) return null;

    const times = data.map(d => d.timestamp_Beijing);
    const temps = data.map(d => d.temperature_C);
    const humidities = data.map(d => d.humidity_RH);
    const pressures = data.map(d => d.pressure_hPa);

    const option = {
      backgroundColor: 'transparent',
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '15%',
        containLabel: true
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        textStyle: { color: '#fff' },
        formatter: function(params) {
          let result = `<div style="font-weight: bold; margin-bottom: 5px;">${params[0].axisValue}</div>`;
          params.forEach(param => {
            result += `<div>${param.marker} ${param.seriesName}: ${param.value}${param.seriesName.includes('气压') ? ' hPa' : (param.seriesName.includes('温度') ? '°C' : '%')}</div>`;
          });
          return result;
        }
      },
      legend: {
        data: ['温度', '湿度', '气压'],
        textStyle: { color: '#fff' },
        top: 10
      },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: { 
          color: '#fff',
          rotate: 45,
          formatter: function(value) {
            return value ? value.split(' ')[1] : '';
          }
        },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } },
        axisTick: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } }
      },
      yAxis: [
        {
          type: 'value',
          name: '温度(°C) / 湿度(%)',
          nameTextStyle: { color: '#fff' },
          axisLabel: { color: '#fff' },
          axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } },
          splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
        },
        {
          type: 'value',
          name: '气压(hPa)',
          nameTextStyle: { color: '#fff' },
          axisLabel: { color: '#fff' },
          axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } }
        }
      ],
      series: [
        {
          name: '温度',
          type: 'line',
          data: temps,
          smooth: true,
          lineStyle: { color: '#60a5fa', width: 3 },
          itemStyle: { color: '#60a5fa' },
          areaStyle: { 
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(96, 165, 250, 0.3)' },
                { offset: 1, color: 'rgba(96, 165, 250, 0.1)' }
              ]
            }
          }
        },
        {
          name: '湿度',
          type: 'line',
          data: humidities,
          smooth: true,
          lineStyle: { color: '#34d399', width: 3 },
          itemStyle: { color: '#34d399' },
          areaStyle: { 
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(52, 211, 153, 0.3)' },
                { offset: 1, color: 'rgba(52, 211, 153, 0.1)' }
              ]
            }
          }
        },
        {
          name: '气压',
          type: 'line',
          yAxisIndex: 1,
          data: pressures,
          smooth: true,
          lineStyle: { color: '#a78bfa', width: 3 },
          itemStyle: { color: '#a78bfa' },
          areaStyle: { 
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(167, 139, 250, 0.3)' },
                { offset: 1, color: 'rgba(167, 139, 250, 0.1)' }
              ]
            }
          }
        }
      ]
    };

    chart.setOption(option, true);
    console.log(`预览图表更新完成: ${data.length} 数据点`);
    return chart;
  }

  /**
   * 创建环境参数趋势图表
   */
  async createEnvironmentalChart(containerId, data) {
    const chart = await this.createChart(containerId);
    if (!chart || !data || data.length === 0) return null;

    const times = data.map(d => d.timestamp_Beijing);
    
    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: 'rgba(148, 163, 184, 0.2)',
        textStyle: { color: '#fff' }
      },
      legend: {
        data: ['温度', '湿度', '气压'],
        textStyle: { color: '#e2e8f0' },
        top: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: {
          color: '#94a3b8',
          formatter: function(value) {
            return value ? value.split(' ')[1] : '';
          }
        },
        axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } }
      },
      yAxis: [
        {
          type: 'value',
          name: '温度 (°C) / 湿度 (%)',
          axisLabel: { color: '#94a3b8' },
          axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
          splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
        },
        {
          type: 'value',
          name: '气压 (hPa)',
          axisLabel: { color: '#94a3b8' },
          axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } }
        }
      ],
      series: [
        {
          name: '温度',
          type: 'line',
          data: data.map(d => d.temperature_C),
          smooth: true,
          lineStyle: { color: '#60a5fa', width: 2 },
          areaStyle: { color: 'rgba(96, 165, 250, 0.1)' }
        },
        {
          name: '湿度',
          type: 'line',
          data: data.map(d => d.humidity_RH),
          smooth: true,
          lineStyle: { color: '#34d399', width: 2 },
          areaStyle: { color: 'rgba(52, 211, 153, 0.1)' }
        },
        {
          name: '气压',
          type: 'line',
          yAxisIndex: 1,
          data: data.map(d => d.pressure_hPa),
          smooth: true,
          lineStyle: { color: '#a78bfa', width: 2 },
          areaStyle: { color: 'rgba(167, 139, 250, 0.1)' }
        }
      ]
    };

    chart.setOption(option, true);
    console.log(`环境参数图表更新完成: ${data.length} 数据点`);
    return chart;
  }

  /**
   * 创建晃动分析图表
   */
  async createSwayChart(containerId, data) {
    const chart = await this.createChart(containerId);
    if (!chart || !data || data.length === 0) return null;

    const times = data.map(d => d.timestamp_Beijing);
    const swayData = data.map(d => d.sway_speed_dps);
    const alertThreshold = 60;
    const alertData = swayData.map((v, i) => v > alertThreshold ? [i, v] : null).filter(v => v !== null);

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: 'rgba(148, 163, 184, 0.2)',
        textStyle: { color: '#fff' }
      },
      legend: {
        data: ['晃动速度', '异常阈值', '超标数据'],
        textStyle: { color: '#e2e8f0' },
        top: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: {
          color: '#94a3b8',
          formatter: function(value) {
            return value ? value.split(' ')[1] : '';
          }
        },
        axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } }
      },
      yAxis: {
        type: 'value',
        name: '晃动速度 (°/s)',
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
      },
      series: [
        {
          name: '晃动速度',
          type: 'line',
          data: swayData,
          smooth: true,
          lineStyle: { color: '#f87171', width: 2 },
          areaStyle: { color: 'rgba(248, 113, 113, 0.1)' }
        },
        {
          name: '异常阈值',
          type: 'line',
          data: new Array(times.length).fill(alertThreshold),
          lineStyle: { 
            color: '#ef4444', 
            width: 2, 
            type: 'dashed' 
          },
          symbol: 'none'
        },
        {
          name: '超标数据',
          type: 'scatter',
          data: alertData,
          symbolSize: 8,
          itemStyle: { color: '#dc2626' }
        }
      ]
    };

    chart.setOption(option, true);
    console.log(`晃动分析图表更新完成: ${data.length} 数据点, ${alertData.length} 个超标点`);
    return chart;
  }

  /**
   * 调整所有图表大小
   */
  resizeAllCharts() {
    this.charts.forEach((chart, id) => {
      try {
        chart.resize();
      } catch (error) {
        console.warn(`调整图表大小失败 ${id}:`, error);
      }
    });
  }

  /**
   * 销毁所有图表
   */
  disposeAllCharts() {
    this.charts.forEach((chart, id) => {
      try {
        chart.dispose();
      } catch (error) {
        console.warn(`销毁图表失败 ${id}:`, error);
      }
    });
    this.charts.clear();
  }

  /**
   * 获取图表实例
   */
  getChart(containerId) {
    return this.charts.get(containerId);
  }
}