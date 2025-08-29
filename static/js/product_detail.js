/* ===== Product detail: gallery + add to cart reuse ===== */
(() => {
  const mainImg = document.getElementById('pdMainImg');
  const thumbs = document.querySelectorAll('.pd-thumb');
  if (mainImg && thumbs.length) {
    thumbs.forEach(btn => {
      btn.addEventListener('click', () => {
        thumbs.forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        mainImg.src = btn.dataset.src;
      });
    });
  }

  // Reuse add-to-cart from shop; simple local hook
  const detailAdd = document.querySelector('.pd-info .addCart');
  if (detailAdd) {
    const getCookie = (name) => (document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)') || [,'',''])[2];
    const toast = document.getElementById('toast');
    const showToast = (m) => { if (!toast) return; toast.textContent = m; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),1200); };
    const qtyInput = document.querySelector('.pd-info .qty-in');

    document.querySelector('.pd-info').addEventListener('click', async (e) => {
      if (e.target.matches('[data-inc], [data-dec]')) {
        let v = parseInt(qtyInput.value || '1', 10); if (Number.isNaN(v) || v < 1) v = 1;
        v = e.target.hasAttribute('data-inc') ? v + 1 : Math.max(1, v - 1);
        qtyInput.value = String(v);
        return;
      }
      if (e.target.closest('.addCart')) {
        const id = detailAdd.dataset.id, qty = qtyInput.value || '1';
        detailAdd.disabled = true;
        try {
          const res = await fetch('/shop/add/', {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken'),'Content-Type':'application/x-www-form-urlencoded'},
            body: new URLSearchParams({ product_id: id, qty })
          });
          const data = res.ok ? await res.json() : { ok: false };
          if (data.ok) {
            document.dispatchEvent(new CustomEvent('cart:updated', { detail: { count: data.cart_count }}));
            showToast('Added to cart');
          } else showToast('Add failed');
        } catch { showToast('Network error'); }
        finally { detailAdd.disabled = false; }
      }
    });
  }
})();
