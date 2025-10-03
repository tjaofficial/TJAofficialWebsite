(function () {
  const form = document.getElementById('signupForm');
  const btn = document.getElementById('signupBtn');
  const pw = form ? form.querySelector('input[name="password"]') : null;
  const confirmPw = form ? form.querySelector('input[name="confirm_password"]') : null;
  const meter = document.getElementById('pwMeter');
  const hint = document.getElementById('pwHint');

  if (!form) return;

  function scorePassword(val) {
    if (!val) return 0;
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^\w\s]/.test(val)) score++;
    return score;
  }

  pw && pw.addEventListener('input', () => {
    const s = scorePassword(pw.value);
    if (meter) meter.value = s;
    if (hint) {
      const labels = ['Very weak', 'Weak', 'Okay', 'Good', 'Strong'];
      hint.textContent = `Password strength: ${labels[s] || labels[0]}`;
    }
  });

  confirmPw && confirmPw.addEventListener('input', () => {
    if (!pw) return;
    if (confirmPw.value && pw.value !== confirmPw.value) {
      confirmPw.setCustomValidity('Passwords do not match.');
    } else {
      confirmPw.setCustomValidity('');
    }
  });

  form.addEventListener('submit', () => {
    btn?.classList.add('loading');
    btn?.setAttribute('disabled', 'true');
  });
})();
