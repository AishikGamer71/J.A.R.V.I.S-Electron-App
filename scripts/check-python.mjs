import { spawn } from 'node:child_process';
import path from 'node:path';

const electronPath = path.resolve('node_modules/electron/dist/electron.exe');
console.log('Launching Electron with stdio inherit...');
const child = spawn(electronPath, ['.'], {
  cwd: process.cwd(),
  env: { ...process.env, ELECTRON_ENABLE_LOGGING: '1' },
  stdio: 'inherit'
});

let sec = 0;
const interval = setInterval(async () => {
  sec++;
  try {
    const res = await fetch('http://127.0.0.1:8765/health');
    const data = await res.json();
    console.log(`\n==========================================`);
    console.log(`[Second ${sec}] BACKEND IS HEALTHY AND CONNECTED!`);
    console.log(data);
    console.log(`==========================================\n`);
    clearInterval(interval);
    setTimeout(() => {
      child.kill();
      process.exit(0);
    }, 2000);
  } catch (err) {
    process.stdout.write(`[Sec ${sec}: wait] `);
    if (sec >= 20) {
      clearInterval(interval);
      child.kill();
      process.exit(1);
    }
  }
}, 1000);
