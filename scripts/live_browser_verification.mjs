import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ARTIFACTS_DIR = path.resolve('browser_artifacts');

if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

// Launch Chrome with remote debugging
const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--disable-gpu',
  '--window-size=1440,900',
  'http://localhost:3000'
]);

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getWsUrl() {
  for (let i = 0; i < 20; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/list');
      const data = await res.json();
      const page = data.find(p => p.type === 'page');
      if (page && page.webSocketDebuggerUrl) {
        return page.webSocketDebuggerUrl;
      }
    } catch (e) {}
    await sleep(500);
  }
  throw new Error('Chrome debugging endpoint not ready');
}

async function main() {
  try {
    console.log('Connecting to Chrome Remote Debugging...');
    const wsUrl = await getWsUrl();
    const ws = new WebSocket(wsUrl);

    let idCounter = 1;
    const pending = new Map();

    ws.addEventListener('message', (event) => {
      const parsed = JSON.parse(event.data);
      if (parsed.id && pending.has(parsed.id)) {
        pending.get(parsed.id)(parsed.result);
        pending.delete(parsed.id);
      }
    });

    await new Promise((resolve) => ws.addEventListener('open', resolve));

    function send(method, params = {}) {
      return new Promise((resolve) => {
        const id = idCounter++;
        pending.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    await send('Page.enable');
    await send('Runtime.enable');
    await sleep(2000);

    // Check light mode default class on html
    const lightCheck = await send('Runtime.evaluate', {
      expression: 'document.documentElement.className',
      returnByValue: true
    });
    console.log('Initial html class attribute:', lightCheck?.result?.value);

    // Get initial computed background color of body
    const initialBg = await send('Runtime.evaluate', {
      expression: 'window.getComputedStyle(document.body).backgroundColor',
      returnByValue: true
    });
    console.log('Initial body background color (Light mode default):', initialBg?.result?.value);

    // Take Light Mode Screenshot
    const shot1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(ARTIFACTS_DIR, '01_light_mode_default.png'), Buffer.from(shot1.data, 'base64'));
    console.log('Saved 01_light_mode_default.png');

    // Toggle theme via clicking theme toggle button (button with title containing "theme" or toggleTheme)
    const toggleResult = await send('Runtime.evaluate', {
      expression: `
        (() => {
          const btn = Array.from(document.querySelectorAll('button')).find(b => 
            (b.getAttribute('title') && b.getAttribute('title').toLowerCase().includes('theme')) ||
            (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('theme')) ||
            b.innerText.toLowerCase().includes('light') || b.innerText.toLowerCase().includes('dark') ||
            b.outerHTML.includes('toggleTheme') || b.querySelector('svg')
          );
          if (btn) {
            btn.click();
            return 'Theme button clicked: ' + (btn.getAttribute('title') || btn.innerText || btn.className);
          }
          return 'Theme button not found';
        })()
      `,
      returnByValue: true
    });
    console.log('Toggle Theme action:', toggleResult?.result?.value);
    await sleep(1000);

    // Check dark mode class on html
    const darkCheck = await send('Runtime.evaluate', {
      expression: 'document.documentElement.className',
      returnByValue: true
    });
    console.log('Updated html class attribute:', darkCheck?.result?.value);

    // Get updated computed background color of body
    const darkBg = await send('Runtime.evaluate', {
      expression: 'window.getComputedStyle(document.body).backgroundColor',
      returnByValue: true
    });
    console.log('Updated body background color (Dark mode active):', darkBg?.result?.value);

    // Take Dark Mode Screenshot
    const shot2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(ARTIFACTS_DIR, '02_dark_mode_active.png'), Buffer.from(shot2.data, 'base64'));
    console.log('Saved 02_dark_mode_active.png');

    // Toggle theme back to light mode
    await send('Runtime.evaluate', {
      expression: `
        (() => {
          const btn = Array.from(document.querySelectorAll('button')).find(b => 
            (b.getAttribute('title') && b.getAttribute('title').toLowerCase().includes('theme')) ||
            (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('theme')) ||
            b.innerText.toLowerCase().includes('light') || b.innerText.toLowerCase().includes('dark') ||
            b.outerHTML.includes('toggleTheme') || b.querySelector('svg')
          );
          if (btn) btn.click();
        })()
      `,
      returnByValue: true
    });
    await sleep(1000);

    const backCheck = await send('Runtime.evaluate', {
      expression: 'document.documentElement.className',
      returnByValue: true
    });
    console.log('Restored html class attribute:', backCheck?.result?.value);

    const shot3 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(ARTIFACTS_DIR, '03_restored_light_mode.png'), Buffer.from(shot3.data, 'base64'));
    console.log('Saved 03_restored_light_mode.png');

    ws.close();
    chrome.kill();
    process.exit(0);
  } catch (err) {
    console.error('Error in live browser verification:', err);
    if (chrome) chrome.kill();
    process.exit(1);
  }
}

main();
