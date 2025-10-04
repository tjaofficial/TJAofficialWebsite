(function(){
  const $ = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  // ------- 1) “Redeem” confirm overlay + double-submit guard -------
  const root = document.querySelector('[data-rewards]');
  if (!root) return;

  // Build a tiny confirm dialog once
  const backdrop = document.createElement('div');
  backdrop.className = 'rw-dialog-backdrop';
  backdrop.innerHTML = `
    <div class="rw-dialog" role="dialog" aria-modal="true" aria-labelledby="rwDlgT">
      <h4 id="rwDlgT">Confirm redemption</h4>
      <p id="rwDlgP">Redeem this reward?</p>
      <div class="row">
        <button type="button" class="rw-btn rw-btn--ghost" data-cancel>Cancel</button>
        <button type="button" class="rw-btn" data-confirm>Redeem</button>
      </div>
    </div>`;
  document.body.appendChild(backdrop);

  const dlg = backdrop.querySelector('.rw-dialog');
  const pTxt = $('#rwDlgP', dlg);
  let pendingForm = null;

  // Snack bar
  const toast = document.createElement('div');
  toast.className = 'rw-toast';
  toast.innerHTML = `<div role="status" aria-live="polite"></div>`;
  document.body.appendChild(toast);
  const showToast = (msg='Done!')=>{
    toast.firstElementChild.textContent = msg;
    toast.classList.add('rw-toast--show');
    setTimeout(()=>toast.classList.remove('rw-toast--show'), 2200);
  };

  // Wire every redeem form to open confirm
  $$('form[data-redeem-form], .reward-tile form').forEach(form => {
    form.addEventListener('submit', (e)=>{
      // prevent multiple submits
      if (form.dataset.submitting === '1') { e.preventDefault(); return; }

      const meta = (form.querySelector('[data-redeem]')?.dataset.redeem || '').split('|');
      const [name, pts] = [meta[0] || 'this reward', meta[1] || 'points'];

      e.preventDefault();
      pTxt.textContent = `Are you sure you want to redeem ${name} for ${pts} points?`;
      pendingForm = form;
      backdrop.style.display = 'flex';
      setTimeout(()=>backdrop.style.opacity = 1, 0);
      dlg.focus();
    }, false);
  });

  // Confirm / Cancel handlers
  backdrop.addEventListener('click', (e)=>{
    if (e.target === backdrop) { // click outside dialog
      backdrop.style.opacity = 0; setTimeout(()=>backdrop.style.display='none', 120);
      pendingForm = null;
    }
  });
  $('[data-cancel]', dlg).addEventListener('click', ()=>{
    backdrop.style.opacity = 0; setTimeout(()=>backdrop.style.display='none', 120);
    pendingForm = null;
  });
  $('[data-confirm]', dlg).addEventListener('click', ()=>{
    if (!pendingForm) return;
    pendingForm.dataset.submitting = '1';
    const btn = pendingForm.querySelector('button[type="submit"]');
    if (btn){ btn.disabled = true; btn.textContent = 'Redeeming…'; }
    // close
    backdrop.style.opacity = 0; setTimeout(()=>backdrop.style.display='none', 80);
    pendingForm.submit();
    // show feedback (in case redirect is slow)
    showToast('Processing redemption…');
  });

  // ------- 2) Gift code UX: uppercase + prevent double submit -------
  const giftForm = root.querySelector('.giftcode-form');
  if (giftForm){
    const input = giftForm.querySelector('input[name="code"]');
    const btn = giftForm.querySelector('button');
    input.addEventListener('input', ()=>{
      input.value = input.value.toUpperCase().replace(/\s+/g,'').slice(0, 32);
    });
    giftForm.addEventListener('submit', ()=>{
      btn.disabled = true;
      btn.textContent = 'Claiming…';
      showToast('Checking your code…');
    });
  }

  // ------- 3) Smooth “see all rewards” anchor (optional nicety) -------
  $$('a[href*="#"]').forEach(a=>{
    a.addEventListener('click', (e)=>{
      const id = a.getAttribute('href');
      if (!id || id.charAt(0) !== '#') return;
      const el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({behavior:'smooth', block:'start'});
    });
  });

  // ------- 4) Tiny interaction polish: pulse on new messages (if any) -------
  const msgCards = $$('.card[role="status"], .messages li');
  if (msgCards.length){
    msgCards.forEach(n=>{
      n.animate([{transform:'scale(1)'},{transform:'scale(1.02)'},{transform:'scale(1)'}], {duration:220});
    });
  }
})();
