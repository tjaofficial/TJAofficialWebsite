// static/js/setbuilder.js
(() => {
  const $  = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

  const table   = $('#sbTable');
  const body    = $('#sbBody');
  const totalEl = $('#sbTotal');
  const labelEl = $('#sbLabel');
  const vibeEl  = $('#sbVibe');
  const saveBtn = $('#sbSave');
  const addBtn  = $('#sbAdd');

  let dirty = false;

  // ---------------- utils ----------------
  const clampInt = (v, min=0, max=999999) => {
    v = parseInt(v ?? '0', 10);
    if (isNaN(v)) v = 0;
    return Math.max(min, Math.min(max, v));
  };
  const mToSeconds = (min) => clampInt(min, 0, 9999) * 60;
  const secondsToLabel = (sec) => {
    sec = clampInt(sec, 0, 24*3600);
    const m = Math.floor(sec/60), s = sec%60;
    return `${m}:${String(s).padStart(2,'0')}`;
  };

  function markDirty() {
    if (!dirty) {
      dirty = true;
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.style.cursor = "unset";
      }
    }
  }

  function computeTotals() {
    let total = 0;
    $$('#sbBody tr').forEach(tr => {
      const dur = clampInt(tr.dataset.duration || '0', 0);
      total += dur;
      const cell = $('[data-col="dur"]', tr);
      if (cell) cell.textContent = secondsToLabel(dur);
    });
    if (totalEl) totalEl.textContent = secondsToLabel(total);
  }

  // Responsive TH labels for TDs
  const headers = $$('thead th', table).map(th => th.textContent.trim());
  function applyDataTh(tr) {
    const tds = $$('td', tr);
    tds.forEach((td, i) => td.setAttribute('data-th', headers[i] || ''));
  }
  // apply to existing
  $$('#sbBody tr').forEach(applyDataTh);

  // ---------------- change listeners ----------------
  labelEl?.addEventListener('input', markDirty);
  vibeEl?.addEventListener('change', markDirty);

  // ---------------- drag & drop ----------------
  let dragEl = null;
  body.addEventListener('dragstart', (e) => {
    const tr = e.target.closest('tr[draggable="true"]');
    if (!tr) return;
    dragEl = tr;
    tr.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });
  body.addEventListener('dragend', () => {
    dragEl?.classList.remove('dragging');
    dragEl = null;
    markDirty();
  });
  body.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (!dragEl) return;
    const rows = $$('#sbBody tr').filter(r => r !== dragEl);
    let after = null;
    for (const row of rows) {
      const rect = row.getBoundingClientRect();
      const midpoint = rect.top + rect.height / 2;
      if (e.clientY < midpoint) { after = row; break; }
    }
    if (after) body.insertBefore(dragEl, after);
    else body.appendChild(dragEl);
  });

  // delete row
  body.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    const tr = btn.closest('tr');
    if (tr) tr.remove();
    computeTotals();
    markDirty();
  });

  // ---------------- modal ----------------
  const dlg        = $('#sbModal');
  const kindSel    = $('#mKind');

  const rowBlocks  = $$('.m-row'); // each has data-show="OPENER|HEADLINER|COLLAB|BREAK|INTERMISSION"
  function showRow(kind) {
    rowBlocks.forEach(r => {
      r.style.display = (r.dataset.show === kind) ? '' : 'none';
    });
  }
  kindSel?.addEventListener('change', () => showRow(kindSel.value));
  // default
  showRow(kindSel?.value || 'OPENER');

  // Headliner -> fetch songs
  const headSel = $('#mHeadliner');
  const headSong = $('#mHeadSong');
  headSel?.addEventListener('change', async () => {
    headSong.innerHTML = '<option value="">— select song —</option>';
    headSong.disabled = true;
    const id = headSel.value;
    if (!id) return;
    try {
      const res = await fetch(`/control/setbuilder/api/songs/by-artist/${id}/`);
      if (!res.ok) return;
      const data = await res.json();
      data.songs.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = `${s.title} (${s.label})`;
        opt.dataset.dur = s.dur;
        headSong.appendChild(opt);
      });
      headSong.disabled = false;
    } catch {}
  });

  // Collab -> multi-artist union
  const collabArtists = $('#mCollabArtists');
  const collabSong    = $('#mCollabSong');

  async function loadCollabSongs(){
    collabSong.innerHTML = '<option value="">— select collab song —</option>';
    collabSong.disabled = true;
    const ids = Array.from(collabArtists.selectedOptions).map(o => o.value);
    if (!ids.length) return;

    const seen = new Map();
    for (const id of ids) {
      try {
        const res = await fetch(`/control/setbuilder/api/songs/by-artist/${id}/`);
        if (!res.ok) continue;
        const data = await res.json();
        data.songs.forEach(s => { if (!seen.has(s.id)) seen.set(s.id, s); });
      } catch {}
    }

    for (const s of seen.values()) {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = `${s.title} (${s.label})`;
      opt.dataset.dur = s.dur;
      collabSong.appendChild(opt);
    }
    collabSong.disabled = false;
  }
  collabArtists?.addEventListener('change', loadCollabSongs);

  // open modal
  addBtn?.addEventListener('click', () => dlg?.showModal());

  // Save in modal -> append row
  $('#mSave')?.addEventListener('click', (e) => {
    e.preventDefault();
    const kind = kindSel?.value || 'OPENER';

    let artistName = '—';
    let songTitle  = '—';
    let collabTxt  = '—';
    let duration   = 0;
    let artistId   = '';
    let songId     = '';

    if (kind === 'OPENER') {
      const openerOpt = $('#mOpener')?.selectedOptions?.[0];
      if (!openerOpt || !openerOpt.value) return;
      artistName = openerOpt.textContent;
      songTitle  = 'Opener';
      duration   = mToSeconds($('#mOpenerMin')?.value);
      artistId   = openerOpt.value;
    } else if (kind === 'HEADLINER') {
      const a = $('#mHeadliner')?.selectedOptions?.[0];
      const s = $('#mHeadSong')?.selectedOptions?.[0];
      if (!a || !a.value || !s || !s.value) return;
      artistName = a.textContent;
      songTitle  = s.textContent.replace(/\s*\(\d+:\d{2}\)\s*$/, '');
      collabTxt  = '—';
      duration   = clampInt(s.dataset.dur || '0', 0);
      artistId   = a.value;
      songId     = s.value;
    } else if (kind === 'COLLAB') {
      const s = $('#mCollabSong')?.selectedOptions?.[0];
      if (!s || !s.value) return;
      artistName = 'Collaboration';
      songTitle  = s.textContent.replace(/\s*\(\d+:\d{2}\)\s*$/, '');
      collabTxt  = 'Yes';
      duration   = clampInt(s.dataset.dur || '0', 0);
      songId     = s.value;
    } else if (kind === 'BREAK') {
      artistName = 'Break';
      songTitle  = 'Break';
      duration   = mToSeconds($('#mBreakMin')?.value);
    } else if (kind === 'INTERMISSION') {
      artistName = 'Intermission';
      songTitle  = 'Intermission';
      duration   = mToSeconds($('#mInterMin')?.value);
    } else if (kind === 'TALKING') {
      const a = $('#mtHeadliner')?.selectedOptions?.[0];
      if (!a || !a.value) return;
      artistName = a.textContent;
      songTitle  = 'Talking';
    }

    // Build row
    const tr = document.createElement('tr');
    tr.setAttribute('draggable', 'true');
    tr.dataset.kind     = kind;
    tr.dataset.artist   = artistId || '';
    tr.dataset.song     = songId   || '';
    tr.dataset.duration = String(duration);

    tr.innerHTML = `
      <td class="drag">↕</td>
      <td>${artistName}</td>
      <td>${songTitle}</td>
      <td>${collabTxt}</td>
      <td data-col="dur"></td>
      <td><button class="link" data-remove>Delete</button></td>
    `;
    applyDataTh(tr);
    body.appendChild(tr);

    computeTotals();
    markDirty();
    dlg?.close();
  });

  // ---------------- save show ----------------
  function getCsrf() {
    // prefer cookie (works even when no form CSRF input is on the page)
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : '';
  }

  saveBtn?.addEventListener('click', async () => {
    const slug = table?.dataset.slug || '';

    const items = $$('#sbBody tr').map(tr => ({
      kind: tr.dataset.kind,
      artist_id: tr.dataset.artist || null,
      song_id: tr.dataset.song || null,
      duration_seconds: clampInt(tr.dataset.duration || '0', 0),
      display_name: $('td:nth-child(2)', tr)?.textContent || ''
    }));

    const payload = {
      slug,
      label: (labelEl?.value || '').trim(),
      vibe:  vibeEl?.value || 'mixed',
      items
    };

    if (!payload.label) {
      alert('Please enter a Show Label.');
      return;
    }

    try {
      saveBtn.disabled = true;
      saveBtn.style.cursor = "not-allowed";
      const res = await fetch('/control/setbuilder/shows/save/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf()
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        saveBtn.disabled = false;
        saveBtn.style.cursor = "unset";
        alert('Could not save');
        return;
      }
      const data = await res.json();
      if (data.slug) table.dataset.slug = data.slug;
      dirty = false;
      saveBtn.disabled = true;
      saveBtn.style.cursor = "not-allowed";
      // Optional toast
      // console.log('Saved', data);
      window.location.href = '/control/setbuilder/shows/';
    } catch (e) {
      saveBtn.disabled = false;
      saveBtn.style.cursor = "unset";
      alert('Could not save');
    }
  });

  // keyboard shortcut save
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      if (!saveBtn?.disabled) saveBtn.click();
    }
  });

  // ---------------- init ----------------
  computeTotals();
  // ensure durations printed for SSR rows
  $$('#sbBody tr').forEach(tr => {
    const dur = clampInt(tr.dataset.duration || '0', 0);
    const cell = $('[data-col="dur"]', tr);
    if (cell) cell.textContent = secondsToLabel(dur);
  });
})();
