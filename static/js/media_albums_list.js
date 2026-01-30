(() => {
  const forms = document.querySelectorAll('form[action*="toggle_public"]');
  if (!forms.length) return;

  forms.forEach((f) => {
    const btn = f.querySelector('button');
    if (!btn) return;

    f.addEventListener('submit', () => {
      btn.disabled = true;
      const original = btn.textContent;
      btn.textContent = "Updating…";
      btn.style.opacity = "0.75";

      // If something prevents navigation (rare), restore after a sec
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = original;
        btn.style.opacity = "";
      }, 2500);
    });
  });
})();
