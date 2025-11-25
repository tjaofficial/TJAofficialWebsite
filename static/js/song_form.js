(() => {
  const $  = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  const form = $('.sf-form');
  if (!form) return;

  // Fields
  const titleEl    = $('input[name="title"]', form);
  const minutesEl  = $('input[name="minutes"]', form);
  const secondsEl  = $('input[name="seconds"]', form);
  const totalChip  = $('[data-total]', form);

  const isCollabEl = $('input[name="is_collab"]', form);
  const collabWrap = $('[data-collab-wrap]', form);     // collapsible container
  const kindSel    = $('select[name="collab_kind"]', form);
  const headWrap   = $('[data-collab-headliners]', form);
  const otherWrap  = $('[data-collab-other]', form);
  const headsSel   = $('select[name="collaborator_artists"]', form);
  const otherInp   = $('input[name="collab_other"]', form);

  const pillset    = $('[data-genres]', form);
  const genreSel   = $('select[name="genre"]', form);
  const saveBtn    = $('button[type="submit"]', form);

  // ===== Duration live total =====
  function updateTotal(){
    const mins = parseInt(minutesEl?.value || '0', 10) || 0;
    const secs = parseInt(secondsEl?.value || '0', 10) || 0;
    const total = mins * 60 + secs;
    const m = Math.floor(total / 60);
    const s = total % 60;
    if (totalChip) totalChip.textContent = `${m}:${String(s).padStart(2,'0')}`;
  }
  minutesEl?.addEventListener('input', updateTotal);
  secondsEl?.addEventListener('input', updateTotal);
  updateTotal();

  // ===== Collab collapse =====
  function syncCollab(){
    const on = !!(isCollabEl && isCollabEl.checked);
    if (!collabWrap) return;
    collabWrap.classList.toggle('is-open', on);
  }
  isCollabEl?.addEventListener('change', syncCollab);
  syncCollab();

  function syncKind(){
    const k = kindSel?.value || 'headliners';
    if (headWrap) headWrap.style.display = (k === 'headliners') ? '' : 'none';
    if (otherWrap) otherWrap.style.display = (k === 'other') ? '' : 'none';
  }
  kindSel?.addEventListener('change', syncKind);
  syncKind();

  // ===== Genre pills =====
  if (pillset && genreSel){
    const setActive = (val)=>{
      $$('.pill', pillset).forEach(p=>p.setAttribute('aria-pressed','false'));
      const active = $(`.pill[data-val="${CSS.escape(val)}"]`, pillset);
      if (active) active.setAttribute('aria-pressed','true');
      genreSel.value = val;
    };

    pillset.addEventListener('click', (e)=>{
      const pill = e.target.closest('.pill');
      if (!pill) return;
      setActive(pill.dataset.val);
    });

    if (genreSel.value) setActive(genreSel.value);

    genreSel.addEventListener('change', ()=> setActive(genreSel.value));
  }

  // ===== Validation + prevent double submit =====
  form.addEventListener('submit', (e)=>{
    const errs = [];
    const mins = parseInt(minutesEl?.value||'0',10) || 0;
    const secs = parseInt(secondsEl?.value||'0',10) || 0;

    if (!titleEl?.value.trim()) errs.push('Title is required.');
    if (mins === 0 && secs === 0) errs.push('Minutes and seconds cannot both be 0.');

    if (isCollabEl?.checked){
      const kind = kindSel?.value || 'headliners';
      if (kind === 'headliners'){
        if (!headsSel?.selectedOptions?.length){
          errs.push('Choose at least one headliner collaborator.');
        }
      } else {
        if (!otherInp?.value.trim()){
          errs.push('Enter collaborator name(s).');
        }
      }
    }

    if (errs.length){
      e.preventDefault();
      alert(errs.join('\n'));
      return;
    }

    if (saveBtn){
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving…';
    }
  });

  // Ctrl/⌘ + S submit
  window.addEventListener('keydown', (e)=>{
    if ((e.metaKey||e.ctrlKey) && e.key.toLowerCase()==='s'){
      e.preventDefault();
      form.requestSubmit();
    }
  });
})();
