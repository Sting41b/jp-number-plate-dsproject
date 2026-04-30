const DATA_DIR = '../data/clean';

const PLATE_COLORS = {
  '白地緑文字':         { bg: '#ffffff', fg: '#1e5e1e', label: '白' },
  '黄地黒文字':         { bg: '#f4c500', fg: '#000000', label: '黄' },
  '緑地白文字':         { bg: '#1e5e1e', fg: '#ffffff', label: '緑' },
  '白地に外字・赤文字': { bg: '#ffffff', fg: '#c7352f', label: '外' },
};

async function loadJSON(name) {
  const res = await fetch(`${DATA_DIR}/${name}`);
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}

async function loadAll() {
  const [summary, chimei, bunrui, hiragana, gotochi] = await Promise.all([
    loadJSON('summary.json'),
    loadJSON('chimei.json'),
    loadJSON('bunrui_bangou.json'),
    loadJSON('hiragana.json'),
    loadJSON('gotochi.json'),
  ]);

  renderStats(summary);
  renderFindings({ chimei, hiragana, gotochi });
  renderChimei(chimei);
  renderBunrui(bunrui);
  renderHiragana(hiragana);
  renderGotochi(gotochi);
  renderSources(summary);
  initTabs();
}

function activateTab(tabId) {
  const buttons = document.querySelectorAll('.tab-btn');
  const panels  = document.querySelectorAll('.tab-panel');
  buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  panels.forEach(p => p.classList.toggle('active', p.id === tabId));
  const target = document.getElementById(tabId);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderStats(s) {
  const cards = [
    { num: s.total_chimei,        label: '地名 places' },
    { num: s.total_gotochi,       label: 'ご当地 plates' },
    { num: s.hiragana_used,       label: 'hiragana used' },
    { num: s.hiragana_excluded,   label: 'hiragana excluded' },
  ];
  document.getElementById('stats').innerHTML = cards.map(c =>
    `<div class="stat-card">
       <div class="stat-num">${c.num}</div>
       <div class="stat-label">${c.label}</div>
     </div>`
  ).join('');
}

function renderChimei(rows) {
  const tbody = document.querySelector('#chimei-table tbody');
  const meta  = document.getElementById('chimei-meta');
  const input = document.getElementById('chimei-search');

  function draw(filtered) {
    tbody.innerHTML = filtered.map(r =>
      `<tr>
         <td><strong>${escapeHtml(r.chimei)}</strong></td>
         <td>${escapeHtml(r.office || '—')}</td>
         <td>${escapeHtml(r.prefecture || '—')}</td>
       </tr>`
    ).join('');
    meta.textContent = `Showing ${filtered.length} of ${rows.length} 地名`;
  }

  draw(rows);

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { draw(rows); return; }
    draw(rows.filter(r =>
      r.chimei.toLowerCase().includes(q) ||
      (r.office || '').toLowerCase().includes(q) ||
      (r.prefecture || '').toLowerCase().includes(q)
    ));
  });
}

function renderBunrui(rows) {
  const tbody = document.querySelector('#bunrui-table tbody');
  tbody.innerHTML = rows.map(r => {
    const color = PLATE_COLORS[r.plate_color] || { bg: '#fff', fg: '#000', label: '?' };
    const swatch = `<span class="color-swatch" style="background:${color.bg};color:${color.fg}">${color.label}</span>`;
    return `<tr>
      <td><strong>${escapeHtml(r.label)}</strong>${r.first_digit_label && r.first_digit_label !== 'special' ? `<br><small>${escapeHtml(r.first_digit_label)}</small>` : ''}</td>
      <td>${escapeHtml(r.vehicle_type_ja)}<br><small>${escapeHtml(r.vehicle_type_en)}</small></td>
      <td>${swatch}<small>${escapeHtml(r.plate_color_en)}</small></td>
      <td><small>${escapeHtml(r.notes || '')}</small></td>
    </tr>`;
  }).join('');
}

function renderHiragana(data) {
  const grid = document.getElementById('hiragana-grid');
  const meta = document.getElementById('hiragana-meta');

  grid.innerHTML = data.characters.map(h => {
    const cls = h.status === 'used' ? 'used' : 'excluded';
    const reason = h.exclusion_reason
      ? ` data-reason="${escapeHtml(h.exclusion_reason)} (${escapeHtml(h.category)})"`
      : '';
    return `<div class="kana-cell ${cls}"${reason}>${escapeHtml(h.kana)}</div>`;
  }).join('');

  const s = data.stats;
  const pct = (s.exclusion_rate * 100).toFixed(1);
  meta.textContent =
    `${s.used_count} of ${s.total_gojuuon} gojūon used · ${s.excluded_count} excluded (${pct}%)`;
}

function renderGotochi(data) {
  // Group by date, build cumulative series.
  const byDate = {};
  for (const p of data.plates) {
    byDate[p.issue_date] = (byDate[p.issue_date] || 0) + 1;
  }
  const dates = Object.keys(byDate).sort();
  const cumulative = [];
  let running = 0;
  for (const d of dates) {
    running += byDate[d];
    cumulative.push(running);
  }

  new Chart(document.getElementById('gotochi-chart'), {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: 'Cumulative ご当地 plates',
        data: cumulative,
        borderColor: '#c7352f',
        backgroundColor: 'rgba(199, 53, 47, 0.15)',
        fill: true,
        stepped: true,
        pointRadius: 6,
        pointHoverRadius: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, title: { display: true, text: 'Cumulative count' } },
        x: { title: { display: true, text: 'Issue date' } },
      },
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const date = ctx.label;
              const added = byDate[date] || 0;
              return `(+${added} on this date)`;
            },
          },
        },
      },
    },
  });

  const tbody = document.querySelector('#gotochi-waves tbody');
  tbody.innerHTML = data.wave_summary.map(w =>
    `<tr>
      <td><strong>Wave ${escapeHtml(w.wave)}</strong></td>
      <td>${escapeHtml(w.issue_date)}</td>
      <td>${escapeHtml(w.count)}</td>
      <td><small>${escapeHtml(w.regions.join(', '))}</small></td>
    </tr>`
  ).join('');
}

