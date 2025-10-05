(() => {
  const $ = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  // Reveal on enter
  const snaps = $$('[data-snap], .hl-card[data-obs], .rel-card[data-obs]');
  const io = new IntersectionObserver(es=>{
    es.forEach(e=>{
      if(e.isIntersecting){
        e.target.classList.add('in','reveal');
        io.unobserve(e.target);
      }
    });
  }, {threshold:.12});
  snaps.forEach(el=>io.observe(el));

  // Lazy BGs for headliners (robust)
(() => {
  const els = document.querySelectorAll('[data-lazy-bg]');
  els.forEach(node => {
    const src = node.getAttribute('data-bg');
    if (!src) return; // nothing to load

    // Optional: fade-in
    node.style.opacity = '0';
    node.style.transition = 'opacity .35s ease';

    const img = new Image();
    img.onload = () => {
      node.style.backgroundImage = `url("${src}")`;
      requestAnimationFrame(() => (node.style.opacity = '1'));
    };
    img.onerror = () => {
      // fallback background on error (optional)
      node.style.background = 'linear-gradient(180deg,#111,#0d0d0d)';
      node.style.opacity = '1';
    };
    img.src = src;
  });
})();


  // Slider
  const track = $('[data-track]');
  if (track){
    const prev = $('[data-prev]');
    const next = $('[data-next]');
    const step = () => (track.firstElementChild?.getBoundingClientRect().width || 280) + 12;
    prev?.addEventListener('click', ()=> track.scrollBy({left: -step(), behavior: 'smooth'}));
    next?.addEventListener('click', ()=> track.scrollBy({left:  step(), behavior: 'smooth'}));
  }

  // Video modal (YouTube-only embed ids from model)
  const modal = $('[data-reel]');
  const iframe = modal?.querySelector('iframe');
  const openTiles = $$('[data-open-video]');
  openTiles.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const id = btn.getAttribute('data-embed');
      if(!id || !modal || !iframe) return;
      iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`;
      modal.removeAttribute('hidden');
    });
  });
  const close = $('[data-close-reel]');
  close?.addEventListener('click', ()=>{ if(iframe) iframe.src=''; modal?.setAttribute('hidden',''); });
  modal?.addEventListener('click', (e)=>{ if(e.target === modal){ if(iframe) iframe.src=''; modal.setAttribute('hidden',''); }});

  // Thumbnails for videos (YouTube)
  $$('.vid-tile .thumb').forEach(th=>{
    const id = th.parentElement?.getAttribute('data-embed');
    if(id) th.style.backgroundImage = `url('https://i.ytimg.com/vi/${id}/hqdefault.jpg')`;
  });

  // Marquee duplication to avoid gaps
  const mq = $('[data-marquee] .marquee-track');
  if(mq){
    mq.innerHTML += mq.innerHTML;
  }
})();
