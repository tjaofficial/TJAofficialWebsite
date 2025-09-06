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

(function(){
  const form = document.getElementById('addForm');
  if(!form) return;

  const msg = document.getElementById('msg');
  const qtyInput = document.getElementById('qtyInput');

  // qty controls
  document.querySelectorAll('.qbtn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const d = parseInt(btn.dataset.d || '0', 10);
      const v = Math.max(1, parseInt(qtyInput.value || '1', 10) + d);
      qtyInput.value = v;
    });
  });

  // CSRF helper (ensures header always present)
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    if (msg) { msg.textContent = ''; msg.className = 'msg'; }

    const fd = new FormData(form);

    try {
      const r = await fetch(form.action, {
        method: 'POST',
        body: fd,
        headers: {
          'X-Requested-With':'fetch',
          'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'same-origin'
      });

      let data = null;
      const ct = r.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        data = await r.json();
      } else {
        const text = await r.text();
        throw new Error(`Non-JSON response (${r.status}): ${text.slice(0, 200)}`);
      }

      if (!data.ok) {
        if (msg) { msg.textContent = data.error || 'Could not add to cart.'; msg.className = 'msg err'; }
        return;
      }

      document.dispatchEvent(new CustomEvent('cart:updated', {detail: {count: data.cart_count || 0}}));
      if (msg) { msg.textContent = 'Added to cart!'; msg.className = 'msg ok'; }

    } catch (err) {
      console.error('Add to cart failed:', err);
      if (msg) { msg.textContent = 'Something went wrong. Please try again.'; msg.className = 'msg err'; }
    }
  });
})();
