/* =========================================================
 * Linescope Server - static/js/script.js
 * 多图：晃动速度、温度、湿度、气压、光照各一张图
 * Chart.js 可选；无则自动使用 Canvas 兜底
 * ========================================================= */

(() => {
  const isDashboard =
    !!document.querySelector('#dashboard-root') ||
    !!document.querySelector('#chart-sway') ||
    !!document.querySelector('#sensor-table');
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

  /* -----------------------------
   * Dashboard 页面逻辑
   * ----------------------------- */
  async function initDashboard() {
    const state = {
      refreshMs: 5 * 60 * 1000, // 5分钟刷新
      rows: [],
      charts: {},          // {id: ChartInstance}
      fallbackCtxs: {},    // {id: CanvasRenderingContext2D}
      fallbackSized: {},   // {id: boolean}
    };

    const preload = window.__LINESCOPE_DATA__;
    if (Array.isArray(preload) && preload.length) {
      state.rows = preload;
      renderAll(state);
    } else {
      await fetchAndRender(state);
    }

    setInterval(() => fetchAndRender(state), state.refreshMs);

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
    renderCharts(state);   // ★ 改成多图渲染
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

    const html = rows.map(r => {
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

  /* -----------------------------
   * 多图渲染
   * ----------------------------- */
  function renderCharts(state) {
    const rows = state.rows || [];
    const labels = rows.map(r => r.timestamp_Beijing);

    const series = {
      'chart-sway':  { label: 'Sway (°/s)',     data: rows.map(r => +r.sway_speed_dps), yTitle: '°/s' },
      'chart-temp':  { label: 'Temp (°C)',      data: rows.map(r => +r.temperature_C), yTitle: '°C' },
      'chart-humid': { label: 'Humidity (%RH)', data: rows.map(r => +r.humidity_RH),   yTitle: '%RH' },
      'chart-press': { label: 'Pressure (hPa)', data: rows.map(r => +r.pressure_hPa),  yTitle: 'hPa' },
      'chart-lux':   { label: 'Lux',            data: rows.map(r => +r.lux),           yTitle: 'Lux' },
    };

    // 优先 Chart.js
    if (window.Chart) {
      Object.entries(series).forEach(([id, conf]) => {
        const canvas = $(`#${id}`);
        if (!canvas) return;

        if (state.charts[id]) {
          const ch = state.charts[id];
          ch.data.labels = labels;
          ch.data.datasets[0].data = conf.data;
          ch.update('none');
        } else {
          const ctx = canvas.getContext('2d');
          state.charts[id] = new Chart(ctx, {
            type: 'line',
            data: {
              labels,
              datasets: [{
                label: conf.label,
                data: conf.data,
                borderWidth: 2,
                tension: 0.25,
                pointRadius: 0
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              interaction: { mode: 'index', intersect: false },
              plugins: { legend: { display: true } },
              scales: {
                x: { ticks: { maxTicksLimit: 8 }, grid: { display: false } },
                y: {
                  position: 'left',
                  title: { display: true, text: conf.yTitle },
                  grid: { drawBorder: false }
                }
              }
            }
          });
        }
      });
      return;
    }

    // 无 Chart.js：使用 Canvas 兜底
    Object.entries(series).forEach(([id, conf]) => {
      const canvas = $(`#${id}`);
      if (!canvas) return;

      // 首次时设置尺寸匹配容器
      if (!state.fallbackSized[id]) {
        const parent = canvas.parentElement;
        const w = parent?.clientWidth || 800;
        const h = parent?.clientHeight || 300;
        canvas.width = w * devicePixelRatio;
        canvas.height = h * devicePixelRatio;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        state.fallbackSized[id] = true;
      }
      const ctx = state.fallbackCtxs[id] || canvas.getContext('2d');
      state.fallbackCtxs[id] = ctx;
      drawSingleLine(ctx, canvas, labels, conf.data, conf.yTitle);
    });
  }

  function drawSingleLine(ctx, canvas, labels, data, yTitle) {
    if (!ctx || !canvas) return;
    const W = canvas.width, H = canvas.height;

    ctx.clearRect(0, 0, W, H);

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

    // 归一化
    const vals = data.filter(Number.isFinite);
    if (vals.length < 2) return;
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const span = (max - min) || 1;
    const n = data.length;

    // 折线
    ctx.save();
    ctx.lineWidth = 2 * devicePixelRatio;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const v = data[i];
      const x = padL + (W - padL - padR) * (i / Math.max(1, n - 1));
      const y = padT + (H - padT - padB) * (1 - ((v - min) / span));
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();

    // 轴标题
    ctx.save();
    ctx.fillStyle = 'currentColor';
    ctx.font = `${12 * devicePixelRatio}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
    ctx.fillText(yTitle, 8 * devicePixelRatio, padT + 14 * devicePixelRatio);
    ctx.restore();
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

    setInterval(async () => {
      try {
        const r = await fetch('/healthz', { cache: 'no-store' });
        if (r.ok) {
          setStatus(true);
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

  function $(sel, root = document) { return root.querySelector(sel); }
})();
