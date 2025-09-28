// Simple countdown + sticky visibility + copy-link
(() => {
  const cdWrap = document.querySelector("[data-countdown]");
  if (cdWrap) {
    const deadline = new Date(cdWrap.getAttribute("data-countdown"));
    const $d = cdWrap.querySelector("[data-d]");
    const $h = cdWrap.querySelector("[data-h]");
    const $m = cdWrap.querySelector("[data-m]");
    const $s = cdWrap.querySelector("[data-s]");

    const tick = () => {
      const now = new Date();
      let diff = Math.max(0, Math.floor((deadline - now) / 1000));
      const d = Math.floor(diff / 86400); diff -= d * 86400;
      const h = Math.floor(diff / 3600);  diff -= h * 3600;
      const m = Math.floor(diff / 60);    diff -= m * 60;
      const s = diff;
      if ($d) $d.textContent = d;
      if ($h) $h.textContent = h;
      if ($m) $m.textContent = m;
      if ($s) $s.textContent = s;
    };
    tick();
    setInterval(tick, 1000);
  }

  // Copy URL
  const copyBtn = document.querySelector("[data-copy-url]");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(window.location.href);
        copyBtn.textContent = "Copied!";
        setTimeout(() => (copyBtn.textContent = "Copy Link"), 1200);
      } catch (e) {
        alert("Could not copy.");
      }
    });
  }

  // Show/hide sticky bar after user scrolls past hero title
  const sticky = document.querySelector("[data-sticky]");
  const title = document.querySelector(".event-title");
  if (sticky && title) {
    const obs = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          // When title is not visible, sticky stands out more (we already use CSS position:sticky)
          sticky.style.opacity = entry.isIntersecting ? "0.0" : "1.0";
          sticky.style.pointerEvents = entry.isIntersecting ? "none" : "auto";
        });
      }, { threshold: 0.1 }
    );
    obs.observe(title);
  }
})();
