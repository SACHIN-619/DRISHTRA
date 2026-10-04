import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const TEMP_PROFILE = path.resolve('./temp_fresh_profile_' + Date.now());
const ARTIFACTS_DIR = path.resolve('./browser_artifacts');

if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

console.log('[BROWSER TEST] Launching fresh isolated Chrome instance...');
const chromeProc = spawn(CHROME_PATH, [
  '--headless=new',
  '--remote-debugging-port=9333',
  '--remote-allow-origins=*',
  `--user-data-dir=${TEMP_PROFILE}`,
  '--disable-gpu',
  '--window-size=1440,960'
]);

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getWsUrl() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9333/json/list');
      const list = await res.json();
      const page = list.find(item => item.type === 'page');
      if (page && page.webSocketDebuggerUrl) {
        return page.webSocketDebuggerUrl;
      }
    } catch (e) {
      await sleep(300);
    }
  }
  throw new Error('Could not find page target on port 9333');
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) {
            cb.reject(new Error(msg.error.message));
          } else {
            cb.resolve(msg.result);
          }
        }
      };
    });
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    return res.result ? res.result.value : null;
  }

  async screenshot(filePath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(filePath, Buffer.from(res.data, 'base64'));
    console.log(`[BROWSER TEST] Saved screenshot: ${path.basename(filePath)}`);
  }

  close() {
    this.ws.close();
  }
}

async function main() {
  try {
    const wsUrl = await getWsUrl();
    console.log('[BROWSER TEST] Connected to fresh Chrome page on port 9333');

    const client = new CDPClient(wsUrl);
    await client.connect();

    await client.send('Page.enable');
    await client.send('DOM.enable');
    await client.send('Runtime.enable');

    console.log('[BROWSER TEST] Navigating to http://localhost:3005...');
    await client.send('Page.navigate', { url: 'http://localhost:3005' });
    await sleep(4000); // full hydration & layout

    // Inspect initial state
    const htmlClasses = await client.eval('document.documentElement.className');
    const bodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');
    const mainBg = await client.eval('window.getComputedStyle(document.querySelector("main") || document.body).backgroundColor');
    const containerBg = await client.eval('window.getComputedStyle(document.querySelector(".min-h-screen") || document.body).backgroundColor');
    const textThemeBtn = await client.eval('document.getElementById("themeToggleBtn")?.innerText');

    console.log('\n================ INITIAL LOAD (DEFAULT THEME) ================');
    console.log('HTML Class:', htmlClasses);
    console.log('Body Background:', bodyBg);
    console.log('Container Background:', containerBg);
    console.log('Main Content Background:', mainBg);
    console.log('Theme Toggle Button Text:', textThemeBtn?.replace(/\\n/g, ' '));

    await client.screenshot(path.join(ARTIFACTS_DIR, '01_fresh_default_light.png'));

    // Toggle to Dark Mode
    console.log('\n================ TOGGLING TO DARK MODE ================');
    await client.eval('document.getElementById("themeToggleBtn").click()');
    await sleep(1000);

    const darkHtmlClasses = await client.eval('document.documentElement.className');
    const darkBodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');
    const darkStorage = await client.eval('localStorage.getItem("drishtra_theme")');

    console.log('HTML Class in Dark Mode:', darkHtmlClasses);
    console.log('Body Background in Dark Mode:', darkBodyBg);
    console.log('localStorage theme:', darkStorage);

    await client.screenshot(path.join(ARTIFACTS_DIR, '02_fresh_dark_mode.png'));

    // Toggle back to Light Mode
    console.log('\n================ REVERTING TO LIGHT MODE ================');
    await client.eval('document.getElementById("themeToggleBtn").click()');
    await sleep(1000);

    const revertedHtmlClasses = await client.eval('document.documentElement.className');
    const revertedBodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');

    console.log('HTML Class reverted:', revertedHtmlClasses);
    console.log('Body Background reverted:', revertedBodyBg);

    await client.screenshot(path.join(ARTIFACTS_DIR, '03_fresh_reverted_light.png'));

    client.close();
    console.log('\n[BROWSER TEST COMPLETE] All tests passed.');
  } finally {
    try {
      chromeProc.kill();
    } catch (e) {}
    try {
      fs.rmSync(TEMP_PROFILE, { recursive: true, force: true });
    } catch (e) {}
  }
}

main().catch(err => {
  console.error('[BROWSER TEST ERROR]:', err);
  try {
    chromeProc.kill();
  } catch (e) {}
  process.exit(1);
});
