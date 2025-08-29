/* ===== Checkout placeholder (prep for Stripe) ===== */
(() => {
  const btn = document.getElementById('checkoutBtn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    // Placeholder — later we’ll hit a Django view that creates a Stripe Checkout Session
    // and redirect to session.url. For now, just show a toast.
    const toast = document.getElementById('toast');
    if (toast) {
      toast.textContent = 'Stripe checkout coming soon…';
      toast.classList.add('show');
      setTimeout(()=>toast.classList.remove('show'), 1200);
    }
  });
})();

/* ===== Checkout: live quote ===== */
(() => {
  const form = document.getElementById('quoteForm');
  if (!form) return;

  const ship = document.getElementById('shipMethod');
  const state = document.getElementById('taxState');
  const qSubtotal = document.getElementById('qSubtotal');
  const qShip = document.getElementById('qShip');
  const qTax = document.getElementById('qTax');
  const qTotal = document.getElementById('qTotal');

  const getCookie = (name) => (document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)') || [,'',''])[2];

  const fetchQuote = async () => {
    try {
      const res = await fetch('/cart/quote/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type':'application/x-www-form-urlencoded'},
        body: new URLSearchParams({ method: ship.value, state: state.value })
      });
      if (!res.ok) throw new Error();
      const d = await res.json();
      if (!d.ok) return;
      qShip.textContent = d.ship;
      qTax.textContent = d.tax;
      qTotal.textContent = d.total;
      // subtotal already rendered server-side
    } catch (e) {
      // no-op
    }
  };

  ship.addEventListener('change', fetchQuote);
  state.addEventListener('input', fetchQuote);
  fetchQuote();
})();
