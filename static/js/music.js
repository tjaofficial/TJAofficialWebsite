/* ===== Music page: filter + collapse ===== */
(() => {
  const list = document.getElementById('discography');
  const filter = document.getElementById('musicFilter');
  if (!list) return;

  // Filter by release title or any track title
  const apply = () => {
    const q = (filter?.value || '').trim().toLowerCase();
    list.querySelectorAll('.release-card').forEach(card => {
      const inTitle = (card.dataset.title || '').includes(q);
      const inTracks = Array.from(card.querySelectorAll('.track')).some(li => (li.dataset.track || '').includes(q));
      card.style.display = (!q || inTitle || inTracks) ? '' : 'none';
    });
  };
  filter?.addEventListener('input', apply);

  // Collapse/expand tracklists
  list.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-collapse]');
    if (!btn) return;
    const card = e.target.closest('.release-card');
    const tl = card?.querySelector('.tracklist');
    if (!tl) return;
    const collapsed = tl.hasAttribute('data-collapsed');
    if (collapsed) {
      tl.removeAttribute('data-collapsed');
      tl.style.maxHeight = '';
      btn.textContent = 'Collapse';
    } else {
      tl.setAttribute('data-collapsed', 'true');
      tl.style.maxHeight = '140px'; // peek a few tracks
      btn.textContent = 'Expand';
    }
  });

  // Initial: collapse long tracklists on small screens
  const mql = window.matchMedia('(max-width: 640px)');
  const autoCollapse = () => {
    if (!mql.matches) return;
    list.querySelectorAll('.tracklist').forEach(tl => {
      if (tl.childElementCount > 5 && !tl.hasAttribute('data-collapsed')) {
        tl.setAttribute('data-collapsed','true');
        tl.style.maxHeight = '140px';
      }
    });
  };
  autoCollapse();
})();
