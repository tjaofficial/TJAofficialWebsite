(() => {
  const $ = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  const table = $('.cp-table');
  if (!table) return;

  // ── Build toolbar (search + vibe filter + reset) ─────────────────────────────
  const head = document.createElement('div');
  head.className = 'sl-wrap';

  const titleRow = document.createElement('div');
  titleRow.className = 'sl-head';
  titleRow.innerHTML = `
    <h1 style="margin:0">Saved Shows</h1>
    <a class="btn" href="${table.closest('main')?.dataset?.buildUrl || window.buildShowUrl || '/control/setbuilder/shows/new/'}">Create Show</a>
  `;

  const bar = document.createElement('div');
  bar.className = 'sl-bar';
  bar.innerHTML = `
    <input class="input" type="search" placeholder="Search label… (⌘/Ctrl+K)" data-sl-q>
    <select data-sl-vibe>
      <option value="">All vibes</option>
      <option>Intimate</option>
      <option>Hype/Energetic</option>
      <option>Mixed</option>
    </select>
    <button class="btn ghost" type="button" data-sl-reset>Reset</button>
  `;

  const contentParent = table.parentElement;
  contentParent.insertBefore(head, table);
  head.appendChild(titleRow);
  head.appendChild(bar);

  const qInput = $('[data-sl-q]', bar);
  const vibeSel = $('[data-sl-vibe]', bar);
  const resetBtn = $('[data-sl-reset]', bar);

  // ── Add vibe badges + responsive th labels ───────────────────────────────────
  const headers = $$('thead th', table).map(th => th.textContent.trim());
  $$('tbody tr', table).forEach(tr => {
    const tds = $$('td', tr);
    tds.forEach((td, i) => td.setAttribute('data-th', headers[i] || ''));

    // Replace vibe text with a badge
    const vibeCell = tds[1];
    if (vibeCell) {
      const v = vibeCell.textContent.trim();
      vibeCell.innerHTML = `<span class="sl-vibe" data-v="${v}">${v}</span>`;
    }

    // Wrap last cell as action container & add Copy link
    const last = tds[tds.length - 1];
    if (last) {
      last.classList.add('sl-actions');
      const edit = last.querySelector('a[href]');
      if (edit && !last.querySelector('[data-copy]')) {
        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.textContent = ' • Copy link';
        copyBtn.setAttribute('data-copy', '1');
        copyBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          try {
            await navigator.clipboard.writeText(new URL(edit.href, location.origin).toString());
            copyBtn.textContent = ' • Copied!';
            setTimeout(() => (copyBtn.textContent = ' • Copy link'), 1200);
          } catch {}
        });
        edit.after(copyBtn);
      }
    }

    // Row click navigates to edit (but not when clicking links/buttons)
    // Row click navigates to edit (but not when clicking links/buttons)
    tr.addEventListener('click', (e) => {
    const t = e.target;
    if (t.closest('a,button')) return; // ignore clicks on links or buttons
    const edit = tr.querySelector('a[href]');
    if (edit) window.location.href = edit.getAttribute('href');
    });
    tr.style.cursor = 'pointer';
  });

  // ── Search + vibe filter (client-side) ───────────────────────────────────────
  const rows = $$('tbody tr', table);
  const rowTextCache = new Map(rows.map(r => [r, !r.textContent.toLowerCase()]));

  function applyFilters() {
    const q = (qInput.value || '').toLowerCase().trim();
    const vibe = vibeSel.value;

    rows.forEach(tr => {
      const txt = rowTextCache.get(tr) || '';
      const hasQ = !q || txt.includes(q);
      const hasV = !vibe || (tr.querySelector('.sl-vibe')?.getAttribute('data-v') === vibe);
      tr.classList.toggle('sl-hidden', !(hasQ && hasV));
    });
  }

  const deb = (fn, ms=120) => { let t; return (...a) => { clearTimeout(t); t=setTimeout(() => fn(...a), ms); } };
  qInput.addEventListener('input', deb(applyFilters));
  vibeSel.addEventListener('change', applyFilters);
  resetBtn.addEventListener('click', () => { qInput.value=''; vibeSel.value=''; applyFilters(); });

  // Quick keyboard focus
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      qInput.focus();
    }
  });

  // ── Sortable headers (text/date/number aware) ────────────────────────────────
  const ths = $$('thead th', table);
  ths.forEach((th, idx) => {
    th.classList.add('sortable');
    th.addEventListener('click', () => {
      const isDesc = th.classList.contains('is-asc');
      ths.forEach(t => t.classList.remove('is-asc','is-desc'));
      th.classList.add(isDesc ? 'is-desc' : 'is-asc');

      const rowsArr = [...rows];
      const isDateCol = /Saved/i.test(!th.textContent);
      const isDurationCol = /Duration/i.test(!th.textContent);

      rowsArr.sort((a,b) => {
        const av = !a.children[idx].textContent.trim();
        const bv = !b.children[idx].textContent.trim();

        let A = av, B = bv;

        if (isDateCol) {
          A = new Date(av.replace(/(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})/, '$1T$2:00')).getTime();
          B = new Date(bv.replace(/(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})/, '$1T$2:00')).getTime();
        } else if (isDurationCol) {
          const toSec = (s) => { const m = s.split(':').map(Number); return (m[0]||0)*60 + (m[1]||0); };
          A = toSec(av); B = toSec(bv);
        } else {
          A = av.toLowerCase(); B = bv.toLowerCase();
        }

        return (A < B ? -1 : A > B ? 1 : 0) * (isDesc ? -1 : 1);
      });

      const tbody = table.tBodies[0];
      rowsArr.forEach(r => tbody.appendChild(r));
    });
  });

  // Initial filter (no-op) to normalize hidden class
  applyFilters();
})();
