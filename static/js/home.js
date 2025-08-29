/* Home: gentle parallax on hero background */
(() => {
  const bg = document.querySelector('.home-hero__bg');
  if (!bg) return;
  let rx = 0, ry = 0, tx = 0, ty = 0;
  const lerp = (a,b,t)=>a+(b-a)*t;
  window.addEventListener('mousemove', (e) => {
    const x = (e.clientX / window.innerWidth) - 0.5;
    const y = (e.clientY / window.innerHeight) - 0.5;
    rx = x * 12; ry = y * 8;
  });
  function frame(){
    tx = lerp(tx, rx, 0.06);
    ty = lerp(ty, ry, 0.06);
    bg.style.transform = `translate(${tx}px, ${ty}px)`;
    requestAnimationFrame(frame);
  }
  frame();
})();
