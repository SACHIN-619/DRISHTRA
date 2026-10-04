async function main() {
  const res = await fetch('http://127.0.0.1:9222/json/list');
  const pages = await res.json();
  const page = pages.find(p => p.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);

  ws.onopen = () => {
    ws.send(JSON.stringify({
      id: 1,
      method: 'Runtime.evaluate',
      params: {
        expression: `
          (() => {
            const el = document.querySelector('.bg-environment');
            const main = document.querySelector('main');
            const body = document.body;
            return {
              bodyBg: window.getComputedStyle(body).backgroundColor,
              divBg: el ? window.getComputedStyle(el).backgroundColor : 'none',
              mainBg: main ? window.getComputedStyle(main).backgroundColor : 'none',
              htmlClass: document.documentElement.className
            };
          })()
        `,
        returnByValue: true
      }
    }));
  };

  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.id === 1) {
      console.log('Styles:', data.result.value);
      process.exit(0);
    }
  };
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
