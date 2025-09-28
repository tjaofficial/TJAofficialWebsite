(function () {
  // If JS disabled, CSS shows a non-sticky fallback submit.
  document.documentElement.classList.remove('no-js');

  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const $  = (sel, root = document) => root.querySelector(sel);

  const money = (cents) => {
    const n = (cents || 0) / 100;
    return n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
  };

  const form     = $('#ppx-form');
  const subtotalEl = $('#ppx-subtotal');
  const submitBtn  = $('#ppx-submit');

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
      dec.disabled = q <= 0;
      inc.disabled = q >= max;
      const lt = q * price;
      lineTotal.textContent = q ? money(lt) : '—';
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
      // strip non-digits
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
    subtotalEl.textContent = money(subtotal);
    submitBtn.disabled = subtotal <= 0 || !isPurchaserValid();
  }

  function isPurchaserValid() {
    const name = $('[name="purchaser_name"]');
    const email = $('[name="email"]');
    const ok = !!(name?.value.trim() && email?.value.trim() && email.checkValidity());
    return ok;
  }

  // Form-level validation to toggle submit
  form.addEventListener('input', () => {
    computeSubtotal();
  });

  // Prevent submit if nothing selected or invalid info
  form.addEventListener('submit', (e) => {
    if (submitBtn.disabled) {
      e.preventDefault();
      // light hint flash
      submitBtn.animate([{transform:'scale(1)'},{transform:'scale(1.03)'},{transform:'scale(1)'}], {duration:180});
    }
  });

  // First run
  computeSubtotal();
})();
