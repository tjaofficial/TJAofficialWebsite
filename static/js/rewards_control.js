(function(){
  const $ = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  // ===== tiny toast =====
  const toast = document.createElement('div');
  toast.className = 'rc-toast';
  toast.innerHTML = `<div role="status" aria-live="polite"></div>`;
  document.body.appendChild(toast);
  function showToast(msg){ toast.firstElementChild.textContent = msg; toast.classList.add('rc-toast--show'); setTimeout(()=>toast.classList.remove('rc-toast--show'), 2000); }

  // ===== list page enhancements (reward_items.html) =====
  (function(){
    const table = $('.cp-table');
    if(!table) return;

    // Quick filters (insert if not present)
    let bar = $('.rc-filters');
    if(!bar){
      bar = document.createElement('div');
      bar.className = 'rc-filters';
      bar.innerHTML = `
        <input type="search" placeholder="Search name/SKU…" data-rc-search>
        <select data-rc-type>
          <option value="">All types</option>
          <option value="PRODUCT">Product</option>
          <option value="TICKET">Ticket</option>
          <option value="COUPON">Coupon</option>
          <option value="CUSTOM">Custom</option>
        </select>
        <select data-rc-active>
          <option value="">Any status</option>
          <option value="1">Active</option>
          <option value="0">Inactive</option>
        </select>
        <button class="btn btn-ghost" type="button" data-rc-reset>Reset</button>
      `;
      table.before(bar);
    }

    const rows = $$('tbody tr', table);
    const search = $('[data-rc-search]');
    const typeSel = $('[data-rc-type]');
    const activeSel = $('[data-rc-active]');
    const resetBtn = $('[data-rc-reset]');

    function normalize(s){ return (s||'').toLowerCase().trim(); }
    function textOfRow(tr){
      const tds = $$('td', tr).map(td=>td.textContent.trim()).join(' ');
      return normalize(tds);
    }
    const cache = new Map();
    rows.forEach(r=>cache.set(r, textOfRow(r)));

    function apply(){
      const q = normalize(search.value);
      const type = typeSel.value;
      const active = activeSel.value;

      rows.forEach(tr=>{
        const txt = cache.get(tr);
        const cols = $$('td', tr);
        const typeTxt = (cols[3]?.textContent || '').toUpperCase(); // "Type" col
        const isActive = (cols[7]?.textContent || '').includes('✅') ? '1' : '0';

        let ok = true;
        if(q && !txt.includes(q)) ok = false;
        if(type && !typeTxt.includes(type)) ok = false;
        if(active && active !== isActive) ok = false;

        tr.style.display = ok ? '' : 'none';
      });
    }

    function debounce(fn, ms=160){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
    search.addEventListener('input', debounce(apply, 120));
    typeSel.addEventListener('change', apply);
    activeSel.addEventListener('change', apply);
    resetBtn.addEventListener('click', ()=>{
      search.value=''; typeSel.value=''; activeSel.value='';
      apply(); showToast('Filters cleared');
    });

    // Click to sort by points or inventory
    const ths = $$('thead th', table);
    ths.forEach((th, idx)=>{
      if(['Cost (pts)','Inventory'].includes(th.textContent.trim())){
        th.style.cursor = 'pointer';
        th.title = 'Click to sort';
        let dir = 1;
        th.addEventListener('click', ()=>{
          const tbody = $('tbody', table);
          const rowsArr = $$('.cp-table tbody tr');
          rowsArr.sort((a,b)=>{
            const av = parseInt($$('td', a)[idx].textContent.trim() || '0', 10);
            const bv = parseInt($$('td', b)[idx].textContent.trim() || '0', 10);
            return dir * (av - bv);
          });
          dir *= -1;
          rowsArr.forEach(r=>tbody.appendChild(r));
        });
      }
    });
  })();

  // ===== add/edit form enhancements (reward_item_form.html) =====
  (function(){
    const form = $('.cp-form');
    if(!form) return;

    const typeSel = form.querySelector('select[name="fulfill_type"]');
    const targetProd = $('#targetProduct');
    const targetTick = $('#targetTicket');
    const nameInput = form.querySelector('input[name="name"]');
    const skuInput = form.querySelector('input[name="sku"]');
    const costInput = form.querySelector('input[name="points_cost"]');
    const invInput  = form.querySelector('input[name="inventory"]');
    const qtyInput  = form.querySelector('input[name="quantity_per_redeem"]');

    function syncTarget(){
      const v = typeSel.value;
      targetProd.style.display = (v === 'PRODUCT') ? 'block' : 'none';
      targetTick.style.display = (v === 'TICKET') ? 'block' : 'none';
      // For tickets, quantity per redemption defaults to 1 if empty
      if(v === 'TICKET' && (!qtyInput.value || parseInt(qtyInput.value,10) < 1)){
        qtyInput.value = 1;
      }
    }
    typeSel && typeSel.addEventListener('change', syncTarget);
    syncTarget();

    // Auto-suggest SKU from name (if empty)
    function slugify(s){ return (s||'').toUpperCase().replace(/[^A-Z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,32); }
    nameInput && nameInput.addEventListener('input', ()=>{
      if(!skuInput.value.trim()){
        skuInput.value = slugify(nameInput.value);
      }
    });

    // clamp numeric inputs & live preview toast
    function clampInt(el, min=0, max=999999){
      let v = parseInt(el.value||'0', 10);
      if(isNaN(v)) v = min;
      v = Math.max(min, Math.min(max, v));
      el.value = v;
      return v;
    }
    costInput && costInput.addEventListener('input', ()=>{
      const v = clampInt(costInput, 0, 100000);
      if(v === 0) showToast('Setting this reward to 0 pts (free)');
    });
    invInput && invInput.addEventListener('input', ()=> clampInt(invInput, 0, 100000));
    qtyInput && qtyInput.addEventListener('input', ()=> clampInt(qtyInput, 1, 1000));

    // prevent double submit
    form.addEventListener('submit', ()=>{
      const btn = form.querySelector('button[type="submit"]');
      if(btn){ btn.disabled = true; btn.textContent = 'Saving…'; }
    });
  })();

  // ===== gift page enhancements (gift_reward.html) =====
  (function(){
    const form = document.querySelector('form.cp-form[action$="/rewards/gift/"], form.cp-form:has(select[name="item"])');
    if(!form) return;

    const userSel = form.querySelector('select[name="user"]');
    const itemSel = form.querySelector('select[name="item"]');
    let info = document.createElement('div');
    info.className = 'hint';
    itemSel.parentElement.appendChild(info);

    // lightweight info fetch by reading option text (no API; show simple guidance)
    function updateInfo(){
      const txt = itemSel.options[itemSel.selectedIndex]?.text || '';
      info.textContent = txt ? `Selected: ${txt}` : '';
    }
    itemSel.addEventListener('change', updateInfo);
    updateInfo();

    form.addEventListener('submit', (e)=>{
      const uOk = !!userSel.value;
      const iOk = !!itemSel.value;
      if(!uOk || !iOk){
        e.preventDefault();
        showToast('Pick a user and a reward');
        [userSel, itemSel].forEach(el=>{ if(!el.value){ el.style.boxShadow='0 0 0 3px rgba(255,107,107,.25)'; el.addEventListener('input',()=>el.style.boxShadow=''); }});
        return;
      }
      const btn = form.querySelector('button[type="submit"]');
      if(btn){ btn.disabled = true; btn.textContent = 'Gifting…'; }
    });
  })();

  // ===== confirm delete forms (reward_items list) =====
  (function(){
    const delForms = $$('form[action*="/delete"]');
    if(!delForms.length) return;

    // make a custom modal (nicer than native confirm)
    const backdrop = document.createElement('div');
    backdrop.className = 'rc-backdrop';
    backdrop.innerHTML = `
      <div class="rc-dialog" role="dialog" aria-modal="true" aria-labelledby="rcDlgH">
        <h4 id="rcDlgH">Delete this reward?</h4>
        <p>This action cannot be undone.</p>
        <div class="row">
          <button type="button" class="btn btn-ghost" data-cancel>Cancel</button>
          <button type="button" class="btn btn-danger" data-confirm>Delete</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);

    let pending = null;
    delForms.forEach(f=>{
      f.addEventListener('submit', (e)=>{
        if(f.dataset.ok==='1') return; // already confirmed
        e.preventDefault();
        pending = f;
        backdrop.style.display='flex';
      });
    });
    backdrop.addEventListener('click', (e)=>{
      if(e.target === backdrop){ backdrop.style.display='none'; pending=null; }
    });
    $('[data-cancel]', backdrop).addEventListener('click', ()=>{ backdrop.style.display='none'; pending=null; });
    $('[data-confirm]', backdrop).addEventListener('click', ()=>{
      if(!pending) return;
      pending.dataset.ok='1';
      backdrop.style.display='none';
      pending.submit();
    });
  })();
})();


(function(){
    const sel = document.querySelector('select[name="reward_type"]');
    const tTicket = document.getElementById('giftTargetTicket');
    const tProduct = document.getElementById('giftTargetProduct');
    const qty = document.querySelector('input[name="quantity"]');

    function sync(){
      const v = sel.value;
      tTicket.style.display  = (v === 'TICKET') ? 'block' : 'none';
      tProduct.style.display = (v === 'PRODUCT') ? 'block' : 'none';
      if(v === 'TICKET' && (!qty.value || parseInt(qty.value,10) < 1)){ qty.value = 1; }
      if(v === 'PRODUCT' && (!qty.value || parseInt(qty.value,10) < 1)){ qty.value = 1; }
    }
    sel.addEventListener('change', sync);
    sync();
  })();