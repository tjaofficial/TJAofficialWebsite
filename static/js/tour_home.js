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

  // Lazy BGs for headliners
  $$('[data-lazy-bg]').forEach(node=>{
    const src = node.getAttribute('data-bg');
    if(!src) return;
    const img = new Image();
    img.onload = () => node.style.backgroundImage = `url('${src}')`;
    img.src = src;
  });

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
