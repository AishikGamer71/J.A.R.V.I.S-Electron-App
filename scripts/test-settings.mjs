import http from 'http';
import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distDir = path.resolve(__dirname, '..', 'dist');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf'
};

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/') reqPath = '/index.html';
  const filePath = path.join(distDir, reqPath.replace(/^\//, ''));
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
    fs.createReadStream(filePath).pipe(res);
  } else {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    fs.createReadStream(path.join(distDir, 'index.html')).pipe(res);
  }
});

server.listen(5499, async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  
  page.on('console', (msg) => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', (err) => console.error('PAGE ERROR:', err.stack || err.message));

  await page.addInitScript(() => {
    window.alert = () => {};
    window.confirm = () => true;
    window.WebSocket = class {
      constructor() { this.readyState = 1; setTimeout(() => this.onopen && this.onopen({}), 10); }
      send() {}
      close() {}
      addEventListener() {}
      removeEventListener() {}
    };
    window.electron = {
      ipcRenderer: {
        on: () => {},
        off: () => {},
        addListener: () => {},
        removeListener: () => {},
        removeAllListeners: () => {},
        send: () => {},
        invoke: async () => ({})
      }
    };
    window.hermesDesktop = {
      isAvailable: true,
      getConnection: async () => ({ baseUrl: 'http://127.0.0.1:8765', token: 'mock-token' }),
      getGatewayWsUrl: async () => ({ ok: true, wsUrl: 'ws://127.0.0.1:8765/api/ws' }),
      getStatus: async () => ({ status: 'ready', model: 'hermes-3-llama-3.1-8b' }),
      api: async () => ([])
    };
  });

  await page.goto('http://127.0.0.1:5499', { waitUntil: 'load' });
  await page.waitForTimeout(1000);
  
  console.log('Clicking SETTINGS...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const btn = buttons.find(b => b.textContent && b.textContent.includes('SETTINGS'));
    if (btn) btn.click();
  });

  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'showcase_screenshots/test_settings.png' });
  console.log('Saved showcase_screenshots/test_settings.png');

  await browser.close();
  server.close();
  process.exit(0);
});
