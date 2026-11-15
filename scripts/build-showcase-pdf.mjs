import http from 'http';
import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const distDir = path.resolve(projectRoot, 'dist');
const screenshotsDir = path.resolve(projectRoot, 'showcase_screenshots');
const outputPdfPath = path.resolve(projectRoot, 'JARVIS_AI_Prototype_Showcase.pdf');
const brainPdfPath = 'C:\\Users\\utpal\\.gemini\\antigravity\\brain\\a85841db-a58b-4f53-8f61-6d53f332ea24\\JARVIS_AI_Prototype_Showcase.pdf';

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

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

function startStaticServer(port = 5480) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      let reqPath = req.url.split('?')[0];
      if (reqPath === '/') reqPath = '/index.html';
      
      const filePath = path.join(distDir, reqPath.replace(/^\//, ''));
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const ext = path.extname(filePath).toLowerCase();
        const contentType = MIME_TYPES[ext] || 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': contentType, 'Access-Control-Allow-Origin': '*' });
        fs.createReadStream(filePath).pipe(res);
      } else {
        const indexPath = path.join(distDir, 'index.html');
        if (fs.existsSync(indexPath)) {
          res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
          fs.createReadStream(indexPath).pipe(res);
        } else {
          res.writeHead(404);
          res.end('Not found');
        }
      }
    });

    server.on('error', reject);
    server.listen(port, '127.0.0.1', () => {
      resolve({
        port,
        url: `http://127.0.0.1:${port}`,
        close: () => new Promise((res) => server.close(res))
      });
    });
  });
}

const modulesToCapture = [
  {
    id: 'DASHBOARD',
    name: '01_Particle_HUD_Dashboard',
    title: 'Futuristic 3D Particle HUD Dashboard',
    desc: 'Interactive 3D particle neural interface, live system telemetry (CPU Load, RAM Usage, Temperature, OS Uptime), voice state indicators, and real-time audio visualizer.'
  },
  {
    id: 'CHAT',
    name: '02_Neural_Chat_Interface',
    title: 'Autonomous Multi-Model AI Chat & Workspace',
    desc: 'Interactive AI conversational environment featuring multi-tier routing (Ollama, Gemini, Claude, OpenAI), persistent session memory, and autonomous skill execution.'
  },
  {
    id: 'MODULES',
    name: '03_System_Autonomous_Modules',
    title: 'Neural Automation & Capability Modules',
    desc: 'Registry of pre-built autonomous agent skills for vocal synthesis, speech transcription, translation, and scheduled background routines.'
  },
  {
    id: 'TASK MANAGER',
    name: '04_Live_System_Task_Manager',
    title: 'System Diagnostics & Real-Time Process Monitor',
    desc: 'Live hardware utilization charts, active background process hierarchy, memory consumption metrics, and task supervisor.'
  },
  {
    id: 'Apps',
    name: '05_AI_App_Store_Plugins',
    title: 'Integrated AI App Store & Plugin Hub',
    desc: 'Extensible ecosystem of productivity tools, developer plugins, and custom integrations with one-click activation.'
  },
  {
    id: 'NOTES',
    name: '06_Quick_Notes_Workspace',
    title: 'Persistent Scratchpad & Quick Notes',
    desc: 'Local-first markdown scratchpad and note-taking tool linked with persistent agent memory bank.'
  },
  {
    id: 'GALLERY',
    name: '07_Media_Vision_Gallery',
    title: 'Media, Vision & Image Generation Hub',
    desc: 'Visual assets manager showcasing camera inputs, desktop screen captures, and multi-modal AI generation results.'
  },
  {
    id: 'TERMINAL',
    name: '08_Integrated_Terminal_Console',
    title: 'Direct System Terminal & Neural CLI',
    desc: 'Built-in developer terminal powered by xterm and native shell integration for executing commands and agent scripts.'
  },
  {
    id: 'PHONE',
    name: '09_Neural_Comms_Phone_Bridge',
    title: 'Neural Communications & Device Bridge',
    desc: 'Device integration and ADB bridge for remote device control, notifications, and mobile telemetry.'
  },
  {
    id: 'SETTINGS',
    name: '10_Command_Center_Settings_Vault',
    title: 'Command Center Vault & Model Settings',
    desc: 'Security-hardened credential vault, custom voice selection (Piper TTS / Whisper STT), theme customizations, and multi-LLM API configuration.'
  }
];

