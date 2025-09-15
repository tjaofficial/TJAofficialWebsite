(() => {
  const list = document.querySelector('.ck-list');
  const toast = document.getElementById('toast');
  const doneEl = document.getElementById('doneCount');
  const totalEl = document.getElementById('totalCount');
  const bar = document.querySelector('.progress .bar');

  if (!list) return;

  const getCookie = (name) => (document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)')||[])[2] || '';
  const csrf = getCookie('csrftoken');

  function showToast(msg){ if(!toast) return; toast.textContent = msg; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'), 1000); }

  list.addEventListener('click', async (e) => {
    const li = e.target.closest('.ck-item');
    if (!li || !e.target.closest('.ck-toggle')) return;
    const id = li.dataset.id;

    try {
      const url = li.dataset.toggleUrl || `/events/checklist/toggle/${id}/`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch' }
      });
      const data = await res.json();
      if (!data.ok) throw new Error();
      li.classList.toggle('is-done', data.is_done);
      if (doneEl && totalEl) {
        doneEl.textContent = String(data.done);
        const total = parseInt(totalEl.textContent || '0', 10) || 0;
        const pct = total ? Math.round((data.done / total) * 100) : 0;
        if (bar) bar.style.width = pct + '%';
      }
      showToast(data.is_done ? 'Completed' : 'Reopened');
    } catch {
      showToast('Failed');
    }
  });

  // initialize bar width
  if (bar && doneEl && totalEl) {
    const d = parseInt(doneEl.textContent || '0', 10) || 0;
    const t = parseInt(totalEl.textContent || '0', 10) || 0;
    bar.style.width = t ? Math.round((d/t)*100) + '%' : '0%';
  }
})();
