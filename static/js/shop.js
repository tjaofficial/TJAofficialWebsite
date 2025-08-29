/* ===== Shop: qty controls, add-to-cart, toast ===== */
(() => {
  const shop = document.querySelector('.shop-grid');
  if (!shop) return;

  // CSRF helper (Django)
  const getCookie = (name) => {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  };
  const csrftoken = getCookie('csrftoken');

  const toast = document.getElementById('toast');
  const showToast = (msg) => {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 1400);
  };

  shop.addEventListener('click', async (e) => {
    // quantity +/- buttons
    const dec = e.target.closest('[data-dec]');
    const inc = e.target.closest('[data-inc]');
    if (dec || inc) {
      const card = e.target.closest('.product-card');
      const input = card.querySelector('.qty-in');
      let val = parseInt(input.value || '1', 10);
      if (Number.isNaN(val) || val < 1) val = 1;
      input.value = String(dec ? Math.max(1, val - 1) : val + 1);
      return;
    }

    const addBtn = e.target.closest('.addCart');
    if (!addBtn) return;

    const card = e.target.closest('.product-card');
    const id = card?.dataset?.id;
    const qty = card?.querySelector('.qty-in')?.value || '1';

    if (!id) return;

    addBtn.disabled = true;
    try {
      const res = await fetch('/shop/add/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ product_id: id, qty })
      });
      if (!res.ok) throw new Error('Add to cart failed');
      const data = await res.json();
      if (data.ok) {
        showToast(`Added: ${data.product.title} (${qty})`);
        // We'll wire header cart badge later; placeholder event:
        document.dispatchEvent(new CustomEvent('cart:updated', { detail: { count: data.cart_count }}));
      } else {
        showToast('Could not add to cart.');
      }
    } catch (err) {
      showToast('Network error.');
    } finally {
      addBtn.disabled = false;
    }
  });
})();
