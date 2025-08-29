/* ===== Passport interactions ===== */
(() => {
  const wrap = document.querySelector('.passport-wrap');
  if (!wrap) return;

  // 1) Confetti burst if we see a success notice
  const hasSuccess = !!wrap.querySelector('.notice.success');
  if (hasSuccess) {
    burstConfetti();
  }

  // 2) Redeem input helpers
  const codeIn = document.getElementById('redeemCode');
  const pasteBtn = document.getElementById('pasteBtn');
  const form = document.getElementById('redeemForm');

  if (codeIn) {
    // Uppercase & strip spaces
    codeIn.addEventListener('input', () => {
      codeIn.value = codeIn.value.toUpperCase().replace(/\s+/g, '');
    });
    // Submit on Enter works by default; simulate a little press animation
    form?.addEventListener('submit', () => {
      document.getElementById('redeemBtn')?.classList.add('active');
      setTimeout(() => document.getElementById('redeemBtn')?.classList.remove('active'), 300);
    });
  }
  // Paste from clipboard
  pasteBtn?.addEventListener('click', async () => {
    try {
      const txt = await navigator.clipboard.readText();
      if (txt) {
        codeIn.value = txt.trim().toUpperCase();
        codeIn.focus();
      }
    } catch (_) {
      // clipboard might be blocked
    }
  });

  // 3) Milestone ring animation
  const ring = document.querySelector('.ring');
  if (ring) {
    const svg = ring.querySelector('.ring-svg');
    // Add a gradient def once
    if (svg && !svg.querySelector('defs')) {
      const defs = document.createElementNS('http://www.w3.org/2000/svg','defs');
      const lg = document.createElementNS('http://www.w3.org/2000/svg','linearGradient');
      lg.setAttribute('id','grad'); lg.setAttribute('x1','0'); lg.setAttribute('y1','0'); lg.setAttribute('x2','1'); lg.setAttribute('y2','1');
      const s1 = document.createElementNS('http://www.w3.org/2000/svg','stop'); s1.setAttribute('offset','0%'); s1.setAttribute('stop-color','#7c5cff');
      const s2 = document.createElementNS('http://www.w3.org/2000/svg','stop'); s2.setAttribute('offset','100%'); s2.setAttribute('stop-color','#3cd1e4');
      lg.appendChild(s1); lg.appendChild(s2); defs.appendChild(lg); svg.prepend(defs);
    }
    const fg = ring.querySelector('.ring-fg');
    const total = 339.292; // circumference
    const pct = Math.max(0, Math.min(100, parseInt(ring.dataset.progress || '0', 10)));
    const offset = total - (total * pct / 100);
    requestAnimationFrame(() => { fg.style.strokeDashoffset = String(offset); });
  }

  // 4) Tiny confetti function (no libs)
  function burstConfetti() {
    const n = 50;
    const elms = [];
    for (let i=0;i<n;i++){
      const s = document.createElement('i');
      s.style.position='fixed';
      s.style.left = (Math.random()*100)+'vw';
      s.style.top = '-10px';
      s.style.width = s.style.height = (6 + Math.random()*6)+'px';
      s.style.background = ['#7c5cff','#3cd1e4','#ffd166','#06d6a0','#ef476f'][i%5];
      s.style.opacity='0.9';
      s.style.zIndex='2000';
      s.style.transform='translateZ(0)';
      document.body.appendChild(s);
      elms.push(s);
      const fall = 100 + Math.random()*60;
      const drift = (Math.random()*2-1)*40;
      s.animate([
        { transform:`translate(0,0) rotate(0deg)`, opacity:1 },
        { transform:`translate(${drift}px, ${fall}vh) rotate(${720*Math.random()}deg)`, opacity:0.9 }
      ], { duration: 1200 + Math.random()*800, easing:'cubic-bezier(.22,.61,.36,1)' })
      .onfinish = () => s.remove();
    }
  }

  // 5) If there’s an error notice, give the redeem box a shake
  if (wrap.querySelector('.notice.error')) {
    const box = document.querySelector('.redeem-box');
    box?.classList.add('shake');
    setTimeout(()=>box?.classList.remove('shake'), 600);
  }
})();


/* ===== Passport: QR scanner + level anim ===== */
(() => {
  const scanBtn     = document.getElementById('scanBtn');
  const stopBtn     = document.getElementById('stopScanBtn');
  const qrBox       = document.getElementById('qrBox');
  const qrVideo     = document.getElementById('qrVideo');
  const qrCanvas    = document.getElementById('qrCanvas');
  const qrStatus    = document.getElementById('qrStatus');
  const codeInput   = document.getElementById('redeemCode');
  const redeemForm  = document.getElementById('redeemForm');

  // Animate level bar on load
  const lvlFill = document.querySelector('.lvl-fill');
  if (lvlFill) {
    const w = lvlFill.style.width || '0%';
    lvlFill.style.width = '0%';
    requestAnimationFrame(() => { requestAnimationFrame(() => { lvlFill.style.width = w; }); });
  }

  if (!scanBtn || !qrBox || !qrVideo) return;

  let stream = null;
  let rafId = 0;
  let detector = null;
  let supported = false;

  async function initDetector() {
    try {
      if ('BarcodeDetector' in window) {
        const formats = await BarcodeDetector.getSupportedFormats?.() || [];
        if (!formats.length || !formats.includes('qr_code')) {
          // Some browsers omit formats list—still try QR-only
          detector = new BarcodeDetector({ formats: ['qr_code'] });
        } else {
          detector = new BarcodeDetector({ formats: ['qr_code'] });
        }
        supported = true;
      } else {
        supported = false;
      }
    } catch {
      supported = false;
    }
  }

  async function startScan() {
    await initDetector();
    qrStatus.textContent = supported ? 'Starting camera…' : 'QR detection not supported—try manual entry.';
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, audio: false
      });
      qrVideo.srcObject = stream;
      qrBox.hidden = false;
      qrStatus.textContent = supported ? 'Point camera at QR code' : 'Camera on (QR decode not supported here)';
      loop();
    } catch (err) {
      qrStatus.textContent = 'Camera permission denied or unavailable.';
    }
  }

  function stopScan() {
    cancelAnimationFrame(rafId);
    if (qrVideo) qrVideo.pause?.();
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    qrBox.hidden = true;
    qrStatus.textContent = '';
  }

  async function loop() {
    if (!qrVideo || qrVideo.readyState < 2) { rafId = requestAnimationFrame(loop); return; }

    if (supported && detector) {
      try {
        const codes = await detector.detect(qrVideo);
        if (codes && codes.length) {
          const raw = (codes[0].rawValue || '').trim().toUpperCase();
          if (raw) {
            codeInput.value = raw;
            stopScan();
            // Auto-submit
            redeemForm.submit();
            return;
          }
        }
      } catch {
        // ignore and keep scanning
      }
    } else {
      // Fallback: sample frames (no decode—keep status visible)
      // We keep the preview for user to type code from QR if needed.
    }
    rafId = requestAnimationFrame(loop);
  }

  scanBtn.addEventListener('click', startScan);
  stopBtn?.addEventListener('click', stopScan);
  // Stop when navigating away
  window.addEventListener('pagehide', stopScan);
})();
