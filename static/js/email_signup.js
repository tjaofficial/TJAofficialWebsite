/* ===== Email signup AJAX (optional) ===== */
(() => {
  const form = document.querySelector('.email-form');
  if (!form) return;
  // Leave classic POST for browsers with JS disabled
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      const res = await fetch(location.pathname, {
        method: 'POST',
        headers: {'X-Requested-With':'fetch'},
        body: new FormData(form)
      });
      // fall back to reload if server returns redirect
      if (res.redirected) { location.href = res.url; return; }
      // simple success UX:
      const ok = res.ok;
      const note = document.createElement('div');
      note.className = 'card';
      note.textContent = ok ? 'Thanks! You’re on the list ✅' : 'Please try again.';
      form.prepend(note);
      if (ok) form.reset();
      setTimeout(() => note.remove(), 3000);
    } catch {
      // ignore and let user retry
    } finally {
      btn.disabled = false;
    }
  }, { once: false });
})();
