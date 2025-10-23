(() => {
  const $  = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  const table = $('.cp-table');
  if (!table) return;

  // Build header + toolbar
  const wrap = document.createElement('div');
  wrap.className = 'sl-wrap';

  const head = document.createElement('div');
  head.className = 'sl-head';
  head.innerHTML = `
    <h1>My Songs</h1>
    <a class="btn" href="${(document.currentScript && document.currentScript.dataset?.newUrl) || '/control/setbuilder/songs/new/'}">Add Song</a>
  `;

  const bar = document.createElement('div');
  bar.className = 'sl-bar';
  bar.innerHTML = `
    <input class="input" type="search" placeholder="Search title/feeling… (⌘/Ctrl+K)" data-sl-q>
    <select data-sl-genre>
      <option value="">All genres</option>
      <option value="hiphop">Hip-Hop</option>
      <option value="rnb">R&B</option>
      <option value="pop">Pop</option>
      <option value="edm">EDM</option>
      <option value="trap">Trap</option>
      <option value="alt">Alt/Indie</option>
      <option value="other">Other</option>
    </select>
    <select data-sl-collab>
      <option value="">Any collab</option>
      <option value="yes">Collab: Yes</option>
      <option value="no">Collab: No</option>
    </select>
    <button class="btn ghost" type="button" data-sl-reset>Reset</button>
  `;

  // Insert before table
  const parent = table.parentElement;
  parent.insertBefore(wrap, table);
  wrap.appendChild(head);
  wrap.appendChild(bar);

  const qInput = $('[data-sl-q]', bar);
  const genreSel = $('[data-sl-genre]', bar);
  const collabSel = $('[data-sl-collab]', bar);
  const resetBtn = $('[data-sl-reset]', bar);

  // Add data-th for responsive rows & prettify cells (badges)
  const headers = $$('thead th', table).map(th => th.textContent.trim());
  const rows = $$('tbody tr', table);
  rows.forEach(tr => {
    const cells = $$('td', tr);
    cells.forEach((td, i) => td.setAttribute('data-th', headers[i] || ''));

    // Collab -> badge
    const collabCell = cells[2];
    if (collabCell) {
      const isYes = /yes/i.test(collabCell.textContent.trim());
      collabCell.innerHTML = `<span class="badge ${isYes?'collab-yes':'collab-no'}">${isYes?'Yes':'No'}</span>`;
    }

    // Genre -> badge (if present)
    const genreCell = cells[3];
    const gText = (genreCell?.textContent || '').trim();
    if (gText) genreCell.innerHTML = `<span class="badge genre">${gText}</span>`;

    // Actions cell class
    const last = cells[cells.length - 1];
    if (last) last.classList.add('sl-actions');

    // Row click navigates to edit unless clicking a control
    tr.addEventListener('click', (e) => {
      if (e.target.closest('a,button,form,input,select')) return;
      const editLink = tr.querySelector('a[href*="/edit"]') || tr.querySelector('a[href]');
      if (editLink) window.location.href = editLink.getAttribute('href');
    });
    tr.style.cursor = 'pointer';
  });

  // Build cache for filtering
  const cache = new Map();
  rows.forEach(tr => {
    const text = tr.textContent.toLowerCase();
    // Try to capture raw genre value for reliable filtering; fallback to label text
    const genreCell = tr.children[3];
    const genreLabel = (genreCell?.textContent || '').toLowerCase();
    cache.set(tr, { text, genreLabel });
  });

  // Filters
  function applyFilters(){
    const q = (qInput.value || '').toLowerCase().trim();
    const g = (genreSel.value || '').toLowerCase().trim();
    const c = (collabSel.value || '').trim(); // '', 'yes', 'no'

    rows.forEach(tr => {
      const { text, genreLabel } = cache.get(tr) || { text:'', genreLabel:'' };

      // collab check via badge class
      const isYes = tr.querySelector('.badge.collab-yes') ? true : false;

      let ok = true;
      if (q && !text.includes(q)) ok = false;
      if (g && !genreLabel.includes(g)) ok = false;
      if (c === 'yes' && !isYes) ok = false;
      if (c === 'no'  &&  isYes) ok = false;

      tr.classList.toggle('sl-hidden', !ok);
    });
  }
  const debounce = (fn,ms=140)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; };
  qInput.addEventListener('input', debounce(applyFilters));
  genreSel.addEventListener('change', applyFilters);
  collabSel.addEventListener('change', applyFilters);
  resetBtn.addEventListener('click', () => {
    qInput.value = ''; genreSel.value = ''; collabSel.value = '';
    applyFilters();
    toast('Filters cleared');
  });

  // Sortable columns
  const ths = $$('thead th', table);
  ths.forEach((th, idx) => {
    th.classList.add('sortable');
    th.addEventListener('click', () => {
      const isDesc = th.classList.contains('is-asc');
      ths.forEach(t => t.classList.remove('is-asc','is-desc'));
      th.classList.add(isDesc ? 'is-desc' : 'is-asc');

      const toSec = (s) => {
        const m = s.split(':').map(Number);
        return (m[0]||0)*60 + (m[1]||0);
      };

      const rowsArr = [...rows];
      rowsArr.sort((a,b) => {
        const av = a.children[idx]?.textContent.trim() || '';
        const bv = b.children[idx]?.textContent.trim() || '';
        let A = av, B = bv;

        // Duration column
        if (/duration/i.test(th.textContent)) {
          A = toSec(av); B = toSec(bv);
        } else if (/collab/i.test(th.textContent)) {
          // Yes before No
          A = /Yes/i.test(av) ? 1 : 0;
          B = /Yes/i.test(bv) ? 1 : 0;
        } else {
          // Text
          A = av.toLowerCase(); B = bv.toLowerCase();
        }
        return (A < B ? -1 : A > B ? 1 : 0) * (isDesc ? -1 : 1);
      });

      const tbody = table.tBodies[0];
      rowsArr.forEach(r => tbody.appendChild(r));
    });
  });

  // Keyboard: ⌘/Ctrl+K focuses search
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey||e.ctrlKey) && e.key.toLowerCase()==='k') {
      e.preventDefault();
      qInput.focus();
    }
  });

  // Toast helper
  const toastEl = document.createElement('div');
  toastEl.className = 'sl-toast';
  document.body.appendChild(toastEl);
  function toast(msg){
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 1500);
  }

  // Inline delete confirmation: intercept buttons with class "link" in the last cell
  $$('form button.link', table).forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (!confirm('Delete song?')) e.preventDefault();
    });
  });

  // Initial pass
  applyFilters();
})();
