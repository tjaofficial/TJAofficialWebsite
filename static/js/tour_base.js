(() => {
  const $ = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  /* ===== Scroll reveal ===== */
  const reveals = $$('[data-snap]');
  const ro = new IntersectionObserver(es=>{
    es.forEach(e=>{
      if(e.isIntersecting){ e.target.classList.add('in'); ro.unobserve(e.target); }
    });
  }, {threshold:.12});
  reveals.forEach(el=>ro.observe(el));

  /* ===== Particles (starfield) ===== */
  const canvas = $('#tourParticles');
  const ctx = canvas?.getContext('2d');
  let stars = [], raf = 0, w=0, h=0;
  const rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function resize(){
    if(!canvas) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    w = canvas.clientWidth = canvas.parentElement.clientWidth;
    h = canvas.clientHeight = Math.max(280, canvas.parentElement.clientHeight);
    canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
    // rebuild stars based on area
    const target = Math.floor((w*h)/15000);
    stars = Array.from({length: target}, ()=>({
      x: Math.random()*w,
      y: Math.random()*h,
      z: Math.random()*1 + .2,
      a: Math.random()*0.6 + 0.2
    }));
  }
  function draw(){
    if(!ctx) return;
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle = '#ffffff';
    for(const s of stars){
      const size = s.z * 1.6;
      ctx.globalAlpha = s.a;
      ctx.fillRect(s.x, s.y, size, size);
      // slow drift
      s.y += 0.02 + s.z*0.05;
      if(s.y > h){ s.y = -2; s.x = Math.random()*w; }
    }
    ctx.globalAlpha = 1;
    raf = requestAnimationFrame(draw);
  }
  if(canvas && !rm){
    resize(); draw();
    window.addEventListener('resize', ()=>{ cancelAnimationFrame(raf); resize(); draw(); }, {passive:true});
  }

  /* ===== Parallax tilt on hero ===== */
  const hero = $('[data-parallax]');
  if(hero && !rm){
    let rx=0, ry=0, tx=0, ty=0;
    const ease = 0.08;
    function loop(){
      rx += (tx - rx) * ease; ry += (ty - ry) * ease;
      hero.style.transform = `perspective(900px) rotateX(${ry}deg) rotateY(${rx}deg) translateZ(0)`;
      requestAnimationFrame(loop);
    }
    loop();
    window.addEventListener('pointermove', (e)=>{
      const r = hero.getBoundingClientRect();
      const cx = r.left + r.width/2, cy = r.top + r.height/2;
      tx = ((e.clientX - cx) / (r.width/2)) * 15;
      ty = (-(e.clientY - cy) / (r.height/2)) * 15;
    }, {passive:true});
    window.addEventListener('pointerleave', ()=>{ tx=ty=0; }, {passive:true});
  }

  /* ===== Sticky shrink toggler ===== */
  const header = $('.tour-hero');
  let stuck = false;
  function onScroll(){
    const y = window.scrollY || 0;
    const should = y > 24;
    if(should !== stuck){
      stuck = should;
      header?.classList.toggle('is-stuck', stuck);
    }
  }
  onScroll(); window.addEventListener('scroll', onScroll, {passive:true});

  /* ===== Animated nav underline ===== */
  const nav = $('.tour-nav'); const ink = $('.nav-ink', nav);
  function placeInk(el){
    if(!nav || !ink || !el) return;
    const r = el.getBoundingClientRect();
    const rn = nav.getBoundingClientRect();
    const left = r.left - rn.left + 10;
    const width = Math.max(24, r.width - 20);
    ink.style.left = left + 'px';
    ink.style.width = width + 'px';
  }
  const active = $('.tour-nav a.active') || $('.tour-nav a');
  placeInk(active);
  $$('.tour-nav a').forEach(a=>{
    a.addEventListener('mouseenter', ()=>placeInk(a));
    a.addEventListener('focus', ()=>placeInk(a));
  });
  nav?.addEventListener('mouseleave', ()=>placeInk(active));

  /* ===== Lazy BGs for headliners / tiles ===== */
  const lazyBG = $$('[data-lazy-bg]');
  lazyBG.forEach(node=>{
    const src = node.getAttribute('data-bg');
    if(!src) return;
    node.style.opacity = '0';
    node.style.transition = 'opacity .35s ease';
    const img = new Image();
    img.onload = () => {
      node.style.backgroundImage = `url("${src}")`;
      requestAnimationFrame(()=> node.style.opacity = '1');
    };
    img.onerror = () => { node.style.opacity = '1'; };
    img.src = src;
  });

})();
