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
