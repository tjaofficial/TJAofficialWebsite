/* EPK dashboard tabs */
(() => {
  const bar = document.querySelector('[data-tabs]');
  if (!bar) return;
  const tabs = bar.querySelectorAll('.tab');
  const panels = {
    profile: document.getElementById('tab-profile'),
    photos:  document.getElementById('tab-photos'),
    videos:  document.getElementById('tab-videos'),
  };
  bar.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab'); if (!btn) return;
    const key = btn.dataset.tab; if (!panels[key]) return;
    tabs.forEach(t => t.classList.remove('is-active'));
    Object.values(panels).forEach(p => p.classList.remove('is-active'));
    btn.classList.add('is-active'); panels[key].classList.add('is-active');
  });
})();


// EPK Lightbox
(() => {
  const grid = document.getElementById('epk-photos');
  if (!grid) return;

  const items = Array.from(grid.querySelectorAll('a[data-full]'));
  let idx = -1;

  // Build lightbox DOM once
  const lb = document.createElement('div');
  lb.className = 'lb';
  lb.innerHTML = `
    <div class="lb-inner">
      <img class="lb-img" alt="">
      <div class="lb-cap"></div>
      <button class="lb-btn lb-prev" aria-label="Previous">‹</button>
      <button class="lb-btn lb-next" aria-label="Next">›</button>
      <button class="lb-close" aria-label="Close">×</button>
    </div>
  `;
  document.body.appendChild(lb);

  const img = lb.querySelector('.lb-img');
  const cap = lb.querySelector('.lb-cap');
  const btnPrev = lb.querySelector('.lb-prev');
  const btnNext = lb.querySelector('.lb-next');
  const btnClose = lb.querySelector('.lb-close');

  const openAt = (i) => {
    idx = (i + items.length) % items.length;
    const a = items[idx];
    img.src = a.dataset.full;
    img.alt = a.getAttribute('aria-label') || a.dataset.caption || '';
    cap.textContent = a.dataset.caption || '';
    lb.classList.add('is-open');
    document.documentElement.style.overflow = 'hidden';
  };
  const close = () => {
    lb.classList.remove('is-open');
    img.src = '';
    document.documentElement.style.overflow = '';
  };
  const next = () => openAt(idx + 1);
  const prev = () => openAt(idx - 1);

  // Click handlers
  grid.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-full]');
    if (!a) return;
    e.preventDefault();
    openAt(items.indexOf(a));
  });
  btnClose.addEventListener('click', close);
  btnNext.addEventListener('click', next);
  btnPrev.addEventListener('click', prev);
  lb.addEventListener('click', (e) => { if (e.target === lb) close(); });

  // Keyboard
  window.addEventListener('keydown', (e) => {
    if (!lb.classList.contains('is-open')) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowRight') next();
    else if (e.key === 'ArrowLeft') prev();
  });

  // Basic swipe
  let startX = 0, startY = 0;
  img.addEventListener('touchstart', (e) => {
    const t = e.touches[0]; startX = t.clientX; startY = t.clientY;
  }, {passive:true});
  img.addEventListener('touchend', (e) => {
    const t = e.changedTouches[0];
    const dx = t.clientX - startX, dy = t.clientY - startY;
    if (Math.abs(dx) > 40 && Math.abs(dy) < 60) {
      dx < 0 ? next() : prev();
    }
  }, {passive:true});
})();

