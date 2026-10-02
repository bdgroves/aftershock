// Screenshots of the live site, run in Actions (real network: tiles, CDN scripts).
import { chromium } from 'playwright';
import fs from 'fs';
const b = await chromium.launch();
const errs = [];
for (const [name, vp, hash] of [['desk', { width: 1440, height: 900 }, 'us'], ['world', { width: 1440, height: 900 }, 'world'], ['phone', { width: 390, height: 844 }, 'us-CA'], ['texas', { width: 1440, height: 900 }, 'us-TX'], ['oklahoma', { width: 1440, height: 900 }, 'us-OK'], ['washington', { width: 1440, height: 900 }, 'us-WA']]) {
  const p = await b.newPage({ viewport: vp });
  p.on('pageerror', e => errs.push(`${name}: ${e.message}`));
  p.on('console', m => { if (m.type() === 'error') errs.push(`${name} console: ${m.text()}`); });
  await p.goto('https://brooksgroves.com/aftershock/?v=' + Date.now() + '#' + hash, { waitUntil: 'networkidle' });
  await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); });
  await p.waitForTimeout(3000);
  await p.screenshot({ path: `tools/shots/${name}.png`, fullPage: true });
}
fs.writeFileSync('tools/shots/errors.txt', errs.join('\n') || 'no errors');
await b.close();