async function captureAndGeneratePdf() {
  console.log('🚀 Starting built-in static server for dist/...');
  const server = await startStaticServer(5480);
  console.log(`✅ Static server running at: ${server.url}`);

  console.log('🌐 Launching Playwright browser...');
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2
  });

  const page = await context.newPage();

  // Comprehensive mock setup
  await page.addInitScript(() => {
    window.alert = () => {};
    window.confirm = () => true;

    localStorage.setItem('GEMINI_API_KEY', 'mock-valid-gemini-key');
    localStorage.setItem('OPENAI_API_KEY', 'mock-valid-openai-key');
    localStorage.setItem('ANTHROPIC_API_KEY', 'mock-valid-claude-key');
    localStorage.setItem('jarvis_user_name', 'Oishik');
    localStorage.setItem('jarvis_theme', JSON.stringify({ primaryColor: '#10b981', name: 'Emerald' }));

    const listeners = {};

    window.WebSocket = class MockWebSocket {
      constructor(url) {
        this.url = url;
        this.readyState = 1;
        setTimeout(() => {
          if (this.onopen) this.onopen({ type: 'open' });
        }, 50);
      }
      send(data) {}
      close() {
        this.readyState = 3;
        if (this.onclose) this.onclose({ type: 'close' });
      }
      addEventListener(event, fn) {
        if (event === 'open') setTimeout(() => fn({ type: 'open' }), 50);
      }
      removeEventListener() {}
    };

    window.electron = {
      ipcRenderer: {
        on: (event, handler) => {
          if (!listeners[event]) listeners[event] = [];
          listeners[event].push(handler);
        },
        off: (event, handler) => {
          if (listeners[event]) {
            listeners[event] = listeners[event].filter(h => h !== handler);
          }
        },
        addListener: (event, handler) => {
          if (!listeners[event]) listeners[event] = [];
          listeners[event].push(handler);
        },
        removeListener: (event, handler) => {
          if (listeners[event]) {
            listeners[event] = listeners[event].filter(h => h !== handler);
          }
        },
        removeAllListeners: (event) => {
          if (event) delete listeners[event];
          else Object.keys(listeners).forEach(k => delete listeners[k]);
        },
        send: (event, payload) => {
          if (event === 'terminal-spawn') {
            setTimeout(() => {
              if (listeners['terminal-output']) {
                listeners['terminal-output'].forEach(h => {
                  h(null, {
                    tabId: payload?.tabId || 'tab-1',
                    data: 'Microsoft Windows [Version 10.0.26100.3194]\r\n(c) Microsoft Corporation. All rights reserved.\r\n\r\nE:\\Projects\\J.A.R.V.I.S Electron App> '
                  });
                });
              }
            }, 100);
          }
        },
        invoke: async (channel, ...args) => {
          if (channel === 'get-system-stats') {
            return {
              cpu: '14.2',
              memory: {
                total: '16.0 GB',
                free: '9.8 GB',
                usedPercentage: '38'
              },
              temperature: 42,
              os: {
                type: 'Windows 11 Pro',
                uptime: '5h 24m'
              }
            };
          }
          if (channel === 'get-system-load') {
            return {
              success: true,
              cpu: '14.2',
              memory: '38.5',
              memoryUsedGb: '6.1',
              memoryTotalGb: '16.0'
            };
          }
          if (channel === 'get-processes') {
            return {
              success: true,
              processes: [
                { name: 'JARVIS Neural Core', pid: 10420, cpu: 8.4, mem: 412.5, user: 'SYSTEM', path: 'C:\\JARVIS\\core.exe', children: [{ pid: 10420, cpu: 8.4, mem: 412.5, user: 'SYSTEM' }] },
                { name: 'Hermes Agent Engine', pid: 8432, cpu: 4.1, mem: 620.0, user: 'OISHIK', path: 'C:\\hermes\\hermes.exe', children: [{ pid: 8432, cpu: 4.1, mem: 620.0, user: 'OISHIK' }] },
                { name: 'Faster-Whisper STT', pid: 14210, cpu: 1.2, mem: 340.0, user: 'SYSTEM', path: 'C:\\JARVIS\\services\\whisper.exe', children: [{ pid: 14210, cpu: 1.2, mem: 340.0, user: 'SYSTEM' }] },
                { name: 'Piper Neural TTS', pid: 16890, cpu: 0.5, mem: 180.2, user: 'SYSTEM', path: 'C:\\JARVIS\\services\\piper.exe', children: [{ pid: 16890, cpu: 0.5, mem: 180.2, user: 'SYSTEM' }] },
                { name: 'ThreeJS Particle HUD', pid: 19440, cpu: 2.8, mem: 290.4, user: 'OISHIK', path: 'C:\\JARVIS\\render.exe', children: [{ pid: 19440, cpu: 2.8, mem: 290.4, user: 'OISHIK' }] },
                { name: 'Ollama Local LLM Router', pid: 5120, cpu: 0.0, mem: 1840.0, user: 'SYSTEM', path: 'C:\\ollama\\ollama.exe', children: [{ pid: 5120, cpu: 0.0, mem: 1840.0, user: 'SYSTEM' }] }
              ]
            };
          }
          if (channel === 'get-personality') {
            return 'You are J.A.R.V.I.S., an advanced autonomous AI operating system designed to assist with computation, real-time telemetry, terminal tasks, and system automation.';
          }
          if (channel === 'get-notes') {
            return [
              {
                filename: 'notes-01.md',
                title: 'System Architecture & Telemetry',
                content: '# System Architecture\n\n- Multi-tier LLM Routing active\n- Piper Neural Voice & Faster-Whisper ready\n- Local autonomous tool execution initialized.',
                createdAt: new Date()
              },
              {
                filename: 'notes-02.md',
                title: 'Autonomous Agent Schedule',
                content: '# Autonomous Schedule\n\n- 04:00: Diagnostic health check\n- 12:00: Telemetry snapshot sync\n- Continuous real-time voice wake-word detection.',
                createdAt: new Date()
              }
            ];
          }
          if (channel === 'get-gallery') {
            return [
              {
                filename: 'neural-hud.png',
                displayName: 'Neural 3D HUD Sphere',
                path: 'C:\\assets\\neural-hud.png',
                url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect width="100%" height="100%" fill="%23050505"/><circle cx="200" cy="150" r="80" stroke="%2310b981" stroke-width="3" fill="none"/><circle cx="200" cy="150" r="40" stroke="%2306b6d4" stroke-width="2" fill="none"/><text x="50%" y="50%" text-anchor="middle" fill="%2310b981" font-size="14" font-family="monospace" dy=".3em">NEURAL HUD</text></svg>',
                createdAt: new Date()
              }
            ];
          }
          if (channel === 'get-chat-history') {
            return [
              { role: 'user', parts: [{ text: 'JARVIS, initialize all sub-systems and report diagnostics.' }] },
              { role: 'model', parts: [{ text: 'All neural systems online. 3D Particle HUD active, faster-whisper voice engine connected, local Ollama router ready, and system telemetry nominal.' }] }
            ];
          }
          if (channel === 'adb-get-history') {
            return [
              { ip: '192.168.1.105', port: '5555', deviceName: 'Galaxy S24 Ultra (Android 14)', model: 'Galaxy S24 Ultra', connectedAt: 'Today, 18:30' }
            ];
          }
          if (channel === 'adb-telemetry') {
            return {
              success: true,
              data: {
                model: 'Galaxy S24 Ultra',
                os: 'Android 14 (One UI 6.1)',
                battery: { level: 88, isCharging: false, temp: '32.4' },
                storage: { used: '128 GB', total: '512 GB TOTAL', percent: 25 }
              }
            };
          }
          if (channel === 'adb-connect') {
            return { success: true };
          }
          if (channel === 'get-installed-apps') {
            return [
              { id: '1', name: 'Visual Studio Code' },
              { id: '2', name: 'Google Chrome' },
              { id: '3', name: 'Terminal' },
              { id: '4', name: 'Spotify' },
              { id: '5', name: 'Discord' }
            ];
          }
          if (channel === 'get-drives') {
            return [
              { fs: 'C:', size: 1024 * 1024 * 1024 * 512, used: 1024 * 1024 * 1024 * 210, use: 41 },
              { fs: 'E:', size: 1024 * 1024 * 1024 * 1024, used: 1024 * 1024 * 1024 * 380, use: 37 }
            ];
          }
          return { success: true };
        }
      }
    };

    window.hermesDesktop = {
      isAvailable: true,
      getConnection: async () => ({ baseUrl: 'http://127.0.0.1:8765', token: 'mock-token' }),
      getGatewayWsUrl: async () => ({ ok: true, wsUrl: 'ws://127.0.0.1:8765/api/ws' }),
      getStatus: async () => ({ status: 'ready', model: 'hermes-3-llama-3.1-8b' }),
      api: async ({ path, method }) => {
        if (path === '/api/memory') {
          return [
            { id: 1, content: 'User preferred persona: J.A.R.V.I.S Autonomous Assistant' },
            { id: 2, content: 'Default Local Model: Hermes-3 LLaMA 3.1 8B (Ollama)' }
          ];
        }
        if (path && path.includes('/sessions')) {
          return [
            { id: 'session-1', title: 'System Diagnostics & Telemetry', created_at: new Date().toISOString() },
            { id: 'session-2', title: 'Code Refactoring & Testing', created_at: new Date().toISOString() }
          ];
        }
        return { success: true };
      }
    };
  });

  console.log('🔗 Loading application from static server...');
  await page.goto(server.url, { waitUntil: 'load', timeout: 15000 });
  await page.waitForTimeout(2500);

  // Activate system online
  try {
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const systemBtn = buttons.find((b) => b.textContent && b.textContent.includes('SYSTEM'));
      if (systemBtn) systemBtn.click();
    });
    await page.waitForTimeout(1000);
  } catch (e) {
    console.warn('System toggle note:', e);
  }

  const capturedSlides = [];

  for (const mod of modulesToCapture) {
    console.log(`📸 Capturing view: ${mod.id} (${mod.title})...`);
    try {
      await page.evaluate((tabId) => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find((b) => {
          const t = b.textContent ? b.textContent.trim().toUpperCase() : '';
          return t.includes(tabId.toUpperCase());
        });
        if (btn) btn.click();
      }, mod.id);

      await page.waitForTimeout(1600);

      const screenshotFile = path.join(screenshotsDir, `${mod.name}.png`);
      await page.screenshot({ path: screenshotFile, fullPage: false });
      console.log(`  ✓ Saved: ${mod.name}.png`);

      const imageBase64 = fs.readFileSync(screenshotFile).toString('base64');
      capturedSlides.push({
        ...mod,
        imageBase64: `data:image/png;base64,${imageBase64}`
      });
    } catch (err) {
      console.error(`  ✗ Error capturing ${mod.id}:`, err.message);
    }
  }

  console.log('📑 Building Showcase PDF document...');

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #09090b;
      color: #f4f4f5;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    .slide {
      width: 100vw;
      height: 100vh;
      page-break-after: always;
      display: flex;
      flex-direction: column;
      padding: 28px 40px;
      position: relative;
      background: radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.05) 0%, rgba(9, 9, 11, 1) 90%);
      overflow: hidden;
    }

    .slide::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      background: linear-gradient(90deg, #10b981, #06b6d4, #3b82f6);
    }

    /* Cover Slide */
    .cover-slide {
      justify-content: center;
      align-items: center;
      text-align: center;
      background: radial-gradient(circle at 50% 40%, rgba(16, 185, 129, 0.12) 0%, rgba(9, 9, 11, 1) 80%);
    }

    .badge-prototype {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 18px;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #34d399;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      margin-bottom: 18px;
    }

    .cover-title {
      font-size: 52px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 40%, #a1a1aa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 10px;
    }

    .cover-subtitle {
      font-size: 20px;
      color: #10b981;
      font-weight: 600;
      letter-spacing: 0.05em;
      margin-bottom: 20px;
    }

    .cover-desc {
      max-width: 780px;
      font-size: 15px;
      line-height: 1.6;
      color: #a1a1aa;
      margin-bottom: 30px;
    }

    .tech-stack-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
      max-width: 880px;
      margin-bottom: 30px;
    }

    .tech-chip {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      color: #e4e4e7;
    }

    .author-box {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: #71717a;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 16px;
    }

    .author-box span {
      color: #10b981;
      font-weight: 600;
    }

    /* Content Slides */
    .slide-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 8px;
    }

    .slide-title-group h2 {
      font-size: 20px;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .slide-title-group p {
      font-size: 13px;
      color: #9ca3af;
      margin-top: 2px;
    }

    .slide-num-badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 4px 10px;
      border-radius: 6px;
    }

    .screenshot-container {
      flex: 1;
      width: 100%;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 16px 36px -12px rgba(0, 0, 0, 0.8);
      background: #000000;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .screenshot-container img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .slide-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: #71717a;
    }

    /* Final Summary Slide */
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      margin-top: 14px;
    }

    .summary-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 18px;
    }

    .summary-card h3 {
      font-size: 15px;
      color: #34d399;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .summary-card ul {
      list-style-type: none;
    }

    .summary-card li {
      font-size: 12px;
      color: #d4d4d8;
      margin-bottom: 6px;
      line-height: 1.4;
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }

    .summary-card li::before {
      content: "▹";
      color: #10b981;
      font-size: 12px;
    }
  </style>
