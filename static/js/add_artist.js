(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const form = $('#add-artist-form');
  if (!form) return;

  // --- Collapsible socials
  const collapsible = $('.collapsible');
  if (collapsible) {
    const head = $('.collapsible-head', collapsible);
    const body = $('.collapsible-body', collapsible);
    const setExpanded = (exp) => {
      collapsible.dataset.collapsed = exp ? 'false' : 'true';
      head.setAttribute('aria-expanded', String(exp));
    };
    setExpanded(false);
    const toggle = () => setExpanded(collapsible.dataset.collapsed === 'true');
    head.addEventListener('click', toggle);
    head.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  }

  // --- Live previews for avatar + hero
  const bindPreview = (fileInput, imgEl) => {
    if (!fileInput || !imgEl) return;
    fileInput.addEventListener('change', () => {
      const f = fileInput.files && fileInput.files[0];
      if (!f) { imgEl.classList.add('hidden'); imgEl.src = ''; return; }
      const url = URL.createObjectURL(f);
      imgEl.src = url;
      imgEl.classList.remove('hidden');
    });
  };
  bindPreview($('#id_avatar'), $('#preview-avatar'));
  bindPreview($('#id_hero_image'), $('#preview-hero'));

  // --- Bio counter
  const bio = $('#id_bio');
  const bioCount = $('#bio-count');
  const BIO_MAX = 800;
  const updateBioCount = () => {
    if (!bio || !bioCount) return;
    const len = bio.value.length;
    bioCount.textContent = len;
    if (len > BIO_MAX) { bio.classList.add('is-invalid'); }
    else { bio.classList.remove('is-invalid'); }
  };
  if (bio) { bio.setAttribute('maxlength', BIO_MAX); bio.addEventListener('input', updateBioCount); updateBioCount(); }

  // --- Username suggestion (from name)
  const nameInput = $('#id_name') || $('input[name="name"]');
  const usernameInput = $('#id_username');
  const suggestBtn = $('#btn-suggest-username');
  if (suggestBtn && nameInput && usernameInput) {
    suggestBtn.addEventListener('click', () => {
      const base = (nameInput.value || '').toLowerCase()
        .replace(/[^a-z0-9]+/g, '')
        .replace(/^the/, '')              // trim common prefixes
        .slice(0, 20);
      if (!base) return;
      // add small hash to reduce collisions
      const hash = Math.random().toString(36).slice(2, 5);
      usernameInput.value = `${base}${hash}`;
      usernameInput.classList.remove('is-invalid');
      usernameInput.focus();
    });
  }

  // --- Basic client-side required validation
  const requiredSelectors = [
    '#id_username',
    '#id_email',
    '#id_name',
    '#id_default_role'
  ];
  const isEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  form.addEventListener('submit', (e) => {
    let ok = true;

    requiredSelectors.forEach(sel => {
      const el = $(sel);
      if (!el) return;
      const val = (el.value || '').trim();
      const fail = (sel === '#id_email') ? !isEmail(val) : !val;
      el.classList.toggle('is-invalid', fail);
      if (fail) ok = false;
    });

    if (!ok) {
      e.preventDefault();
      const firstBad = $('.is-invalid');
      if (firstBad) firstBad.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // loading state
    const btn = $('#btn-submit');
    if (btn) {
      btn.classList.add('loading');
      btn.setAttribute('disabled', 'disabled');
    }
  });

  // --- Light URL normalizer for socials (adds https:// if missing)
  const urlFields = $$('input[type="url"]', form);
  urlFields.forEach(input => {
    input.addEventListener('blur', () => {
      let v = (input.value || '').trim();
      if (!v) return;
      if (!/^https?:\/\//i.test(v)) {
        input.value = `https://${v}`;
      }
    });
  });
})();
