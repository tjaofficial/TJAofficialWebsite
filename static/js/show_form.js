/* ===== Add Show form niceties ===== */
(() => {
  const form = document.querySelector('form.form');
  if (!form) return;

  const dt = form.querySelector('input[type="datetime-local"]');
  if (dt) {
    // If the control is empty, default to today at 20:00
    if (!dt.value) {
      const d = new Date();
      d.setHours(20, 0, 0, 0);
      const pad = n => String(n).padStart(2, '0');
      dt.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
  }

  form.addEventListener('submit', (e) => {
    // light client-side check
    const required = form.querySelectorAll('input[required]');
    for (const r of required) {
      if (!r.value.trim()) {
        r.focus();
        break;
      }
    }
  });
})();
