(function () {
  // If JS disabled, CSS shows a non-sticky fallback submit.
  document.documentElement.classList.remove('no-js');

  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const $  = (sel, root = document) => root.querySelector(sel);

  const money = (cents) => {
    const n = (cents || 0) / 100;
    return n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
  };

  const form       = $('#ppx-form');
  const subtotalEl = $('#ppx-subtotal');
  const submitBtn  = $('#ppx-submit');

  // NEW: detect auth state from data attribute
  const isAuthed = form && form.dataset.auth === '1';

  // Stepper logic
  $$('.ppx-type').forEach(card => {
    const price = parseInt(card.dataset.priceCents || '0', 10);
    const remaining = parseInt(card.dataset.remaining || '0', 10);
    const max = parseInt(card.dataset.max || '0', 10) || remaining;

    const qtyInput = $('.qty-input', card);
    const dec = $('.dec', card);
    const inc = $('.inc', card);
    const lineTotal = $('[data-line-total]', card);

    if (!qtyInput) return;

    const clamp = (v) => Math.max(0, Math.min(max, v));

    const updateUI = () => {
      const q = parseInt(qtyInput.value || '0', 10) || 0;
      qtyInput.value = clamp(q);
      if (dec) dec.disabled = q <= 0;
      if (inc) inc.disabled = q >= max;
      const lt = q * price;
      if (lineTotal) lineTotal.textContent = q ? money(lt) : '—';
      computeSubtotal();
    };

    dec?.addEventListener('click', () => {
      qtyInput.value = clamp((parseInt(qtyInput.value || '0', 10) || 0) - 1);
      updateUI();
    });

    inc?.addEventListener('click', () => {
      qtyInput.value = clamp((parseInt(qtyInput.value || '0', 10) || 0) + 1);
      updateUI();
    });

    qtyInput.addEventListener('input', () => {
      qtyInput.value = (qtyInput.value || '').replace(/[^\d]/g, '');
      updateUI();
    });

    // initialize
    updateUI();
  });

  function computeSubtotal() {
    let subtotal = 0;
    $$('.ppx-type').forEach(card => {
      const price = parseInt(card.dataset.priceCents || '0', 10);
      const qty = parseInt($('.qty-input', card)?.value || '0', 10) || 0;
      subtotal += price * qty;
    });
    if (subtotalEl) subtotalEl.textContent = money(subtotal);
    if (submitBtn) submitBtn.disabled = subtotal <= 0 || !isPurchaserValid();
  }

  function isPurchaserValid() {
    if (isAuthed) return true; // <-- Logged-in users don't need visible inputs
    const name = $('[name="purchaser_name"]');
    const email = $('[name="email"]');
    const ok = !!(name?.value.trim() && email?.value.trim() && email.checkValidity());
    return ok;
  }

  form.addEventListener('input', computeSubtotal);

  form.addEventListener('submit', (e) => {
    if (submitBtn && submitBtn.disabled) {
      e.preventDefault();
      submitBtn.animate(
        [{ transform:'scale(1)' }, { transform:'scale(1.03)' }, { transform:'scale(1)' }],
        { duration: 180 }
      );
    }
  });

  // First run
  computeSubtotal();
})();



(function () {
  const form = document.getElementById('ppx-form');
  if (!form) return;

  const eventIdMatch = window.location.pathname.match(/\/events?\/(\d+)|\/(\d+)\/?/i);
  const eventId = (window.__PPX_EVENT_ID__) || (eventIdMatch ? (eventIdMatch[1] || eventIdMatch[2]) : 'unknown');
  const CART_KEY = `ppx_cart_event_${eventId}`;
  const loginBtn = document.getElementById('ppx-login-btn');

  function readCart() {
    const items = {};
    document.querySelectorAll('.qty-input').forEach(inp => {
      const name = inp.getAttribute('name'); // qty_<id>
      const val = parseInt(inp.value || '0', 10);
      if (val > 0) items[name] = val;
    });
    // also capture purchaser info (guest)
    const nameInput = form.querySelector('input[name="purchaser_name"]');
    const emailInput = form.querySelector('input[name="email"]');
    const meta = {
      purchaser_name: nameInput ? nameInput.value : '',
      email: emailInput ? emailInput.value : '',
      artist_token: (form.querySelector('input[name="artist_token"]') || {}).value || ''
    };
    return { items, meta };
  }

  function writeCart(data) {
    localStorage.setItem(CART_KEY, JSON.stringify(data));
  }

  function restoreCart() {
    try {
      const raw = localStorage.getItem(CART_KEY);
      if (!raw) return;
      const { items, meta } = JSON.parse(raw);
      // restore quantities
      Object.entries(items || {}).forEach(([name, qty]) => {
        const inp = form.querySelector(`input[name="${name}"]`);
        if (inp) {
          inp.value = qty;
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
      // for guests, restore name/email
      const nameInput = form.querySelector('input[name="purchaser_name"]');
      const emailInput = form.querySelector('input[name="email"]');
      if (nameInput && meta && meta.purchaser_name) nameInput.value = meta.purchaser_name;
      if (emailInput && meta && meta.email) emailInput.value = meta.email;
      // don’t clear yet—clear on successful Stripe redirect if you prefer
    } catch (e) { /* noop */ }
  }

  // Save on any quantity change
  document.addEventListener('change', (e) => {
    if (e.target && e.target.classList.contains('qty-input')) {
      writeCart(readCart());
    }
  });

  // Save before login click
  loginBtn && loginBtn.addEventListener('click', () => {
    writeCart(readCart());
  }, { passive: true });

  // Restore on load
  restoreCart();

  // Also save right before submit (just in case)
  form.addEventListener('submit', () => writeCart(readCart()));
})();
