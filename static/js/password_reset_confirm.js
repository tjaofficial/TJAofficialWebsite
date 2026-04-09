(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const form = $('#pw-form');
  if (!form) return;

  const pw1 = $('#id_new_password1');
  const pw2 = $('#id_new_password2');
  const bar = $('#pw-strength');
  const rules = $('#pw-rules');
  const matchEl = $('#pw-match');
  const submitBtn = $('#pw-submit');

  const ruleEl = (k) => rules ? rules.querySelector(`[data-ok="${k}"]`) : null;

  // Show/Hide toggles
  $$('.pw-input .toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      if (!input) return;

      const on = input.getAttribute('type') === 'password';
      input.setAttribute('type', on ? 'text' : 'password');
      btn.textContent = on ? 'Hide' : 'Show';
      input.focus();
    });
  });

  if (!pw1 || !pw2) return;

  // Strength rules
  const hasLower = (s) => /[a-z]/.test(s);
  const hasUpper = (s) => /[A-Z]/.test(s);
  const hasSym = (s) => /[^A-Za-z0-9]/.test(s);

  function updateStrength() {
    const v = pw1.value || '';

    const okMin = v.length >= 8;
    const okMix = /[A-Za-z]/.test(v) && /\d/.test(v);
    const okCase = hasLower(v) && hasUpper(v);
    const okSym = hasSym(v);

    ruleEl('min')?.classList.toggle('ok', okMin);
    ruleEl('mix')?.classList.toggle('ok', okMix);
    ruleEl('case')?.classList.toggle('ok', okCase);
    ruleEl('symbol')?.classList.toggle('ok', okSym);

    let score = 0;
    score += okMin ? 1 : 0;
    score += okMix ? 1 : 0;
    score += okCase ? 1 : 0;
    score += okSym ? 1 : 0;

    if (bar) {
      const widths = ['10%', '30%', '55%', '80%', '100%'];
      const colors = ['#ef4444', '#f59e0b', '#fbbf24', '#22c55e', '#16a34a'];
      bar.style.width = widths[score];
      bar.style.background = colors[score];
    }

    pw1.classList.toggle('is-invalid', score < 2);
  }

  function updateMatch() {
    const a = pw1.value || '';
    const b = pw2.value || '';

    if (!a && !b) {
      if (matchEl) {
        matchEl.textContent = '';
        matchEl.className = 'match';
      }
      pw2.classList.remove('is-invalid');
      return;
    }

    if (a === b) {
      if (matchEl) {
        matchEl.textContent = 'Passwords match';
        matchEl.className = 'match ok';
      }
      pw2.classList.remove('is-invalid');
    } else {
      if (matchEl) {
        matchEl.textContent = 'Passwords do not match';
        matchEl.className = 'match bad';
      }
      pw2.classList.add('is-invalid');
    }
  }

  pw1.addEventListener('input', () => {
    updateStrength();
    updateMatch();
  });

  pw2.addEventListener('input', updateMatch);

  updateStrength();
  updateMatch();

  // Submit guard
  form.addEventListener('submit', (e) => {
    updateStrength();
    updateMatch();

    const badStrength = pw1.classList.contains('is-invalid');
    const mismatch = pw2.classList.contains('is-invalid');

    if (badStrength || mismatch) {
      e.preventDefault();
      (badStrength ? pw1 : pw2).scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    if (submitBtn) {
      submitBtn.classList.add('loading');
      submitBtn.setAttribute('disabled', 'disabled');
    }
  });
})();