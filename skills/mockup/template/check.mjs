/* Behaviour check for a mockup built from this template.
   node check.mjs  → exit 0 pass, 1 fail, 2 missing environment. Screenshots go to .check/.
   Replace the screen ids and selectors below with the real ones; keep every assertion. */
import { readFile, stat, mkdir } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, normalize, dirname } from 'node:path';
import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const OUT = join(ROOT, '.check');
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml' };
const problems = [], passes = [];
const expect = (ok, where, msg) => { (ok ? passes : problems).push(`${where}: ${msg}`); };

async function load() { try { return (await import('playwright-core')).chromium; } catch {} console.error('playwright-core is not installed: run `npm install` first'); process.exit(2); }
function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  const base = join(homedir(), '.cache', 'ms-playwright');
  if (existsSync(base)) {
    for (const d of readdirSync(base).filter(d => /^chromium-\d+$/.test(d)).sort().reverse()) {
      for (const p of [join(base, d, 'chrome-linux64', 'chrome'), join(base, d, 'chrome-linux', 'chrome')]) if (existsSync(p)) return p;
    }
  }
  return existsSync('/usr/bin/microsoft-edge') ? '/usr/bin/microsoft-edge' : undefined;
}
function serve(root) {
  const s = createServer(async (req, res) => {
    try {
      let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      if (p.endsWith('/')) p += 'index.html';
      const f = normalize(join(root, p));
      if (!f.startsWith(root)) { res.writeHead(403).end(); return; }
      if (!(await stat(f)).isFile()) throw new Error('not a file');
      res.writeHead(200, { 'content-type': TYPES[extname(f)] || 'application/octet-stream' });
      res.end(await readFile(f));
    } catch { res.writeHead(404).end('not found'); }
  });
  return new Promise(r => s.listen(0, '127.0.0.1', () => r(s)));
}

const chromium = await load();
await mkdir(OUT, { recursive: true });
const server = await serve(ROOT);
const base = `http://127.0.0.1:${server.address().port}/index.html`;
const browser = await chromium.launch({ executablePath: chromePath(), headless: true });
const errors = [];
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));
await page.goto(base, { waitUntil: 'networkidle' });

/* 1. gallery */
const ids = await page.evaluate(() => window.Mockups.screens(window.SEED).map(s => s.id));
expect(ids.length >= 3, 'gallery', `has ${ids.length} screens`);
expect(await page.locator('.card').count() === ids.length, 'gallery', 'one card per screen');
expect(await page.locator('.mock-links a').count() >= ids.length, 'gallery', 'each card has Open/Mobile');

/* 2. routes */
for (const id of ids) {
  await page.evaluate(i => { location.hash = '#/' + i; }, id);
  await page.waitForTimeout(120);
  const info = await page.evaluate(() => ({ screen: !!document.querySelector('#view .screen'), len: document.querySelector('#view').innerText.trim().length, title: document.getElementById('title').textContent }));
  expect(info.screen && info.len > 60 && info.title.length > 0, `route ${id}`, 'renders a titled screen');
}

/* 3. theme persists */
await page.evaluate(() => { location.hash = '#/settings'; });
const before = await page.evaluate(() => document.documentElement.dataset.theme);
await page.click('#theme');
const after = await page.evaluate(() => document.documentElement.dataset.theme);
expect(before !== after, 'theme', `toggles (${before} → ${after})`);
await page.reload({ waitUntil: 'networkidle' });
expect(await page.evaluate(() => document.documentElement.dataset.theme) === after, 'theme', 'kept after reload');
await page.click('#theme');

/* 4. hover changes colour + weight */
await page.evaluate(() => { location.hash = '#/login'; });
const btn = await page.$('.btn-primary');
const style = () => page.evaluate(el => { const s = getComputedStyle(el); return { bg: s.backgroundColor, fg: s.color, fw: s.fontWeight }; }, btn);
const a = await style(); await btn.hover(); await page.waitForTimeout(320); const b = await style();
expect(a.bg !== b.bg || a.fg !== b.fg, 'hover', `colour changes (${a.bg} → ${b.bg})`);
expect(a.fw !== b.fw, 'hover', `font-weight changes (${a.fw} → ${b.fw})`);

/* 4b. keyboard focus is visible */
await page.keyboard.press('Tab');
const focus = await page.evaluate(() => {
  const el = document.activeElement, s = getComputedStyle(el);
  return { tag: el.tagName, outline: s.outlineStyle, width: s.outlineWidth, shadow: s.boxShadow };
});
const ring = (focus.outline !== 'none' && focus.width !== '0px') || focus.shadow !== 'none';
expect(ring, 'focus', `visible focus on Tab (${focus.tag})`);

/* 5. mobile frame */
await page.click('[data-device="mobile"]'); await page.waitForTimeout(150);
const mob = await page.evaluate(() => { const s = document.querySelector('.screen'); return { cls: document.getElementById('view').classList.contains('device-mobile'), w: s ? Math.round(s.getBoundingClientRect().width) : 0 }; });
expect(mob.cls && mob.w > 360 && mob.w <= 392, 'device', `390px frame (${mob.w})`);
await page.click('[data-device="web"]');

/* 6. loading → complete on generate */
await page.evaluate(() => { location.hash = '#/board'; });
await page.waitForTimeout(120);
const beforePending = await page.$eval('.stat b', el => Number(el.textContent));
await page.click('[data-action="generate"]');
expect(await page.locator('.skeleton').count() > 0, 'loading', 'skeleton while generating');
await page.waitForTimeout(1400);
expect(await page.locator('.skeleton').count() === 0, 'loading', 'skeleton clears when done');

/* 7. approve moves the counter */
await page.locator('[data-approve]').first().click();
await page.waitForTimeout(900);
const afterPending = await page.$eval('.stat b', el => Number(el.textContent));
expect(afterPending === beforePending - 1, 'approve', `pending ${beforePending} → ${afterPending}`);

/* 8. no horizontal overflow at 390 */
await page.setViewportSize({ width: 390, height: 844 });
for (const id of ['gallery', ...ids]) {
  await page.evaluate(i => { location.hash = i === 'gallery' ? '#/gallery' : '#/' + i; }, id);
  await page.waitForTimeout(150);
  const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(over <= 1, `390 ${id}`, `no overflow (${over}px)`);
}

/* 9. reduced motion */
const calm = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
await calm.goto(base + '#/board', { waitUntil: 'networkidle' });
const anim = await calm.evaluate(() => { const el = document.querySelector('.spinner,.pulse,.toast'); return el ? getComputedStyle(el).animationName : 'none'; });
expect(anim === 'none', 'reduced-motion', `animations off (${anim})`);
await calm.close();

/* 10. screenshots */
await page.setViewportSize({ width: 1440, height: 900 });
for (const id of ['gallery', ...ids]) {
  await page.evaluate(i => { location.hash = i === 'gallery' ? '#/gallery' : '#/' + i; }, id);
  await page.waitForTimeout(180);
  await page.screenshot({ path: join(OUT, `desktop-1440-${id}.png`) });
}

/* 11. console */
expect(errors.length === 0, 'console', `0 errors (${errors.length}${errors.length ? ': ' + errors.slice(0, 2).join(' | ') : ''})`);

await browser.close(); server.close();
for (const p of passes) console.log('  PASS  ' + p);
for (const p of problems) console.log('  FAIL  ' + p);
console.log(`\n${passes.length} pass, ${problems.length} fail`);
process.exit(problems.length ? 1 : 0);
