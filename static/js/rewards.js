(function () {
  const root = document.querySelector('[data-rewards]');
  if (!root) return;

  // Confirm redemption (prevents accidental clicks)
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-redeem]');
    if (!btn) return;
    const [name, cost] = (btn.getAttribute('data-redeem') || '').split('|');
    if (!window.confirm(`Redeem "${name}" for ${cost} pts?`)) {
      e.preventDefault();
    }
  });

  // Optional: toast from ?msg in URL (example pattern)
  const params = new URLSearchParams(window.location.search);
  const msg = params.get('rwmsg');
  if (msg) {
    // Replace with your site’s toast if you have one
    console.log('[Rewards]', msg);
  }
})();
