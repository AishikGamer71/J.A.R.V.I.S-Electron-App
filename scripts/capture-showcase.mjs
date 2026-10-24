import { createServer } from 'vite';
import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const outputDir = path.resolve(projectRoot, 'showcase_screenshots');

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

async function run() {
  console.log('Starting Vite server...');
  const server = await createServer({
    configFile: path.resolve(projectRoot, 'vite.config.ts'),
    server: {
      port: 5280,
      host: '127.0.0.1'
    }
  });

  await server.listen();
  const address = server.httpServer.address();
  const serverUrl = `http://127.0.0.1:${address.port}`;
  console.log(`Vite server running at ${serverUrl}`);

  console.log('Launching Chrome browser...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    defaultViewport: {
      width: 1440,
      height: 900,
      deviceScaleFactor: 2
    },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security', '--disable-gpu']
  });

  const page = await browser.newPage();

  // Mock electron IPC bridge so components do not throw
  await page.evaluateOnNewDocument(() => {
    window.electron = {
      ipcRenderer: {
        on: () => {},
        off: () => {},
        send: () => {},
        invoke: async (channel, ...args) => {
          if (channel === 'get-system-status') {
            return {
              cpuUsage: 18.5,
              memUsage: 42.1,
              battery: { hasBattery: true, isCharging: true, percent: 94 },
              network: { online: true, latency: 24 }
            };
          }
          if (channel === 'get-chat-history') return [];
          return null;
        },
        removeAllListeners: () => {}
      }
    };
    window.hermesDesktop = {
      isAvailable: true,
      getStatus: async () => ({ status: 'ready', model: 'hermes-3-llama-3.1-8b' })
    };
  });

  console.log('Navigating to app...');
  await page.goto(serverUrl, { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise((r) => setTimeout(r, 3000));

  const tabs = [
    { id: 'CHAT', name: '01_Neural_Chat_Interface' },
    { id: 'DASHBOARD', name: '02_Dashboard_Particle_HUD' },
    { id: 'MODULES', name: '03_Autonomous_Modules' },
    { id: 'TASK MANAGER', name: '04_Task_System_Monitor' },
    { id: 'Apps', name: '05_App_Store_Plugins' },
    { id: 'NOTES', name: '06_Quick_Notes_Workspace' },
    { id: 'GALLERY', name: '07_Neural_Media_Gallery' },
    { id: 'TERMINAL', name: '08_Integrated_Terminal' },
    { id: 'PHONE', name: '09_Comms_Phone_Bridge' },
    { id: 'SETTINGS', name: '10_Settings_Model_Vault' }
  ];

  const capturedImages = [];

  for (const tab of tabs) {
    console.log(`Switching to tab: ${tab.id}...`);
    try {
      const clicked = await page.evaluate((tabId) => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find((b) => b.textContent && b.textContent.trim().toUpperCase().includes(tabId.toUpperCase()));
        if (btn) {
          btn.click();
          return true;
        }
        return false;
      }, tab.id);

      await new Promise((r) => setTimeout(r, 2000));

      const filePath = path.join(outputDir, `${tab.name}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved screenshot: ${filePath}`);
      capturedImages.push(filePath);
    } catch (err) {
      console.error(`Error capturing ${tab.id}:`, err.message);
    }
  }

  await browser.close();
  await server.close();
  console.log('Capture complete! Total images:', capturedImages.length);
}

run().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
