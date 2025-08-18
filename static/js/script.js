/* =========================================================
 * Linescope Server - static/js/script.js
 * 功能：
 *  - Dashboard：拉数据、表格渲染、统计、图表（Chart.js 或 Canvas 兜底）
 *  - Result：MJPEG 流状态指示（在线/离线）
 *  - 通用：下载 CSV、格式化工具等
 * 依赖：
 *  - 可选 Chart.js（如果引入则自动启用更丰富的图表；未引入则自动降级）
 * ========================================================= */

(() => {
  const isDashboard = !!document.querySelector('#dashboard-root') || !!document.querySelector('#chart1') || !!document.querySelector('#sensor-table');
  const isResult = !!document.querySelector('.stream-container');

  /* -----------------------------
   * 公共小工具
   * ----------------------------- */
  const $$ = (sel, root = document) => root.querySelector(sel);
  const $$$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const fmtNum = (v, digits = 2) => {
    if (v === null || v === undefined || Number.isNaN(+v)) return '-';
    return Number(v).toFixed(digits);
  };

  const throttle = (fn, wait = 200) => {
    let t = 0;
    return (...args) => {
      const now = Date.now();
      if (now - t > wait) {
        t = now;
        fn(...args);
      }
    };
  };

  const downloadText = (filename, text) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  const toCSV = (rows) => {
    if (!rows || !rows.length) return '';
    const headers = Object.keys(rows[0]);
    const esc = (s) => {
      const v = String(s ?? '');
      return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
    };
    const head = headers.map(esc).join(',');
    const body = rows.map(r => headers.map(h => esc(r[h])).join(',')).join('\n');
    return `${head}\n${body}`;
  };

  const last = (arr, n) => (n ? arr.slice(-n) : arr[arr.length - 1]);

  /* -----------------------------
   * Dashboard 页面逻辑
   * ----------------------------- */
  async function initDashboard() {
    const state = {
      refreshMs: 5 * 60 * 1000, // 5分钟刷新
      rows: [],
      chart: null,
      fallbackCanvas: null,
      fallbackCtx: null,
    };

    // 优先使用模板注入数据：在 dashboard.html 里可以放：
    // <script>window.__LINESCOPE_DATA__ = {{ data_json|safe }}</script>
    const preload = window.__LINESCOPE_DATA__;
    if (Array.isArray(preload) && preload.length) {
      state.rows = preload;
      renderAll(state);
    } else {
      // 首次拉取
      await fetchAndRender(state);
    }

    // 自动刷新
    setInterval(() => fetchAndRender(state), state.refreshMs);

    // 交互按钮
    const btnRefresh = $('#btn-refresh');
    const btnDownload = $('#btn-download');
    const btnReset = $('#btn-reset');
    if (btnRefresh) btnRefresh.addEventListener('click', () => fetchAndRender(state));
    if (btnDownload) btnDownload.addEventListener('click', () => {
      const csv = toCSV(state.rows);
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      downloadText(`sensor-data-${ts}.csv`, csv);
    });
    if (btnReset) btnReset.addEventListener('click', () => renderTable(state.rows, { resetScroll: true }));

    // 表格内横向滚动时吸顶表头（移动端友好）
    const tblWrap = $('.table-wrap');
    if (tblWrap) {
      tblWrap.addEventListener('scroll', throttle(() => {
        const ths = $$$('thead th', $('.table', tblWrap));
        ths.forEach(th => th.style.transform = `translateX(${tblWrap.scrollLeft}px)`);
      }, 16));
    }
  }

  async function fetchAndRender(state) {
    const loader = $('#last-updated');
    if (loader) loader.textContent = 'Loading...';
    try {
      const res = await fetch('/api/sensor-data', { cache: 'no-store' });
      const data = await res.json();
      if (Array.isArray(data)) {
        state.rows = data;
        renderAll(state);
      }
      if (loader) loader.textContent = `Updated at ${new Date().toLocaleString()}`;
    } catch (e) {
      if (loader) loader.textContent = 'Failed to update';
      console.error(e);
    }
  }

  function renderAll(state) {
    renderStats(state.rows);
    renderTable(state.rows);
    renderChart(state);
  }

  function renderStats(rows) {
    if (!rows || !rows.length) return;
    const numFields = ['sway_speed_dps', 'temperature_C', 'humidity_RH', 'pressure_hPa', 'lux'];
    const stats = {};
    numFields.forEach(k => {
      const vs = rows.map(r => +r[k]).filter(v => Number.isFinite(v));
      const sum = vs.reduce((a, b) => a + b, 0);
      stats[k] = {
        min: Math.min(...vs),
        max: Math.max(...vs),
        avg: vs.length ? sum / vs.length : NaN,
        latest: vs.length ? vs[vs.length - 1] : NaN,
      };
    });
    // 显示到页面（可在 dashboard.html 放这些元素）
    setText('#stats-sway-min', fmtNum(stats.sway_speed_dps?.min));
    setText('#stats-sway-max', fmtNum(stats.sway_speed_dps?.max));
    setText('#stats-sway-avg', fmtNum(stats.sway_speed_dps?.avg));
    setText('#stats-sway-latest', fmtNum(stats.sway_speed_dps?.latest));

    setText('#stats-temp-min', fmtNum(stats.temperature_C?.min));
    setText('#stats-temp-max', fmtNum(stats.temperature_C?.max));
    setText('#stats-temp-avg', fmtNum(stats.temperature_C?.avg));
    setText('#stats-temp-latest', fmtNum(stats.temperature_C?.latest));

    setText('#stats-humid-avg', fmtNum(stats.humidity_RH?.avg));
    setText('#stats-press-avg', fmtNum(stats.pressure_hPa?.avg));
    setText('#stats-lux-avg', fmtNum(stats.lux?.avg));
  }

  function setText(sel, text) {
    const el = $$(sel);
    if (el) el.textContent = text;
  }

  function renderTable(rows, opts = {}) {
    const table = $('#sensor-table');
    const tbody = $('#sensor-tbody');
    if (!table || !tbody) return;

    // 渲染所有行（考虑到 672 行，直接一次性 innerHTML 即可）
    const html = rows.map(r => {
      // 可在此加入异常高亮：如 sway_speed_dps > 阈值
      const alert = Number(r.sway_speed_dps) > 60 ? ' row-alert' : '';
      return `
        <tr class="${alert}">
          <td>${r.timestamp_Beijing}</td>
          <td class="text-right">${fmtNum(r.sway_speed_dps)}</td>
          <td class="text-right">${fmtNum(r.temperature_C)}</td>
          <td class="text-right">${fmtNum(r.humidity_RH)}</td>
          <td class="text-right">${fmtNum(r.pressure_hPa)}</td>
          <td class="text-right">${fmtNum(r.lux)}</td>
        </tr>
      `;
    }).join('');
    tbody.innerHTML = html;

    if (opts.resetScroll) {
      const wrap = $('.table-wrap');
      if (wrap) wrap.scrollTo({ left: 0, top: 0, behavior: 'smooth' });
    }
  }

  function renderChart(state) {
    const labels = state.rows.map(r => r.timestamp_Beijing);
    const sway = state.rows.map(r => +r.sway_speed_dps);
    const temp = state.rows.map(r => +r.temperature_C);
    const humid = state.rows.map(r => +r.humidity_RH);

    const canvasEl = $('#chart1');
    if (!canvasEl) return;

    // 优先使用 Chart.js
    if (window.Chart) {
      if (state.chart) {
        // 更新数据
        state.chart.data.labels = labels;
        state.chart.data.datasets[0].data = sway;
        state.chart.data.datasets[1].data = temp;
        state.chart.data.datasets[2].data = humid;
        state.chart.update('none');
      } else {
        const ctx = canvasEl.getContext('2d');
        state.chart = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets: [
              {
                label: 'Sway (°/s)',
                data: sway,
                borderWidth: 2,
                tension: 0.25,
                pointRadius: 0,
                yAxisID: 'y',
              },
              {
                label: 'Temp (°C)',
                data: temp,
                borderWidth: 2,
                tension: 0.25,
                pointRadius: 0,
                yAxisID: 'y1',
              },
              {
                label: 'Humidity (%RH)',
                data: humid,
                borderWidth: 1,
                borderDash: [4, 4],
                tension: 0.25,
                pointRadius: 0,
                yAxisID: 'y2',
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: { display: true },
              tooltip: {
                callbacks: {
                  title: (items) => {
                    const i = items[0]?.dataIndex ?? 0;
                    return labels[i] || '';
                  },
                },
              },
            },
            scales: {
              x: {
                ticks: { maxTicksLimit: 8 },
                grid: { display: false },
              },
              y: {
                position: 'left',
                title: { display: true, text: '°/s' },
                grid: { drawBorder: false },
              },
              y1: {
                position: 'right',
                title: { display: true, text: '°C' },
                grid: { drawOnChartArea: false, drawBorder: false },
              },
              y2: {
                position: 'right',
                display: false,
              },
            },
          },
        });
      }
      return;
    }

    // 无 Chart.js 时，使用最简 Canvas 兜底折线
    if (!state.fallbackCanvas) {
      state.fallbackCanvas = canvasEl;
      state.fallbackCtx = canvasEl.getContext('2d');
      // 让 Canvas 匹配容器大小（简单处理）
      const parent = canvasEl.parentElement;
      const w = parent?.clientWidth || 800;
      const h = parent?.clientHeight || 300;
      canvasEl.width = w * devicePixelRatio;
      canvasEl.height = h * devicePixelRatio;
      canvasEl.style.width = w + 'px';
      canvasEl.style.height = h + 'px';
    }
    drawTinyLines(state.fallbackCtx, state.fallbackCanvas, [
      { data: sway, title: '°/s' },
      { data: temp, title: '°C' },
    ]);
  }

  function drawTinyLines(ctx, canvas, seriesList) {
    if (!ctx || !canvas) return;
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // 坐标系留边
    const padL = 60 * devicePixelRatio;
    const padR = 20 * devicePixelRatio;
    const padT = 20 * devicePixelRatio;
    const padB = 30 * devicePixelRatio;

    // 网格
    ctx.save();
    ctx.strokeStyle = 'rgba(128,128,128,0.2)';
    ctx.lineWidth = 1 * devicePixelRatio;
    const gridCount = 5;
    for (let i = 0; i <= gridCount; i++) {
      const y = padT + (H - padT - padB) * (i / gridCount);
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(W - padR, y);
      ctx.stroke();
    }
    ctx.restore();

    // 每条数据单独归一化
    seriesList.forEach((s, idx) => {
      const xs = s.data;
      if (!xs || xs.length < 2) return;
      const min = Math.min(...xs.filter(Number.isFinite));
      const max = Math.max(...xs.filter(Number.isFinite));
      const span = (max - min) || 1;
      const n = xs.length;

      ctx.save();
      ctx.lineWidth = (idx === 0 ? 2 : 1) * devicePixelRatio;
      // 不指定颜色，保持浏览器默认（与项目“不要指定颜色”的设计一致）
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const x = padL + (W - padL - padR) * (i / (n - 1));
        const y = padT + (H - padT - padB) * (1 - (xs[i] - min) / span);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.restore();

      // 轴标题
      ctx.save();
      ctx.fillStyle = 'currentColor';
      ctx.font = `${12 * devicePixelRatio}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
      ctx.fillText(s.title, 8 * devicePixelRatio, (padT + 14 * devicePixelRatio) + idx * (16 * devicePixelRatio));
      ctx.restore();
    });
  }

  /* -----------------------------
   * Result 页面逻辑（MJPEG在线状态）
   * ----------------------------- */
  function initResultPage() {
    const img = $('.stream-container img') || $('#streamImg');
    const dot = $('.stream-status .dot');
    const statusText = $('.stream-status');

    const setStatus = (ok) => {
      if (!dot || !statusText) return;
      if (ok) {
        dot.style.background = 'var(--accent)';
        statusText.lastChild && (statusText.lastChild.nodeType === 3)
          ? (statusText.lastChild.textContent = ' Streaming')
          : (statusText.textContent = 'Streaming');
        dot.style.animationPlayState = 'running';
      } else {
        dot.style.background = 'var(--danger)';
        dot.style.animationPlayState = 'paused';
        statusText.lastChild && (statusText.lastChild.nodeType === 3)
          ? (statusText.lastChild.textContent = ' Reconnecting...')
          : (statusText.textContent = 'Reconnecting...');
      }
    };

    if (img) {
      img.addEventListener('load', () => setStatus(true));
      img.addEventListener('error', () => setStatus(false));
    }

    // 周期探测后端健康；若断线尝试重载图片
    setInterval(async () => {
      try {
        const r = await fetch('/healthz', { cache: 'no-store' });
        if (r.ok) {
          setStatus(true);
          // 如果 <img> 的 src 被浏览器断开，重新指向以触发连接
          if (img && (!img.complete || img.naturalWidth === 0)) {
            const url = img.getAttribute('src');
            img.setAttribute('src', url.includes('?') ? url + '&ts=' + Date.now() : url + '?ts=' + Date.now());
          }
        } else {
          setStatus(false);
        }
      } catch (e) {
        setStatus(false);
      }
    }, 15000);
  }

  /* -----------------------------
   * 启动
   * ----------------------------- */
  document.addEventListener('DOMContentLoaded', () => {
    if (isDashboard) initDashboard();
    if (isResult) initResultPage();
  });

  /* -----------------------------
   * DOM 快捷选择器
   * ----------------------------- */
  function $(sel, root = document) { return root.querySelector(sel); }

})();
