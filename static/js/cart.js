/* ===== Cart page: qty, remove, clear, totals ===== */
(() => {
  const grid = document.querySelector('.cart-grid');
  if (!grid) return;

  // helpers
  const getCookie = (name) => {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  };
  const csrf = getCookie('csrftoken');
  const fmt = (cents) => `$${(cents/100).toFixed(2)}`;

  const toast = document.getElementById('toast');
  const showToast = (msg) => { if (!toast) return; toast.textContent = msg; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'), 1200); };

  const sumEl = document.getElementById('sumSubtotal');

  // Recompute client-side line total (needs price from DOM)
  const unitPrice = (row) => {
    // parse like "$12.34"
    const text = row.querySelector('.c-price')?.textContent || '$0.00';
    const num = Number(text.replace(/[^0-9.]/g,'') || '0');
    return Math.round(num * 100);
  };

  const updateQty = async (row, qty) => {
    const id = row.dataset.id;
    if (!id) return;
    const body = new URLSearchParams({ product_id: id, qty: String(qty) });
    const res = await fetch('/cart/update/', { method:'POST', headers:{'X-CSRFToken': csrf,'Content-Type':'application/x-www-form-urlencoded'}, body });
    if (!res.ok) throw new Error('update failed');
    const data = await res.json();

    // Update line total
    const lineCents = unitPrice(row) * qty;
    row.querySelector('.c-line').textContent = fmt(lineCents);

    // Update subtotal
    if (sumEl) sumEl.textContent = data.subtotal;

    // Raise header badge event
    document.dispatchEvent(new CustomEvent('cart:updated', { detail: { count: data.count }}));

    showToast('Updated quantity');
  };

  const removeItem = async (row) => {
    const id = row.dataset.id;
    if (!id) return;
    const body = new URLSearchParams({ product_id: id });
    const res = await fetch('/cart/remove/', { method:'POST', headers:{'X-CSRFToken': csrf,'Content-Type':'application/x-www-form-urlencoded'}, body });
    if (!res.ok) throw new Error('remove failed');
    const data = await res.json();
    row.remove();
    if (sumEl) sumEl.textContent = data.subtotal;
    document.dispatchEvent(new CustomEvent('cart:updated', { detail: { count: data.count }}));
    showToast('Removed item');
    // If no rows left, reload to show empty state
    if (!document.querySelector('.cart-row')) location.reload();
  };

  grid.addEventListener('click', async (e) => {
    const row = e.target.closest('.cart-row');

    if (e.target.closest('[data-inc]') || e.target.closest('[data-dec]')) {
      const input = row.querySelector('.qty-in');
      let v = parseInt(input.value || '1', 10);
      if (Number.isNaN(v) || v < 1) v = 1;
      v = e.target.hasAttribute('data-inc') ? v + 1 : Math.max(1, v - 1);
      input.value = String(v);
      try { await updateQty(row, v); } catch { showToast('Failed to update'); }
      return;
    }

    if (e.target.closest('.c-remove')) {
      try { await removeItem(row); } catch { showToast('Failed to remove'); }
      return;
    }
  });

  grid.addEventListener('change', async (e) => {
    if (!e.target.classList.contains('qty-in')) return;
    const row = e.target.closest('.cart-row');
    let v = parseInt(e.target.value || '1', 10);
    if (Number.isNaN(v) || v < 1) v = 1;
    e.target.value = String(v);
    try { await updateQty(row, v); } catch { showToast('Failed to update'); }
  });

  const clearForm = document.getElementById('clearCartForm');
  if (clearForm) {
    clearForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await fetch('/cart/clear/', { method:'POST', headers:{'X-CSRFToken': csrf} });
        if (!res.ok) throw new Error();
        document.dispatchEvent(new CustomEvent('cart:updated', { detail: { count: 0 }}));
        location.reload();
      } catch { showToast('Failed to clear cart'); }
    });
  }
})();
