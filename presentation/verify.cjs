/* Run against the local server. Playwright is only a verification dependency. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

let browser;
(async () => {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => requests.push(r.url()));
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  const review = name => path.join(__dirname, '.impeccable/review', name);
  await page.goto('http://127.0.0.1:8000');
  await page.waitForFunction(() => window.Reveal?.isReady());
  await page.evaluate(() => document.fonts.ready);
  assert.equal(await page.locator('.slides > section').count(), 2);
  assert.equal(await page.evaluate(() => document.fonts.check('600 28px "Space Grotesk"')), true);
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(244, 241, 233)');
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), false);
  await page.screenshot({ path: review('desktop.png') });
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(350);
  assert.equal(await page.evaluate(() => Reveal.getCurrentSlide().id), 'methodology');
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), true);
  await page.locator('#motion-toggle').click();
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().paused), true);
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), false);
  const initialNodes = await page.locator('#system-diagram *').count();
  // Check the whole loop, including frames near route endpoints and phase changes.
  const diagramAudit = await page.evaluate(() => {
    const svg = document.querySelector('#system-diagram');
    const labels = [...svg.querySelectorAll('text')].filter(el => !el.closest('#hash-cloud, #packet-layer'));
    const intersects = (a, b, inset = 0) => a.x + inset < b.x + b.width && a.x + a.width - inset > b.x && a.y + inset < b.y + b.height && a.y + a.height - inset > b.y;
    const localBox = el => {
      const b = el.getBoundingClientRect();
      const transform = svg.getScreenCTM().inverse();
      const start = new DOMPoint(b.x, b.y).matrixTransform(transform);
      const end = new DOMPoint(b.right, b.bottom).matrixTransform(transform);
      return { x: start.x, y: start.y, width: end.x - start.x, height: end.y - start.y };
    };
    const labelName = el => el.textContent;
    const labelClashes = [], routeClashes = [], packetClashes = [], nodeOverflow = [];
    const boxes = labels.map(el => ({ el, box: localBox(el) }));
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        if (intersects(boxes[i].box, boxes[j].box)) labelClashes.push([labelName(boxes[i].el), labelName(boxes[j].el)]);
      }
    }
    for (const node of svg.querySelectorAll('.node')) {
      const rect = localBox(node.querySelector('rect'));
      for (const label of node.querySelectorAll('text')) {
        const box = localBox(label);
        if (box.x < rect.x + 8 || box.x + box.width > rect.x + rect.width - 8 || box.y < rect.y + 4 || box.y + box.height > rect.y + rect.height - 4) nodeOverflow.push(labelName(label));
      }
    }
    for (const route of svg.querySelectorAll('.connections path')) {
      const length = route.getTotalLength();
      for (let d = 4; d < length - 4; d += 3) {
        const point = route.getPointAtLength(d);
        const hit = boxes.find(({ box }) => point.x > box.x - 2 && point.x < box.x + box.width + 2 && point.y > box.y - 2 && point.y < box.y + box.height + 2);
        if (hit) { routeClashes.push([route.id, labelName(hit.el)]); break; }
      }
    }
    const packetCollisionNames = new Set();
    for (let frame = 0; frame < 600; frame++) {
      const seconds = frame / 20;
      CyberScopePreview.seek(seconds);
      const dynamicBoxes = labels.map(el => ({ el, box: localBox(el) }));
      for (const group of svg.querySelectorAll('#packet-layer > g')) {
        if (group.getAttribute('visibility') !== 'visible' || Number(group.style.opacity) < .15) continue;
        const packetBox = localBox(group);
        for (const { el, box } of dynamicBoxes) {
          if (el.closest('#tamper-marker')?.getAttribute('visibility') === 'hidden') continue;
          if (intersects(packetBox, box, 1)) packetCollisionNames.add(`${group.dataset.route} → ${labelName(el)}`);
        }
      }
    }
    packetClashes.push(...packetCollisionNames);
    const rendered = svg.getBoundingClientRect();
    const matrix = svg.getScreenCTM();
    const renderedContentWidth = matrix.a * svg.viewBox.baseVal.width;
    return { labelClashes, routeClashes, packetClashes, nodeOverflow,
      letterboxWidth: rendered.width - renderedContentWidth,
      diagramWidth: renderedContentWidth,
      plusRemoved: !svg.querySelector('.consumer-node path') };
  });
  console.log('Diagram audit:', JSON.stringify(diagramAudit));
  assert.deepEqual(diagramAudit.labelClashes, [], 'Static diagram labels must not overlap');
  assert.deepEqual(diagramAudit.routeClashes, [], 'Routes must not cross text');
  assert.deepEqual(diagramAudit.packetClashes, [], 'Packets must not cross labels over the full 30-second loop');
  assert.deepEqual(diagramAudit.nodeOverflow, [], 'All node copy must fit with padding');
  assert.ok(Math.abs(diagramAudit.letterboxWidth) < 2, 'SVG must use the available width without side letterboxing');
  assert.equal(diagramAudit.plusRemoved, true, 'The consumer must have no stray plus');
  for (const [seconds, phase, result] of [[4.8, 'onboarding', 'pending'], [13, 'matching', 'match'], [24, 'tampered', 'mismatch'], [29, 'restoring', 'match']]) {
    await page.evaluate(t => CyberScopePreview.seek(t), seconds);
    await page.waitForTimeout(450);
    const state = await page.evaluate(() => CyberScopePreview.getState());
    assert.equal(state.phase, phase);
    assert.equal(state.result, result);
    if (seconds > 6) assert.equal(await page.locator('#baseline-digest').textContent(), '2f9a·7c31');
    if (result === 'mismatch') {
      assert.match(await page.locator('#comparison-text').textContent(), /≠/);
      assert.equal(await page.locator('#tamper-marker').getAttribute('visibility'), 'visible');
      const consumerPackets = await page.locator('#packet-layer > g').evaluateAll(nodes => nodes.filter(n => n.getAttribute('visibility') === 'visible').length);
      assert.ok(consumerPackets > 0, 'Tamper scenario still carries meaningful packet traffic');
    }
    await page.screenshot({ path: review(`${phase}.png`) });
  }
  // Three full deterministic cycles: stable node allocation and unchanged baseline.
  for (let i = 0; i <= 900; i++) await page.evaluate(t => CyberScopePreview.seek(t), i / 10);
  assert.equal(await page.locator('#system-diagram *').count(), initialNodes);
  assert.equal(await page.locator('#baseline-digest').textContent(), '2f9a·7c31');
  await page.evaluate(() => CyberScopePreview.seek(13));
  await page.screenshot({ path: review('method-desktop.png') });
  const noOverlap = await page.evaluate(() => {
    const scene = document.querySelector('.scenario-strip').getBoundingClientRect();
    const footer = document.querySelector('#methodology .slide-footer').getBoundingClientRect();
    return scene.bottom <= footer.top;
  });
  assert.ok(noOverlap, 'Scenario strip must not overlap slide footer');
  await page.locator('#motion-toggle').click();
  await page.waitForTimeout(200);
  const motionAudit = await page.evaluate(() => new Promise(resolve => {
    const frameTimes = [];
    let previous;
    function sample(now) {
      if (previous !== undefined) frameTimes.push(now - previous);
      previous = now;
      if (frameTimes.length < 120) requestAnimationFrame(sample);
      else {
        const sorted = [...frameTimes].sort((a, b) => a - b);
        resolve({ medianFrameMs: sorted[60], p95FrameMs: sorted[114], maxFrameMs: sorted[119] });
      }
    }
    requestAnimationFrame(sample);
  }));
  console.log('Live motion timing:', JSON.stringify(motionAudit));
  assert.ok(motionAudit.medianFrameMs < 34, 'Typical live animation frames should remain smooth');
  const movingTime = await page.evaluate(() => CyberScopePreview.getState().elapsed);
  await page.waitForTimeout(300);
  assert.ok(await page.evaluate(t => CyberScopePreview.getState().elapsed > t, movingTime));
  await page.evaluate(() => Reveal.toggleOverview(true));
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), false);
  await page.evaluate(() => Reveal.toggleOverview(false));
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), true);
  await page.evaluate(() => Reveal.togglePause(true));
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), false);
  await page.evaluate(() => Reveal.togglePause(false));
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), true);
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(350);
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().running), false);
  const offslideTime = await page.evaluate(() => CyberScopePreview.getState().elapsed);
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(() => CyberScopePreview.getState().elapsed), offslideTime);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.screenshot({ path: review('projector-problem.png') });
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(350);
  await page.locator('#motion-toggle').click();
  await page.evaluate(() => CyberScopePreview.seek(24));
  await page.waitForTimeout(450);
  await page.screenshot({ path: review('projector-method.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(350);
  await page.screenshot({ path: review('mobile.png') });
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#methodology')).visibility), 'hidden');
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(350);
  await page.screenshot({ path: review('method-mobile.png') });
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#problem')).visibility), 'hidden');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.evaluate(() => CyberScopePreview.seek(24));
  assert.equal(await page.locator('#packet-layer > g[visibility="visible"]').count(), 0);
  assert.match(await page.locator('#comparison-text').textContent(), /≠/);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: review('reduced-motion.png') });
  const popupEvent = page.waitForEvent('popup');
  await page.keyboard.press('s');
  const speaker = await popupEvent;
  await speaker.waitForLoadState('domcontentloaded');
  await speaker.waitForFunction(() => document.querySelector('.speaker-controls-notes')?.textContent.includes('Raspberry Pi VM'));
  assert.match(await speaker.title(), /Speaker View/);
  await speaker.close();
  // File URL also loads with no remote assets; speaker notes use HTTP above.
  const offline = await context.newPage();
  await offline.goto(`file://${path.join(__dirname, 'index.html')}`);
  await offline.waitForFunction(() => window.Reveal?.isReady());
  assert.equal(await offline.locator('.notes').count(), 2);
  assert.equal(requests.filter(url => !url.startsWith('http://127.0.0.1:8000/')).length, 0);
  assert.deepEqual(errors, []);
  console.log('PASS: two slides, local fonts/assets, navigation, pause/resume, hidden-slide/overview/blackout suspension, 3 loops, stable baseline/node count, projector/mobile captures, reduced motion, speaker view, and file-URL loading.');
  await browser.close();
})().catch(async error => { console.error(error); process.exitCode = 1; await browser?.close(); });
