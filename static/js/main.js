(() => {
  // Mark JS-enabled for CSS
  document.documentElement.classList.remove('no-js');

  /* ===== Mobile Nav Toggle ===== */
  const nav = document.querySelector('[data-nav]');
  const toggle = document.querySelector('.nav-toggle');
  if (toggle && nav) {
    const setOpen = (open) => {
      nav.dataset.open = open ? 'true' : 'false';
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open && window.innerWidth < 920 ? 'hidden' : '';
    };
    toggle.addEventListener('click', () => {
      const open = nav.dataset.open !== 'true';
      setOpen(open);
    });
    // Close on link click (mobile)
    nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setOpen(false)));
  }

  /* ===== Sticky Header Shrink ===== */
  const header = document.querySelector('[data-sticky]');
  let lastY = window.scrollY;
  const onScroll = () => {
    const y = window.scrollY;
    if (!header) return;
    header.classList.toggle('shrink', y > 16);
    lastY = y;
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ===== Theme Toggle (Day / Night) ===== */
  const THEME_KEY = 'tja_theme';
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  const applyTheme = (theme) => {
    document.documentElement.classList.toggle('theme-light', theme === 'light');
    // Also update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'light' ? '#fbfbfe' : '#0b0b0f');
  };
  const stored = localStorage.getItem(THEME_KEY);
  const initialTheme = stored || (prefersDark.matches ? 'dark' : 'light');
  applyTheme(initialTheme);
  const toggleBtn = document.querySelector('[data-theme-toggle]');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const next = document.documentElement.classList.contains('theme-light') ? 'dark' : 'light';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }
  if (prefersDark && !stored) {
    prefersDark.addEventListener('change', e => applyTheme(e.matches ? 'dark' : 'light'));
  }

  /* ===== Reveal-on-Scroll ===== */
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!prefersReduced && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });

    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('revealed'));
  }

  /* ===== Subtle Canvas Orb in Hero (no libs) ===== */
  const canvas = document.getElementById('orb');
  if (canvas && canvas.getContext) {
    const ctx = canvas.getContext('2d');
    let w, h, t = 0, rafId;

    const resize = () => {
      w = canvas.width = canvas.offsetWidth;
      h = canvas.height = canvas.offsetHeight;
    };
    const draw = () => {
      t += 0.005;
      ctx.clearRect(0, 0, w, h);

      // gradient blob
      const cx = w * (0.5 + 0.12 * Math.sin(t * 2.1));
      const cy = h * (0.5 + 0.18 * Math.cos(t * 1.6));
      const r  = Math.min(w, h) * 0.45;

      const g = ctx.createRadialGradient(cx, cy, r * 0.1, cx, cy, r);
      g.addColorStop(0, 'rgba(124,92,255,0.45)');
      g.addColorStop(0.5, 'rgba(0,224,255,0.25)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      rafId = requestAnimationFrame(draw);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    draw();

    // Respect reduced motion
    if (prefersReduced) {
      cancelAnimationFrame(rafId);
      ctx.clearRect(0, 0, w, h);
    }
  }
})();

/* ===== Header cart badge: fetch on load + listen for updates ===== */
(() => {
  const badge = document.getElementById('cartBadge');
  if (!badge) return;

  const setCount = (n) => {
    if (n && n > 0) {
      badge.textContent = n;
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  };

  // Initial fetch
  fetch('/cart/count/')
    .then(r => r.ok ? r.json() : { count: 0 })
    .then(d => setCount(d.count || 0))
    .catch(() => setCount(0));

  // Listen to events from shop/cart pages
  document.addEventListener('cart:updated', (e) => setCount(e.detail?.count || 0), false);
})();
