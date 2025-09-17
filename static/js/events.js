// Animate cards on scroll
(() => {
  const cards = document.querySelectorAll(".evt-card");
  if (!cards.length) return;
  const obs = new IntersectionObserver((ents) => {
    ents.forEach(e => { if (e.isIntersecting) e.target.classList.add("is-in"); });
  }, { rootMargin: "0px 0px -10% 0px", threshold: 0.05 });
  cards.forEach(c => obs.observe(c));
})();

// Sticky filter UX: auto-submit on change + pushState
(() => {
  const form = document.getElementById("evtFilterForm");
  if (!form) return;
  form.addEventListener("change", () => {
    const data = new FormData(form);
    const params = new URLSearchParams(data);
    const url = `${location.pathname}?${params.toString()}`;
    history.replaceState(null, "", url);
    form.submit();
  });
})();