</head>
<body>

  <!-- Slide 1: Cover -->
  <div class="slide cover-slide">
    <div class="badge-prototype">⚡ Working Prototype Showcase</div>
    <h1 class="cover-title">J.A.R.V.I.S AI</h1>
    <h2 class="cover-subtitle">Autonomous AI Desktop Assistant & Neural Interface</h2>
    <p class="cover-desc">
      A futuristic, local-first autonomous desktop AI assistant featuring an interactive 3D particle HUD, 
      neural voice synthesis and speech recognition, multi-model LLM routing, and full OS automation capabilities.
    </p>
    <div class="tech-stack-row">
      <div class="tech-chip">Electron 40 + React 19</div>
      <div class="tech-chip">Three.js 3D Particle HUD</div>
      <div class="tech-chip">Faster-Whisper & Piper Voice Engine</div>
      <div class="tech-chip">Nous Hermes Agent Runtime</div>
      <div class="tech-chip">Ollama / Gemini / Claude / GPT Routing</div>
      <div class="tech-chip">Puppeteer Stealth Automation</div>
      <div class="tech-chip">Node-Pty Terminal Console</div>
    </div>
    <div class="author-box">
      Developer: <span>Oishik</span> &nbsp;|&nbsp; Phone / WhatsApp: <span>+91 8145406618</span> &nbsp;|&nbsp; Status: <span>Working Prototype</span>
    </div>
  </div>

  <!-- Content Slides for Every Tab -->
  ${capturedSlides
    .map(
      (slide, index) => `
  <div class="slide">
    <div class="slide-header">
      <div class="slide-title-group">
        <h2>${slide.title}</h2>
        <p>${slide.desc}</p>
      </div>
      <div class="slide-num-badge">TAB ${String(index + 1).padStart(2, '0')} / ${String(capturedSlides.length).padStart(2, '0')}</div>
    </div>
    <div class="screenshot-container">
      <img src="${slide.imageBase64}" alt="${slide.title}" />
    </div>
    <div class="slide-footer">
      <span>J.A.R.V.I.S Autonomous Desktop Assistant — Working Prototype</span>
      <span>Developer Contact: +91 8145406618 (Oishik)</span>
    </div>
  </div>
  `
    )
    .join('')}

  <!-- Summary Slide -->
  <div class="slide">
    <div class="slide-header">
      <div class="slide-title-group">
        <h2>Project Architecture & Commercial Capabilities</h2>
        <p>Comprehensive overview of key sub-systems, integrations, and readiness for commercialization or buyout.</p>
      </div>
      <div class="slide-num-badge">SPECS</div>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <h3>🧠 Autonomous Intelligence & Routing</h3>
        <ul>
          <li><strong>Multi-Provider LLM Gateway:</strong> Native support for local offline models via Ollama as well as cloud API providers (Google Gemini, Anthropic Claude, OpenAI, Groq).</li>
          <li><strong>Hermes Agent Core:</strong> Persistent session storage, memory banks, subagents, and skill execution.</li>
          <li><strong>Task Automation:</strong> OS-level file operations, shell script execution, and automated workflows.</li>
        </ul>
      </div>

      <div class="summary-card">
        <h3>🎙️ Local Neural Voice Stack</h3>
        <ul>
          <li><strong>Speech-to-Text:</strong> Offline accelerated faster-whisper transcription for real-time speech input.</li>
          <li><strong>Text-to-Speech:</strong> Ultra-fast neural Piper TTS for natural voice synthesis.</li>
          <li><strong>Wake Word & EchoGate:</strong> openWakeWord activation with acoustic feedback cancellation.</li>
        </ul>
      </div>

      <div class="summary-card">
        <h3>🖥️ UI/UX & Desktop Integration</h3>
        <ul>
          <li><strong>Futuristic Particle HUD:</strong> Three.js particle canvas with audio frequency spectrum reaction and reactive HUD cards.</li>
          <li><strong>Desktop Automation:</strong> Puppeteer stealth web browser automation, screen vision, and camera OCR processing.</li>
          <li><strong>Integrated CLI:</strong> Full xterm.js developer terminal connected to native system shell via node-pty.</li>
        </ul>
      </div>

      <div class="summary-card">
        <h3>📦 Build & Distribution Readiness</h3>
        <ul>
          <li><strong>Cross-Platform Installers:</strong> Preconfigured packaging scripts for Windows (NSIS/MSI), macOS (DMG/Zip), and Linux (AppImage/deb).</li>
          <li><strong>Clean MIT Licensing:</strong> Built on permissive open-source components allowing unrestricted customization, rebranding, and commercial distribution.</li>
        </ul>
      </div>
    </div>

    <div class="slide-footer">
      <span>J.A.R.V.I.S AI Project — Working Prototype Showcase</span>
      <span>Contact: Oishik (Phone / WhatsApp: +91 8145406618)</span>
    </div>
  </div>

</body>
</html>
  `;

  console.log('🖨️ Rendering PDF via Playwright print...');
  const printPage = await context.newPage();
  await printPage.setContent(htmlContent, { waitUntil: 'load' });
  await printPage.waitForTimeout(1500);

  const pdfBuffer = await printPage.pdf({
    format: 'A4',
    landscape: true,
    printBackground: true,
    margin: { top: '0px', right: '0px', bottom: '0px', left: '0px' }
  });

  // Try writing to target and alternative fallback if locked
  let targetPath = outputPdfPath;
  try {
    fs.writeFileSync(outputPdfPath, pdfBuffer);
  } catch (err) {
    targetPath = path.resolve(projectRoot, 'JARVIS_AI_Prototype_Showcase_Clean.pdf');
    fs.writeFileSync(targetPath, pdfBuffer);
  }

  try {
    fs.writeFileSync(brainPdfPath, pdfBuffer);
  } catch (e) {
    console.warn('Note: Could not copy to brain dir:', e.message);
  }

  console.log(`🎉 PDF generated successfully!`);
  console.log(`📁 File location: ${targetPath}`);

  await browser.close();
  await server.close();
}

captureAndGeneratePdf().catch((err) => {
  console.error('Fatal Error:', err);
  process.exit(1);
});