function renderFindings({ chimei, hiragana, gotochi }) {
  // Card 1: hiragana exclusion taxonomy. Pull the categorised counts straight
  // from the cleaned hiragana stats — no recomputation in the browser.
  const cats = hiragana.stats.exclusion_categories || {};
  // Display order: visual (3), semantic (2), phonetic (1) — descending count.
  const catOrder = ['visual', 'semantic', 'phonetic'];
  const maxCount = Math.max(1, ...catOrder.map(c => (cats[c] || {}).count || 0));
  const barRows = catOrder.map(c => {
    const entry = cats[c] || { count: 0, examples: [] };
    const widthPct = (entry.count / maxCount) * 100;
    return `<div class="bar-row">
      <span class="bar-label">${escapeHtml(c)}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${widthPct}%"></span></span>
      <span class="bar-examples">${entry.examples.map(escapeHtml).join(' ')}</span>
    </div>`;
  }).join('');

  // Card 2: gotochi wave gaps. Compute year-gaps between consecutive wave
  // start dates so the card states the staircase pattern in plain numbers.
  const waves = (gotochi.wave_summary || []).slice().sort((a, b) =>
    a.issue_date.localeCompare(b.issue_date)
  );
  const gaps = [];
  for (let i = 1; i < waves.length; i++) {
    const prev = new Date(waves[i - 1].issue_date);
    const curr = new Date(waves[i].issue_date);
    gaps.push(((curr - prev) / (365.25 * 24 * 3600 * 1000)).toFixed(1));
  }
  const waveYears = waves.map(w => w.issue_date.slice(0, 4)).join(' → ');
  const gapText = gaps.length
    ? gaps.map((g, i) => `${g}y between Wave ${i + 1} and Wave ${i + 2}`).join('; ')
    : 'no gap data';

  // Card 3: cross-office chimei. Group by chimei in the browser — small data,
  // not worth pre-computing in the pipeline.
  const officesByChimei = {};
  for (const r of chimei) {
    if (!officesByChimei[r.chimei]) officesByChimei[r.chimei] = new Set();
    officesByChimei[r.chimei].add(r.office);
  }
  const crossOffice = Object.entries(officesByChimei)
    .filter(([, offices]) => offices.size > 1)
    .map(([name, offices]) => ({ name, offices: [...offices] }));

  const cards = [
    {
      tab: 'hiragana',
      title: '6 hiragana, 3 kinds of failure',
      body: 'Of 46 gojūon, 6 are excluded — and the exclusions group cleanly into three different design problems: visual confusables, grammatical particles, and a moraic nasal with no standalone sound.',
      visual: `<div class="bar-chart">${barRows}</div>`,
    },
    {
      tab: 'gotochi',
      title: 'Rollouts come in policy bursts',
      body: `The ご当地 scheme has issued 119 plates across ${waves.length} waves (${escapeHtml(waveYears)}) — ${escapeHtml(gapText)}. The cumulative curve is a staircase, not a slope.`,
      visual: `<div class="step-mini" aria-hidden="true">
        <span class="step-bar" style="height:30%"></span>
        <span class="step-bar" style="height:65%"></span>
        <span class="step-bar" style="height:100%"></span>
      </div>`,
    },
    {
      tab: 'chimei',
      title: 'A few names cross prefecture lines',
      body: `Most chimei map 1-to-1 to a single 運輸支局, but ${crossOffice.length} (${crossOffice.map(c => c.name).join(', ')}) are deliberately shared by two — the plate name follows geography, not the administrative line.`,
      visual: `<ul class="cross-list">${crossOffice.map(c =>
        `<li><strong>${escapeHtml(c.name)}</strong><br><small>${c.offices.map(escapeHtml).join(' + ')}</small></li>`
      ).join('')}</ul>`,
    },
  ];

  document.getElementById('findings-grid').innerHTML = cards.map(c =>
    `<article class="finding-card" data-tab="${escapeHtml(c.tab)}" tabindex="0" role="button" aria-label="View ${escapeHtml(c.title)} tab">
       <h3 class="finding-title">${escapeHtml(c.title)}</h3>
       <p class="finding-body">${c.body}</p>
       <div class="finding-visual">${c.visual}</div>
       <span class="finding-cta">Explore →</span>
     </article>`
  ).join('');
}

function renderSources(s) {
  const el = document.getElementById('sources');
  const links = s.data_sources.map(src =>
    `<a href="${escapeHtml(src.url)}" target="_blank" rel="noopener">${escapeHtml(src.name)}</a>`
  );
  el.innerHTML = 'Data sources: ' + links.join(' · ');
}

function initTabs() {
  const buttons = document.querySelectorAll('.tab-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab));
  });
  document.querySelectorAll('.finding-card[data-tab]').forEach(card => {
    card.addEventListener('click', () => activateTab(card.dataset.tab));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateTab(card.dataset.tab);
      }
    });
  });
}

loadAll().catch(err => {
  console.error(err);
  document.body.innerHTML =
    `<div class="loading-error">
       <strong>Failed to load dashboard data.</strong><br>
       ${escapeHtml(err.message)}<br>
       <small>The dashboard must be served over HTTP (e.g.
       <code>python -m http.server 8000</code> from the project root) —
       opening index.html directly via file:// will not work.</small>
     </div>`;
});
