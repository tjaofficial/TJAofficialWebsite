/* ===== Media album lightbox (photos + video embeds) ===== */
(() => {
  const grid = document.getElementById('galleryGrid');
  const lb   = document.getElementById('lightbox');
  if (!grid || !lb) return;

  const stage   = document.getElementById('lbStage');
  const caption = document.getElementById('lbCaption');
  const btnClose= lb.querySelector('.lb-close');
  const btnPrev = lb.querySelector('.lb-prev');
  const btnNext = lb.querySelector('.lb-next');

  const items = Array.from(grid.querySelectorAll('.g-item'));
  let idx = -1;

  const open = (i) => {
    idx = i;
    const el = items[idx];
    const kind = el.dataset.kind;
    stage.innerHTML = '';
    caption.textContent = el.dataset.caption || '';

    if (kind === 'photo') {
      const img = document.createElement('img');
      img.src = el.getAttribute('href');
      stage.appendChild(img);
    } else if (kind === 'video') {
      const iframe = document.createElement('iframe');
      iframe.src = (el.dataset.embed || '') + '?autoplay=1&rel=0&modestbranding=1';
      iframe.allow = 'autoplay; encrypted-media; fullscreen; picture-in-picture';
      iframe.allowFullscreen = true;
      stage.appendChild(iframe);
    }

    lb.hidden = false;
    document.body.style.overflow = 'hidden';
  };

  const close = () => {
    lb.hidden = true;
    stage.innerHTML = '';
    document.body.style.overflow = '';
    idx = -1;
  };

  const next = () => { if (items.length) open((idx + 1) % items.length); };
  const prev = () => { if (items.length) open((idx - 1 + items.length) % items.length); };

  grid.addEventListener('click', (e) => {
    const a = e.target.closest('.g-item');
    if (!a) return;
    e.preventDefault();
    const i = items.indexOf(a);
    if (i >= 0) open(i);
  });

  btnClose.addEventListener('click', close);
  btnNext.addEventListener('click', next);
  btnPrev.addEventListener('click', prev);

  window.addEventListener('keydown', (e) => {
    if (lb.hidden) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowRight') next();
    if (e.key === 'ArrowLeft') prev();
  });

  lb.addEventListener('click', (e) => {
    if (e.target === lb) close();
  });
})();
