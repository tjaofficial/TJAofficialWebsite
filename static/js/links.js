/* ===== Linktree: filter + hover sheen + copy profile link ===== */
(() => {
  // Filter
  const input = document.getElementById('linkFilter');
  if (input) {
    const tiles = Array.from(document.querySelectorAll('.link-tile'));
    const groups = Array.from(document.querySelectorAll('.lt-grid'));
    const headings = Array.from(document.querySelectorAll('.lt-heading'));

    const applyFilter = () => {
      const q = input.value.trim().toLowerCase();
      tiles.forEach(t => {
        const label = (t.dataset.label || t.textContent || '').toLowerCase();
        t.style.display = label.includes(q) ? '' : 'none';
      });
      // Hide headings if their group has no visible tiles
      groups.forEach((g, i) => {
        const visible = Array.from(g.querySelectorAll('.link-tile')).some(t => t.style.display !== 'none');
        g.style.display = visible ? '' : 'none';
        if (headings[i]) headings[i].style.display = visible ? '' : 'none';
      });
    };
    input.addEventListener('input', applyFilter);
  }

  // Hover sheen follows cursor
  const tiles = document.querySelectorAll('.link-tile');
  tiles.forEach(t => {
    t.addEventListener('pointermove', (e) => {
      const rect = t.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      t.style.setProperty('--mx', `${x}%`);
      t.style.setProperty('--my', `${y}%`);
    });
  });

  // Copy profile link (uses current URL or set your canonical link)
  const copyBtn = document.getElementById('copyProfileLink');
  if (copyBtn && navigator.clipboard) {
    copyBtn.addEventListener('click', async () => {
      try {
        const url = window.location.origin + '/links/';
        await navigator.clipboard.writeText(url);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => (copyBtn.textContent = 'Copy Profile Link'), 1200);
      } catch (e) {
        copyBtn.textContent = 'Copy failed';
        setTimeout(() => (copyBtn.textContent = 'Copy Profile Link'), 1400);
      }
    });
  }
})();
