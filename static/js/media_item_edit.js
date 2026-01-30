(() => {
  const kind = document.querySelector('select[name="kind"]');
  if (!kind) return;

  // Django renders fields as <p> wrappers with label+input inside.
  // We'll find the wrapper <p> for image/url.
  const imageInput = document.querySelector('input[name="image"]');
  const urlInput   = document.querySelector('input[name="url"]');

  const imageWrap = imageInput ? imageInput.closest('p') : null;
  const urlWrap   = urlInput ? urlInput.closest('p') : null;

  const apply = () => {
    const v = kind.value;
    if (v === "photo") {
      if (imageWrap) imageWrap.classList.remove('is-hidden');
      if (urlWrap) urlWrap.classList.add('is-hidden');
    } else if (v === "video") {
      if (urlWrap) urlWrap.classList.remove('is-hidden');
      if (imageWrap) imageWrap.classList.add('is-hidden');
    }
  };

  kind.addEventListener('change', apply);
  apply();
})();
