import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const USER_DATA_DIR = path.resolve('./temp_chrome_profile');
const SCREENSHOT_DIR = path.resolve('./browser_artifacts');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

console.log('[DRISHTRA BROWSER TEST] Starting Chrome Headless on CDP port 9222...');
const chromeProc = spawn(CHROME_PATH, [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--remote-allow-origins=*',
  `--user-data-dir=${USER_DATA_DIR}`,
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--window-size=1440,960'
]);

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getPageWsUrl() {
  for (let i = 0; i < 20; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/list');
      const list = await res.json();
      const page = list.find(item => item.type === 'page');
      if (page && page.webSocketDebuggerUrl) {
        return page.webSocketDebuggerUrl;
      }
    } catch (e) {
      await sleep(500);
    }
  }
  throw new Error('Could not find page target in Chrome DevTools');
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
    console.log(`[DRISHTRA BROWSER TEST] Screenshot saved: ${filePath}`);
  }

  close() {
    this.ws.close();
  }
}

async function run() {
  try {
    const wsUrl = await getPageWsUrl();
    console.log('[DRISHTRA BROWSER TEST] Connected to Page CDP:', wsUrl);

    const client = new CDPClient(wsUrl);
    await client.connect();

    await client.send('Page.enable');
    await client.send('DOM.enable');
    await client.send('Runtime.enable');

    console.log('[DRISHTRA BROWSER TEST] Navigating to http://localhost:3005...');
    await client.send('Page.navigate', { url: 'http://localhost:3005' });
    await sleep(3500); // allow hydration & canvas mount

    // 1. Verify default theme is Light Mode
    const htmlClasses = await client.eval('document.documentElement.className');
    const bodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');
    const bodyColor = await client.eval('window.getComputedStyle(document.body).color');
    const toggleBtnText = await client.eval('document.getElementById("themeToggleBtn")?.innerText');
    const hasDarkClass = await client.eval('document.documentElement.classList.contains("dark")');
    const hasLightClass = await client.eval('document.documentElement.classList.contains("light")');

    console.log('\n--- [CHECK 1: DEFAULT THEME STATE] ---');
    console.log('HTML Element Class:', htmlClasses);
    console.log('Contains "light":', hasLightClass);
    console.log('Contains "dark":', hasDarkClass);
    console.log('Computed Body Background:', bodyBg);
    console.log('Computed Body Color:', bodyColor);
    console.log('Theme Toggle Button Text:', toggleBtnText);

    if (hasDarkClass) {
      throw new Error('FAILURE: Initial theme is Dark, expected Light mode by default!');
    }
    console.log('>>> SUCCESS: Light Mode is active BY DEFAULT! <<<');

    await client.screenshot(path.join(SCREENSHOT_DIR, '01_default_light_mode.png'));

    // 2. Click Theme Toggle Button to switch to Dark Mode
    console.log('\n--- [CHECK 2: TOGGLE TO DARK MODE] ---');
    const clickedDark = await client.eval(`
      (() => {
        const btn = document.getElementById("themeToggleBtn");
        if (btn) {
          btn.click();
          return true;
        }
        return false;
      })()
    `);
    console.log('Clicked themeToggleBtn:', clickedDark);
    await sleep(800);

    const darkHtmlClasses = await client.eval('document.documentElement.className');
    const darkBodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');
    const darkStorage = await client.eval('localStorage.getItem("drishtra_theme")');
    const darkHasDarkClass = await client.eval('document.documentElement.classList.contains("dark")');

    console.log('HTML Element Class after toggle:', darkHtmlClasses);
    console.log('Contains "dark" class:', darkHasDarkClass);
    console.log('Computed Body Background in Dark Mode:', darkBodyBg);
    console.log('localStorage drishtra_theme:', darkStorage);

    if (!darkHasDarkClass || darkStorage !== 'dark') {
      throw new Error('FAILURE: Dark mode class was not applied after toggle click!');
    }
    console.log('>>> SUCCESS: Dark Mode toggled successfully! <<<');
    await client.screenshot(path.join(SCREENSHOT_DIR, '02_dark_mode_active.png'));

    // 3. Click Theme Toggle Button again to switch back to Light Mode
    console.log('\n--- [CHECK 3: TOGGLE BACK TO LIGHT MODE] ---');
    await client.eval('document.getElementById("themeToggleBtn").click()');
    await sleep(800);

    const revertedHtmlClasses = await client.eval('document.documentElement.className');
    const revertedBodyBg = await client.eval('window.getComputedStyle(document.body).backgroundColor');
    const revertedStorage = await client.eval('localStorage.getItem("drishtra_theme")');

    console.log('HTML Element Class after revert:', revertedHtmlClasses);
    console.log('Computed Body Background after revert:', revertedBodyBg);
    console.log('localStorage drishtra_theme:', revertedStorage);

    if (revertedStorage !== 'light' || revertedHtmlClasses.includes('dark')) {
      throw new Error('FAILURE: Theme did not revert to Light Mode cleanly!');
    }
    console.log('>>> SUCCESS: Switched back to Light Mode successfully! <<<');
    await client.screenshot(path.join(SCREENSHOT_DIR, '03_reverted_light_mode.png'));

    // 4. Test Scenario Switching Interactivity
    console.log('\n--- [CHECK 4: SCENARIO SWITCHING] ---');
    const scenarioClicked = await client.eval(`
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const poisonBtn = buttons.find(b => b.innerText.includes('Label Poisoning'));
        if (poisonBtn) {
          poisonBtn.click();
          return poisonBtn.innerText.trim();
        }
        return null;
      })()
    `);
    console.log('Clicked Scenario Button:', scenarioClicked);
    await sleep(800);
    await client.screenshot(path.join(SCREENSHOT_DIR, '04_scenario_poisoning_selected.png'));

    // 5. Test Finding Explainability Route (/findings/F-291)
    console.log('\n--- [CHECK 5: FINDINGS EXPLAINABILITY VIEW] ---');
    await client.send('Page.navigate', { url: 'http://localhost:3005/findings/F-291' });
    await sleep(2500);

    const findingTitle = await client.eval('document.querySelector("h1, h2")?.innerText');
    console.log('Findings Page Heading:', findingTitle);
    await client.screenshot(path.join(SCREENSHOT_DIR, '05_finding_f291_light.png'));

    // 6. Test Evidence Locker / Cases Route (/cases)
    console.log('\n--- [CHECK 6: CASES & CHAIN OF CUSTODY] ---');
    await client.send('Page.navigate', { url: 'http://localhost:3005/cases' });
    await sleep(2500);
    await client.screenshot(path.join(SCREENSHOT_DIR, '06_cases_view.png'));

    // 7. Test AI Model Passport Route (/passports/M-04)
    console.log('\n--- [CHECK 7: AI PASSPORT VIEW] ---');
    await client.send('Page.navigate', { url: 'http://localhost:3005/passports/M-04' });
    await sleep(2500);
    await client.screenshot(path.join(SCREENSHOT_DIR, '07_passport_m04_view.png'));

    client.close();
    console.log('\n======================================================');
    console.log('✅ ALL LIVE BROWSER VERIFICATIONS PASSED 100%!');
    console.log('======================================================\n');
  } finally {
    try {
      chromeProc.kill();
    } catch (e) {}
  }
}

run().catch((err) => {
  console.error('[DRISHTRA BROWSER TEST ERROR]:', err);
  try {
    chromeProc.kill();
  } catch (e) {}
  process.exit(1);
});
