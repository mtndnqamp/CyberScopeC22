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
  const phaseText = {
    onboarding: ['Onboarding', 'Collect known-good state and register the approved baseline.'],
    matching: ['Runtime · unchanged', 'The runtime digest matches. Release the sensor reading.'],
    tampered: ['Runtime · USB tampering', 'A new peripheral changes the digest. Reject data and notify the administrator.'],
    restoring: ['Approved restoration', 'The administrator restores the approved state. Runtime checks resume.']
  };

  function stateAt(seconds) {
    const time = ((seconds % 30) + 30) % 30;
    const phase = time < 8 ? 'onboarding' : time < 17 ? 'matching' : time < 26 ? 'tampered' : 'restoring';
    const result = (time >= 11 && time < 17) || time >= 28.5 ? 'match' : time >= 20.5 && time < 26 ? 'mismatch' : 'pending';
    return { time, phase, result, stored: time >= 7, tampered: time >= 17 && time < 26 };
  }

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
    phase: document.querySelector('#phase-name'), description: document.querySelector('#phase-description'),
    tabs: [...document.querySelectorAll('.phase-track [data-phase]')],
    baseline: document.querySelector('#baseline-digest'), tamper: document.querySelector('#tamper-marker'),
    comparison: document.querySelector('#comparison-text'), ledger: [...document.querySelectorAll('#ledger-bars rect')],
    ripple: document.querySelector('#storage-ripple rect')
  };
  function packet(pathId, kind, offset = 0) {
    const group = make('g', { visibility: 'hidden', 'data-route': pathId, 'data-kind': kind }, packetLayer);
    const color = colors[kind] || colors.digest;
    const compact = paths[pathId].length < 60;
    if (kind === 'reference' || (kind === 'sensor' && compact)) {
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
    ...[0, 1].map(i => packet('digest-path', 'digest', i)),
    packet('onboard-path', 'digest'), packet('register-path', 'digest'),
    ...[0, 1].map(i => packet('submit-path', 'digest', i)),
    packet('baseline-path', 'reference'), packet('sensor-path', 'sensor'),
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
    const distance = p.inset + progress * Math.max(0, route.length - p.inset * 2);
    const sampleIndex = distance / route.length * 159;
    const low = Math.min(158, Math.floor(sampleIndex));
    const fraction = sampleIndex - low;
    const a = route.samples[low], b = route.samples[low + 1];
    p.group.setAttribute('transform', `translate(${a.x + (b.x - a.x) * fraction} ${a.y + (b.y - a.y) * fraction})`);
    const fade = Math.min(1, progress / .16, (1 - progress) / .16);
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
  function flow(p, time, speed = 90) {
    const duration = paths[p.pathId].length / speed;
    const period = duration + .55;
    const position = ((time + p.offset * period / 2) % period + period) % period;
    return position <= duration ? position / duration : null;
  }
  const travel = (time, start, end) => time >= start && time <= end ? (time - start) / (end - start) : null;

  let elapsed = 0;
  let previousTime = null;
  let frameId = null;
  let paused = false;
  let hasStoredBaseline = false;
  let lastPhase = '';
  let lastResult = '';
  let lastReducedFrame = -1;
  let lastOutcome = '';
  let lastBaseline = '';

  function render(seconds) {
    const state = stateAt(seconds);
    const t = state.time;
    hasStoredBaseline ||= state.stored || seconds >= 30;
    if (state.result !== lastOutcome) {
      svg.dataset.outcome = state.result;
      lastOutcome = state.result;
    }
    if (state.phase !== lastPhase) {
      svg.dataset.phase = state.phase;
      const [title, description] = phaseText[state.phase];
      ui.phase.textContent = title;
      ui.description.textContent = description;
      ui.tabs.forEach(el => el.classList.toggle('active', el.dataset.phase === state.phase));
      ui.tamper.setAttribute('visibility', state.tampered ? 'visible' : 'hidden');
      lastPhase = state.phase;
    }
    const baseline = hasStoredBaseline ? trustedDigest : '—';
    if (baseline !== lastBaseline) { ui.baseline.textContent = baseline; lastBaseline = baseline; }
    const compare = state.result === 'match' ? `${trustedDigest} = ${trustedDigest}` : state.result === 'mismatch' ? `${changedDigest} ≠ ${trustedDigest}` : hasStoredBaseline ? 'Collecting runtime I2Map' : 'Registering Base I2Map';
    if (compare !== lastResult) {
      ui.comparison.textContent = compare;
      lastResult = compare;
    }
    ui.ledger.forEach((el, i) => el.style.fill = hasStoredBaseline ? colors.digest : t > 5 + i * .6 ? colors.digest : '#d2d3c8');
    const storedProgress = travel(t, 7, 8);
    const ripple = ui.ripple;
    ripple.style.opacity = storedProgress === null || reduceMotion.matches ? 0 : (1 - storedProgress) * .8;
    if (storedProgress !== null) {
      ripple.setAttribute('transform', `translate(988 241) scale(${1 + storedProgress * .04}) translate(-988 -241)`);
    }
    cloudParent.setAttribute('transform', `translate(392 305) rotate(${reduceMotion.matches ? 0 : seconds * 12})`);
    const nextCloudFrame = Math.floor(reduceMotion.matches ? 0 : seconds * 8);
    if (nextCloudFrame !== cloudFrame) {
      cloud.forEach((glyph, i) => glyph.textContent = hex[(i * 7 + nextCloudFrame) % 16]);
      cloudFrame = nextCloudFrame;
    }
    packets.forEach(p => {
      let progress = null;
      switch (p.pathId) {
        case 'parameter-path': progress = flow(p, seconds, 70); break;
        case 'digest-path': progress = flow(p, seconds); break;
        case 'onboard-path': progress = travel(t, 1.6, 4.4); break;
        case 'register-path': progress = travel(t, 4.4, 7); break;
        case 'submit-path': progress = t >= 8 ? flow(p, seconds) : null; break;
        case 'baseline-path': progress = t >= 8 ? flow(p, seconds, 45) : null; break;
        case 'sensor-path': progress = t >= 8 ? flow(p, seconds) : null; break;
        case 'accept-path': progress = state.result === 'match' ? flow(p, seconds) : null; break;
        case 'consumer-path': progress = state.result === 'match' ? flow(p, seconds, 45) : null; break;
        case 'reject-path': progress = travel(t, 20.5, 21.5); break;
        case 'alert-path': progress = travel(t, 21.5, 26); break;
        case 'approve-path': progress = travel(t, 26, 27.5); break;
      }
      drawPacket(p, progress, seconds, state.tampered && ['parameter-path', 'digest-path', 'submit-path', 'reject-path'].includes(p.pathId));
    });
  }

  function eligible() {
    return !paused && !document.hidden && Reveal.getCurrentSlide()?.id === 'methodology' && !Reveal.isOverview() && !Reveal.isPaused();
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
  function updateNav() {
    const index = Reveal.getIndices().h;
    document.querySelector('#slide-count').textContent = `${index + 1} / 2`;
    document.querySelector('#previous-slide').disabled = index === 0;
    document.querySelector('#next-slide').disabled = index === 1;
    synchronize();
  }
  const toggle = document.querySelector('#motion-toggle');
  toggle.addEventListener('click', () => {
    paused = !paused;
    toggle.setAttribute('aria-pressed', String(paused));
    toggle.setAttribute('aria-label', `${paused ? 'Resume' : 'Pause'} diagram animation`);
    toggle.querySelector('span').textContent = paused ? 'Resume' : 'Pause';
    document.querySelector('#motion-symbol').setAttribute('d', paused ? 'M5 3L16 10L5 17Z' : 'M6 4V16M14 4V16');
    synchronize();
  });
  document.querySelector('#previous-slide').addEventListener('click', () => Reveal.prev());
  document.querySelector('#next-slide').addEventListener('click', () => Reveal.next());
  document.addEventListener('visibilitychange', synchronize);
  reduceMotion.addEventListener('change', () => { render(elapsed); synchronize(); });
  for (const event of ['slidechanged', 'overviewshown', 'overviewhidden', 'paused', 'resumed']) Reveal.on(event, updateNav);
  render(0);
  Reveal.initialize({ width: 1600, height: 900, margin: .02, minScale: .1, maxScale: 2,
    controls: false, progress: true, hash: true, center: false, transition: 'fade', transitionSpeed: 'fast',
    keyboard: true, touch: true, autoSlide: 0, disableLayout: false, plugins: [RevealNotes],
    scrollActivationWidth: null
  }).then(updateNav);

  // Small deterministic inspection interface used by the browser verification.
  window.CyberScopePreview = {
    stateAt,
    seek(seconds) { elapsed = seconds; render(elapsed); },
    getState() { return { ...stateAt(elapsed), elapsed, paused, running: frameId !== null, packetCount: packets.length }; }
  };
})();
