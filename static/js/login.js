(function () {
  const form = document.getElementById('loginForm');
  const submitBtn = document.getElementById('submitBtn');
  const btnText = submitBtn.querySelector('.btn-text');
  const username = document.getElementById('id_username');
  const password = document.getElementById('id_password');
  const togglePass = document.getElementById('togglePass');
  const capsHint = document.getElementById('capsHint');

  // Show/Hide password
  togglePass.addEventListener('click', () => {
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);
    togglePass.textContent = type === 'password' ? '👁' : '🙈';
  });

  // Caps Lock detection
  function handleCaps(e) {
    const caps = e.getModifierState && e.getModifierState('CapsLock');
    capsHint.style.display = caps ? 'block' : 'none';
  }
  password.addEventListener('keydown', handleCaps);
  password.addEventListener('keyup', handleCaps);

  // Validation
  function validate() {
    return username.value.trim().length > 0 && password.value.trim().length > 0;
  }

  function toggleSubmit() {
    submitBtn.disabled = !validate();
  }
  username.addEventListener('input', toggleSubmit);
  password.addEventListener('input', toggleSubmit);
  toggleSubmit();

  // Loading state
  form.addEventListener('submit', function () {
    if (!validate()) { return; }
    submitBtn.disabled = true;
    btnText.textContent = 'Logging in…';
  });

  // Autofocus logic
  if (!username.value) username.focus(); else password.focus();
})();
