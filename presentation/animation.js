/* Illustrative choreography, not live attestation or blockchain traffic. */
(() => {
  'use strict';
  const svg = document.querySelector('#system-diagram');
  const ns = 'http://www.w3.org/2000/svg';
  const colors = { digest: '#214be0', sensor: '#08766b', alert: '#c43e2d' };
  const trustedDigest = '2f9a·7c31';
  const changedDigest = 'b814·0de6';
  const hex = '0123456789abcdef';
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const scenarios = [
    {
      duration: 20,
      actions: ['Collect device parameters', 'Generate SHA-256 I2Map', 'Register trusted baseline', 'Send runtime I2Map to chain', 'Receive hashes & compare', 'Accept sensor data'],
      steps: [
        { end:1.6, action:0, routes:'approve parameter' },
        { end:3, action:1, routes:'digest' },
        { end:6.2, action:2, routes:'submit' },
        { end:7, action:2, routes:'store' },
        { end:8, action:2, routes:'store', settled:true },
        { end:9, action:0, routes:'parameter' },
        { end:10.2, action:1, routes:'digest' },
        { end:13, action:3, routes:'submit sensor' },
        { end:14, action:4, routes:'forward' },
        { end:15, action:4, routes:'baseline' },
        { end:15.8, action:4, routes:'', status:'Comparing I2Maps' },
        { end:20, action:5, routes:'accept consumer', result:'match' }
      ]
    },
    {
      duration: 22,
      actions: ['Detect USB state change', 'Hash & submit changed I2Map', 'Receive hashes & compare', 'Reject sensor data', 'Notify administrator', 'Restore approved state'],
      steps: [
        { end:1.4, action:0, routes:'parameter' },
        { end:2.1, action:1, routes:'digest' },
        { end:4.7, action:1, routes:'submit sensor' },
        { end:5.7, action:2, routes:'forward' },
        { end:6.7, action:2, routes:'baseline' },
        { end:7.4, action:2, routes:'', status:'Comparing I2Maps' },
        { end:8.4, action:3, routes:'reject', result:'mismatch' },
        { end:12.7, action:4, routes:'alert', result:'mismatch' },
        { end:14.2, action:5, routes:'approve' },
        { end:15.2, action:5, routes:'parameter' },
        { end:15.8, action:5, routes:'digest' },
        { end:18.4, action:5, routes:'submit sensor' },
        { end:19.1, action:5, routes:'forward' },
        { end:19.8, action:5, routes:'baseline' },
        { end:20.3, action:5, routes:'', status:'Comparing I2Maps' },
        { end:22, action:5, routes:'accept consumer', result:'match' }
      ]
    }
  ];

  function make(tag, attrs, parent) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    parent.appendChild(el);
    return el;
  }

  // Allocate all animated nodes once. Frames only change attributes and text.
  const packetLayer = document.querySelector('#packet-layer');
  // Sample once, then interpolate: no repeated SVG geometry queries per frame.
  const paths = Object.fromEntries([...svg.querySelectorAll('.connections path')].map(path => {
    const length = path.getTotalLength();
    const samples = Array.from({ length: 160 }, (_, i) => {
      const point = path.getPointAtLength(i / 159 * length);
      return { x: point.x, y: point.y };
    });
    return [path.id, { length, samples }];
  }));
  const ui = {
    list: document.querySelector('#activity-list'), panel: document.querySelector('.activity-panel'),
    options: [...document.querySelectorAll('.scenario-options button')],
    previous: document.querySelector('#previous-scenario'), next: document.querySelector('#next-scenario'),
    baseline: document.querySelector('#baseline-digest'), tamper: document.querySelector('#tamper-marker'),
    comparison: document.querySelector('#comparison-text'), ledger: [...document.querySelectorAll('#ledger-bars rect')],
    ripple: document.querySelector('#storage-ripple rect'),
    routeElements: [...svg.querySelectorAll('.connections path, [data-routes]')]
  };
  function packet(pathId, kind, offset = 0) {
    const group = make('g', { visibility: 'hidden', 'data-route': pathId, 'data-kind': kind }, packetLayer);
    const color = colors[kind] || colors.digest;
    const compact = paths[pathId].length < 60;
    if (kind === 'sensor' && compact) {
      make('circle', { r: 4, fill: color }, group);
    } else if (kind === 'raw') {
      make('rect', { x: -28, y: -11, width: 56, height: 22, rx: 4, fill: '#f4f1e9', stroke: color }, group);
      const label = make('text', { x: 0, y: 4, 'text-anchor': 'middle', style: `font:11px monospace;fill:${color}` }, group);
      label.textContent = ['USB:03', 'OS:6.6', 'NET:01'][offset % 3];
    } else if (kind === 'digest') {
      make('circle', { r: 11, fill: '#e6ebfc', stroke: color, 'stroke-width': 1.3 }, group);
      const glyphs = [];
      for (let i = 0; i < 7; i++) {
        const angle = i * Math.PI * 2 / 7;
        glyphs.push(make('text', { x: Math.cos(angle) * 7, y: Math.sin(angle) * 7 + 2, 'text-anchor': 'middle', style: `font:7px monospace;fill:${color}` }, group));
      }
      group.glyphs = glyphs;
    } else if (kind === 'sensor') {
      make('rect', { x: -22, y: -11, width: 44, height: 22, rx: 4, fill: '#e2eee5', stroke: color }, group);
      make('text', { x: 0, y: 4, 'text-anchor': 'middle', style: `font:11px monospace;fill:${color}` }, group).textContent = '24.1';
    } else {
      make('path', { d: 'M0-11L11 8H-11Z', fill: color }, group);
      make('path', { d: 'M0-4V1M0 4V5', stroke: '#f4f1e9', 'stroke-width': 1.7 }, group);
    }
    return { group, pathId, kind, offset, label: group.querySelector('text'), lastGlyphFrame: -1,
      inset: compact ? 6 : kind === 'raw' ? 28 : kind === 'sensor' ? 24 : 14 };
  }

  const packets = [
    packet('parameter-path', 'raw'),
    packet('digest-path', 'digest'),
    packet('submit-path', 'digest'),
    packet('store-path', 'digest'), packet('forward-path', 'digest'),
    packet('baseline-path', 'digest'), packet('sensor-path', 'sensor'),
    packet('accept-path', 'sensor'), packet('consumer-path', 'sensor'),
    packet('reject-path', 'sensor'), packet('alert-path', 'alert'), packet('approve-path', 'digest')
  ];
  const cloud = [];
  const cloudParent = make('g', {}, document.querySelector('#hash-cloud'));
  for (let i = 0; i < 20; i++) {
    const angle = i / 20 * Math.PI * 2;
    const radius = 49 + Math.sin(i * 5) * 5;
    cloud.push(make('text', { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius,
      'text-anchor': 'middle', style: 'font:9px monospace;fill:#f4f1e9;opacity:.55' }, cloudParent));
  }
  let cloudFrame = -1;
  const smoothStep = value => value * value * (3 - 2 * value);

  function drawPacket(p, progress, clock, tampered = false) {
    const visible = progress !== null && !reduceMotion.matches;
    p.group.setAttribute('visibility', visible ? 'visible' : 'hidden');
    if (!visible) return;
    const route = paths[p.pathId];
    const distance = p.inset + progress * (route.length - p.inset);
    const sampleIndex = distance / route.length * 159;
    const low = Math.min(158, Math.floor(sampleIndex));
    const fraction = sampleIndex - low;
    const a = route.samples[low], b = route.samples[low + 1];
    p.group.setAttribute('transform', `translate(${a.x + (b.x - a.x) * fraction} ${a.y + (b.y - a.y) * fraction})`);
    const fade = Math.min(1, progress / .16);
    p.group.style.opacity = smoothStep(Math.max(0, fade));
    const glyphFrame = Math.floor(clock * 8);
    if (p.kind === 'raw' && p.lastGlyphFrame !== glyphFrame) {
      p.label.textContent = tampered ? 'USB:04' : ['USB:03', 'OS:6.6', 'NET:01'][Math.floor(clock / 3) % 3];
    }
    if (p.kind === 'sensor' && p.pathId === 'reject-path') {
      p.group.firstChild.setAttribute('stroke', colors.alert);
      p.label.style.fill = colors.alert;
    }
    if (p.group.glyphs && p.lastGlyphFrame !== glyphFrame) {
      p.group.glyphs.forEach((glyph, i) => {
        glyph.textContent = hex[(Math.floor(clock * 6) + i * 5 + p.offset * 3) % 16];
        glyph.style.fill = tampered ? colors.alert : colors.digest;
      });
      p.group.firstChild.setAttribute('stroke', tampered ? colors.alert : colors.digest);
    }
    p.lastGlyphFrame = glyphFrame;
  }
  // Shared distance-based speed and a quiet handoff between successive packets.
  function flow(p, time, windowLength, speed = 90) {
    const duration = paths[p.pathId].length / speed;
    const period = duration + .55;
    const cycleStart = Math.floor(time / period) * period;
    const available = windowLength - cycleStart;
    if (available < .2) return null;
    const flight = Math.min(duration, available - .08);
    const position = time - cycleStart;
    return position <= flight + .08 ? Math.min(1, position / flight) : null;
  }
  const travel = (time, start, end) => time >= start && time <= end ? Math.min(1, (time - start) / (end - start - .08)) : null;

  let scenarioIndex = 0;
  let elapsed = 0;
  let previousTime = null;
  let frameId = null;
  let paused = false;
  let lastStep = -1;
  let lastReducedFrame = -1;

  function selectScenario(index) {
    if (index < 0 || index >= scenarios.length) return;
    scenarioIndex = index;
    elapsed = 0;
    paused = false;
    lastStep = -1;
    ui.list.replaceChildren(...scenarios[index].actions.map(label => {
      const item = document.createElement('li');
      const marker = document.createElement('span');
      marker.className = 'activity-marker';
      marker.setAttribute('aria-hidden', 'true');
      const icon = make('svg', { viewBox:'0 0 12 12' }, marker);
      make('path', { d:'M2 6L5 9L10 3' }, icon);
      item.append(marker, document.createTextNode(label));
      return item;
    }));
    ui.options.forEach((option, i) => option.setAttribute('aria-pressed', String(i === index)));
    ui.previous.disabled = index === 0;
    ui.next.disabled = index === 1;
    render(0);
    synchronize();
  }

  function render(seconds) {
    const scenario = scenarios[scenarioIndex];
    const t = seconds % scenario.duration;
    const stepIndex = scenario.steps.findIndex(step => t < step.end);
    const step = scenario.steps[stepIndex];
    const start = stepIndex ? scenario.steps[stepIndex - 1].end : 0;
    const phase = scenarioIndex === 0 ? (t < 8 ? 'onboarding' : 'matching') : (step.action < 5 ? 'tampered' : 'restoring');
    const tampered = phase === 'tampered';
    const stored = scenarioIndex === 1 || t >= 7;
    const result = step.result || 'pending';
    const activeRoutes = new Set(step.routes.split(' ').filter(Boolean).map(route => `${route}-path`));
    if (stepIndex !== lastStep) {
      svg.dataset.scenario = String(scenarioIndex);
      svg.dataset.phase = phase;
      svg.dataset.outcome = result;
      svg.dataset.step = String(step.action);
      ui.panel.dataset.phase = phase;
      ui.tamper.setAttribute('visibility', tampered ? 'visible' : 'hidden');
      const completed = new Set(scenario.steps.slice(0, stepIndex).map(previous => previous.action));
      [...ui.list.children].forEach((item, i) => {
        item.classList.toggle('active', i === step.action);
        item.classList.toggle('done', completed.has(i) && i !== step.action);
        if (i === step.action) item.setAttribute('aria-current', 'step');
        else item.removeAttribute('aria-current');
      });
      ui.routeElements.forEach(el => {
        const routes = el.dataset.routes?.split(' ') || [el.id];
        el.classList.toggle('route-active', routes.some(route => activeRoutes.has(route)));
      });
      ui.baseline.textContent = stored ? trustedDigest : '—';
      ui.comparison.textContent = result === 'match' ? `${trustedDigest} = ${trustedDigest}`
        : result === 'mismatch' ? `${changedDigest} ≠ ${trustedDigest}`
        : step.status || (activeRoutes.has('forward-path') ? 'Receiving runtime I2Map'
          : activeRoutes.has('baseline-path') ? 'Receiving baseline'
          : stored ? 'Awaiting runtime I2Map' : 'Baseline onboarding');
      ui.ledger.forEach(el => el.style.fill = stored ? colors.digest : '#d2d3c8');
      lastStep = stepIndex;
    }
    const rippleProgress = scenarioIndex === 0 && t >= 7 && t < 8 ? t - 7 : null;
    ui.ripple.style.opacity = rippleProgress === null || reduceMotion.matches ? 0 : (1 - rippleProgress) * .8;
    if (rippleProgress !== null) ui.ripple.setAttribute('transform', `translate(1345 349) scale(${1 + rippleProgress * .04}) translate(-1345 -349)`);
    cloudParent.setAttribute('transform', `translate(392 305) rotate(${reduceMotion.matches ? 0 : seconds * 12})`);
    const nextCloudFrame = Math.floor(reduceMotion.matches ? 0 : seconds * 8);
    if (nextCloudFrame !== cloudFrame) {
      cloud.forEach((glyph, i) => glyph.textContent = hex[(i * 7 + nextCloudFrame) % 16]);
      cloudFrame = nextCloudFrame;
    }
    packets.forEach(p => {
      let progress = null;
      if (activeRoutes.has(p.pathId) && !step.settled) {
        // Administrative and chain operations make one complete journey; client streams repeat.
        progress = ['submit-path', 'store-path', 'forward-path', 'baseline-path', 'alert-path', 'approve-path', 'reject-path'].includes(p.pathId)
          ? travel(t, start, step.end) : flow(p, t - start, step.end - start);
      }
      drawPacket(p, progress, seconds, tampered && ['parameter-path', 'digest-path', 'submit-path', 'forward-path', 'reject-path'].includes(p.pathId));
    });
  }

  function eligible() {
    return Reveal.isReady() && !paused && !document.hidden && Reveal.getCurrentSlide()?.id === 'methodology' && !Reveal.isOverview() && !Reveal.isPaused();
  }
  function tick(now) {
    frameId = null;
    if (!eligible()) { previousTime = null; return; }
    if (previousTime !== null) elapsed += Math.min((now - previousTime) / 1000, .1);
    previousTime = now;
    if (!reduceMotion.matches || now - lastReducedFrame >= 250) {
      render(elapsed);
      lastReducedFrame = now;
    }
    frameId = requestAnimationFrame(tick);
  }
  function synchronize() {
    if (frameId !== null) cancelAnimationFrame(frameId);
    frameId = null;
    previousTime = null;
    if (eligible()) frameId = requestAnimationFrame(tick);
  }

  const evidence = document.querySelector('.problem-evidence');
  const statistics = [...document.querySelectorAll('.stat-value')];
  let countFrame = null;
  const blastPaths = [...document.querySelectorAll('.blast-lines path')];
  document.querySelectorAll('.blast-dot').forEach((dot, index) => {
    dot.style.offsetPath = `path("${blastPaths[index].getAttribute('d')}")`;
    dot.setAttribute('cx', 0);
    dot.setAttribute('cy', 0);
    dot.setAttribute('aria-hidden', 'true');
  });
  function problemActive() {
    return Reveal.isReady() && Reveal.getCurrentSlide()?.id === 'problem' &&
      !document.hidden && !Reveal.isOverview() && !Reveal.isPaused();
  }
  function settleStatistics() {
    if (countFrame !== null) cancelAnimationFrame(countFrame);
    countFrame = null;
    statistics.forEach(stat => stat.textContent = stat.dataset.target);
  }
  function synchronizeOpening() {
    const active = problemActive();
    document.body.classList.toggle('problem-motion', active && !reduceMotion.matches);
    if (!active || reduceMotion.matches || !evidence.classList.contains('visible')) settleStatistics();
  }
  function countStatistics() {
    settleStatistics();
    if (!problemActive() || reduceMotion.matches) return;
    statistics.forEach(stat => stat.textContent = '0');
    const start = performance.now();
    function count(now) {
      const progress = Math.min(1, (now - start) / 900);
      const eased = 1 - (1 - progress) ** 3;
      statistics.forEach(stat => stat.textContent = Math.round(Number(stat.dataset.target) * eased));
      countFrame = progress < 1 ? requestAnimationFrame(count) : null;
    }
    countFrame = requestAnimationFrame(count);
  }
  Reveal.on('fragmentshown', event => {
    if (event.fragment === evidence) countStatistics();
  });
  function updateNav() {
    const index = Reveal.getIndices().h;
    const fragments = Reveal.availableFragments();
    document.querySelector('#slide-count').textContent = `${index + 1} / ${Reveal.getTotalSlides()}`;
    document.querySelector('#previous-slide').disabled = index === 0 && !fragments.prev;
    document.querySelector('#next-slide').disabled = Reveal.isLastSlide() && !fragments.next;
    synchronize();
    synchronizeOpening();
  }
  ui.options.forEach((option, index) => option.addEventListener('click', () => selectScenario(index)));
  ui.previous.addEventListener('click', () => selectScenario(scenarioIndex - 1));
  ui.next.addEventListener('click', () => selectScenario(scenarioIndex + 1));
  document.addEventListener('keydown', event => {
    if (Reveal.getCurrentSlide()?.id !== 'methodology' || Reveal.isOverview() || Reveal.isOverlayOpen()) return;
    if (!['Space', 'ArrowUp', 'ArrowDown'].includes(event.code)) return;
    if (event.target.matches('input, textarea, select') || event.target.isContentEditable) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (event.repeat) return;
    if (event.code === 'Space') { paused = !paused; synchronize(); }
    else selectScenario(scenarioIndex + (event.code === 'ArrowUp' ? -1 : 1));
  }, true);
  document.querySelector('#previous-slide').addEventListener('click', () => Reveal.prev());
  document.querySelector('#next-slide').addEventListener('click', () => Reveal.next());
  document.addEventListener('visibilitychange', () => { synchronize(); synchronizeOpening(); });
  reduceMotion.addEventListener('change', () => { render(elapsed); synchronize(); synchronizeOpening(); });
  for (const event of ['slidechanged', 'fragmentshown', 'fragmenthidden', 'overviewshown', 'overviewhidden', 'paused', 'resumed']) Reveal.on(event, updateNav);
  selectScenario(0);
  Reveal.initialize({ width: 1600, height: 900, margin: .02, minScale: .1, maxScale: 2,
    controls: false, progress: true, hash: true, center: false, transition: 'fade', transitionSpeed: 'fast',
    keyboard: true, touch: true, autoSlide: 0, disableLayout: false, plugins: [RevealNotes],
    scrollActivationWidth: null
  }).then(updateNav);

})();
