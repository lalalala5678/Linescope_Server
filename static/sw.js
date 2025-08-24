/**
 * Linescope Server Service Worker
 * 提供智能缓存策略和离线支持
 * 版本: 1.0.0
 */

const CACHE_VERSION = 'v1.0.0';
const STATIC_CACHE = `linescope-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `linescope-dynamic-${CACHE_VERSION}`;
const API_CACHE = `linescope-api-${CACHE_VERSION}`;

// 需要预缓存的静态资源
const STATIC_ASSETS = [
  '/',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/js/utils.js',
  '/static/js/api.js',
  '/static/js/charts.js',
  '/static/favicon.ico',
  // 外部库 CDN 资源
  'https://cdn.tailwindcss.com/3.3.0',
  'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js',
  'https://unpkg.com/ag-grid-community@30.0.6/dist/styles/ag-grid.css',
  'https://unpkg.com/ag-grid-community@30.0.6/dist/styles/ag-theme-alpine-dark.css',
  'https://unpkg.com/ag-grid-community@30.0.6/dist/ag-grid-community.min.js'
];

// API 端点缓存配置
const API_CACHE_CONFIG = {
  '/api/sensor-data': { maxAge: 5 * 60 * 1000 }, // 5 分钟
  '/api/sensors/latest': { maxAge: 30 * 1000 },   // 30 秒
  '/api/sensors': { maxAge: 2 * 60 * 1000 }       // 2 分钟
};

/**
 * Service Worker 安装事件
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Precaching static assets...');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((error) => {
        console.error('[SW] Precaching failed:', error);
      })
  );
  
  // 强制激活新的 Service Worker
  self.skipWaiting();
});

/**
 * Service Worker 激活事件
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // 删除旧版本的缓存
              return cacheName.includes('linescope') && !cacheName.includes(CACHE_VERSION);
            })
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service Worker activated');
        return self.clients.claim();
      })
  );
});

/**
 * 网络请求拦截处理
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // 只处理同源请求和指定的 CDN 资源
  if (url.origin !== location.origin && !isCdnResource(url.href)) {
    return;
  }
  
  if (request.method !== 'GET') {
    return;
  }
  
  // 根据请求类型选择缓存策略
  if (isApiRequest(url.pathname)) {
    event.respondWith(handleApiRequest(request));
  } else if (isStaticAsset(url.pathname)) {
    event.respondWith(handleStaticAsset(request));
  } else if (isPageRequest(url.pathname)) {
    event.respondWith(handlePageRequest(request));
  } else {
    event.respondWith(handleOtherRequest(request));
  }
});

/**
 * 处理 API 请求 - Stale While Revalidate 策略
 */
async function handleApiRequest(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  const cacheConfig = API_CACHE_CONFIG[pathname] || { maxAge: 5 * 60 * 1000 };
  
  try {
    const cache = await caches.open(API_CACHE);
    const cachedResponse = await cache.match(request);
    
    // 检查缓存是否过期
    if (cachedResponse) {
      const cachedTime = new Date(cachedResponse.headers.get('sw-cached-time'));
      const now = new Date();
      
      if (now - cachedTime < cacheConfig.maxAge) {
        console.log('[SW] Serving fresh cached API response:', pathname);
        
        // 后台更新缓存
        fetchAndCache(request, cache);
        
        return cachedResponse;
      }
    }
    
    console.log('[SW] Fetching fresh API response:', pathname);
    const response = await fetch(request);
    
    if (response.ok) {
      await cacheApiResponse(cache, request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.error('[SW] API request failed:', error);
    
    // 网络错误时返回缓存的响应（即使过期）
    const cache = await caches.open(API_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      console.log('[SW] Serving stale cached response due to network error');
      return cachedResponse;
    }
    
    // 返回离线页面或错误响应
    return new Response(
      JSON.stringify({ error: 'Network unavailable', offline: true }),
      { 
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * 处理静态资源 - Cache First 策略
 */
async function handleStaticAsset(request) {
  try {
    const cache = await caches.open(STATIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      console.log('[SW] Serving cached static asset:', request.url);
      return cachedResponse;
    }
    
    console.log('[SW] Fetching static asset:', request.url);
    const response = await fetch(request);
    
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.error('[SW] Static asset request failed:', error);
    return new Response('Resource unavailable', { status: 503 });
  }
}

/**
 * 处理页面请求 - Network First 策略
 */
async function handlePageRequest(request) {
  try {
    console.log('[SW] Fetching page:', request.url);
    const response = await fetch(request);
    
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.error('[SW] Page request failed:', error);
    
    // 返回缓存的页面
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      console.log('[SW] Serving cached page due to network error');
      return cachedResponse;
    }
    
    // 返回离线页面
    return new Response(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Linescope - Offline</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body { font-family: system-ui; text-align: center; padding: 50px; }
            .offline { color: #666; }
          </style>
        </head>
        <body>
          <h1>Linescope Server</h1>
          <p class="offline">您当前处于离线状态</p>
          <p>请检查网络连接后刷新页面</p>
        </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

/**
 * 处理其他请求 - Network Only
 */
async function handleOtherRequest(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.error('[SW] Other request failed:', error);
    return new Response('Request failed', { status: 503 });
  }
}

/**
 * 缓存 API 响应并添加时间戳
 */
async function cacheApiResponse(cache, request, response) {
  const responseWithTimestamp = new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: {
      ...response.headers,
      'sw-cached-time': new Date().toISOString()
    }
  });
  
  await cache.put(request, responseWithTimestamp);
}

/**
 * 后台获取并缓存
 */
async function fetchAndCache(request, cache) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      await cacheApiResponse(cache, request, response.clone());
    }
  } catch (error) {
    console.warn('[SW] Background fetch failed:', error);
  }
}

/**
 * 判断是否为 API 请求
 */
function isApiRequest(pathname) {
  return pathname.startsWith('/api/');
}

/**
 * 判断是否为静态资源
 */
function isStaticAsset(pathname) {
  return pathname.startsWith('/static/') || 
         pathname === '/favicon.ico' ||
         pathname.endsWith('.css') ||
         pathname.endsWith('.js') ||
         pathname.endsWith('.jpg') ||
         pathname.endsWith('.png') ||
         pathname.endsWith('.webp') ||
         pathname.endsWith('.svg');
}

/**
 * 判断是否为页面请求
 */
function isPageRequest(pathname) {
  return pathname === '/' || 
         pathname === '/dashboard' || 
         pathname === '/result' ||
         pathname.startsWith('/dashboard') ||
         pathname.startsWith('/result');
}

/**
 * 判断是否为 CDN 资源
 */
function isCdnResource(url) {
  const cdnHosts = [
    'cdn.tailwindcss.com',
    'cdn.jsdelivr.net',
    'unpkg.com',
    'fonts.googleapis.com',
    'fonts.gstatic.com'
  ];
  
  return cdnHosts.some(host => url.includes(host));
}

/**
 * 消息处理 - 支持缓存管理命令
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
      
    case 'CACHE_STATUS':
      getCacheStatus().then((status) => {
        event.ports[0].postMessage(status);
      });
      break;
      
    default:
      console.log('[SW] Unknown message type:', type);
  }
});

/**
 * 清空所有缓存
 */
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames
      .filter(name => name.includes('linescope'))
      .map(name => caches.delete(name))
  );
  console.log('[SW] All caches cleared');
}

/**
 * 获取缓存状态
 */
async function getCacheStatus() {
  const cacheNames = await caches.keys();
  const status = {};
  
  for (const cacheName of cacheNames.filter(name => name.includes('linescope'))) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    status[cacheName] = keys.length;
  }
  
  return status;
}

console.log('[SW] Service Worker loaded successfully');