(() => {
  const $  = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  const form = document.querySelector('.sf-form');
  if (!form) return;

  // Fields (match model/form names)
  const title     = form.querySelector('input[name="title"]');
  const duration_seconds   = form.querySelector('input[name="duration_seconds"]');
  const total     = form.querySelector('[data-total]');

  const isCollab  = form.querySelector('input[name="is_collab"]');
  const collabWrap= form.querySelector('[data-collab-wrap]');
  const kindSel   = form.querySelector('select[name="collab_kind"]'); // headliners | other
  const headWrap  = form.querySelector('[data-collab-headliners]');
  const otherWrap = form.querySelector('[data-collab-other]');
  const headsSel  = form.querySelector('select[name="collaborator_artists"]'); // multiple
  const otherInp  = form.querySelector('input[name="collab_other"]');

  const pillset   = form.querySelector('[data-genres]');
  const genreSel  = form.querySelector('select[name="genre"]');
  const saveBtn   = form.querySelector('button[type="submit"]');

  // Focus ring nicety
  $$('input,select,textarea', form).forEach(el=>{
    el.addEventListener('focus', ()=> el.style.boxShadow = '0 0 0 2px rgba(130,150,255,.25)');
    el.addEventListener('blur',  ()=> el.style.boxShadow = '');
  });

  // Collab UI
  function syncCollab(){
    const on = !!(isCollab && isCollab.checked);
    if (collabWrap) collabWrap.style.display = on ? '' : 'none';
  }
  isCollab?.addEventListener('change', syncCollab);
  syncCollab();

  function syncKind(){
    const k = kindSel?.value || 'headliners';
    if (headWrap) headWrap.style.display = (k==='headliners') ? '' : 'none';
    if (otherWrap) otherWrap.style.display = (k==='other') ? '' : 'none';
  }
  kindSel?.addEventListener('change', syncKind);
  syncKind();

  // Genre pills => set the select
  if (pillset && genreSel){
    pillset.addEventListener('click', (e)=>{
      const pill = e.target.closest('.pill');
      if (!pill) return;
      // single-choice (matches model choices)
      $$('[data-genres] .pill').forEach(p=>p.setAttribute('aria-pressed','false'));
      pill.setAttribute('aria-pressed','true');
      const val = pill.dataset.val;
      if (val && genreSel) genreSel.value = val;
    });

    // hydrate from current select value
    const cur = genreSel.value;
    const active = pillset.querySelector(`.pill[data-val="${CSS.escape(cur)}"]`);
    if (active) active.setAttribute('aria-pressed','true');

    // keep pills in sync if user changes dropdown
    genreSel.addEventListener('change', ()=>{
      $$('[data-genres] .pill').forEach(p=>p.setAttribute('aria-pressed','false'));
      const p = pillset.querySelector(`.pill[data-val="${CSS.escape(genreSel.value)}"]`);
      if (p) p.setAttribute('aria-pressed','true');
    });
  }

  // Validation + prevent double submit
  form.addEventListener('submit', (e)=>{
    const errs = [];
    const ds = parseInt(duration_seconds?.value||'0',10) || 0;

    if (!title?.value.trim()) errs.push('Title is required.');
    if (ds === 0) errs.push('Duration cannot be 0 seconds.');

    if (isCollab?.checked){
      const kind = kindSel?.value || 'headliners';
      if (kind === 'headliners'){
        if (!headsSel || !headsSel.selectedOptions || headsSel.selectedOptions.length === 0){
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
    if (saveBtn){ saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }
  });

  // ⌘/Ctrl+S to save
  window.addEventListener('keydown', (e)=>{
    if ((e.metaKey||e.ctrlKey) && e.key.toLowerCase()==='s'){
      e.preventDefault();
      form.requestSubmit();
    }
  });
})();
