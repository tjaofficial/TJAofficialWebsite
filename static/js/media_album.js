(() => {
  const grid = document.getElementById("masonry");
  const lb = document.getElementById("lightbox");
  if (!grid || !lb) return;

  const stage = document.getElementById("lbStage");
  const caption = document.getElementById("lbCaption");
  const statusEl = document.getElementById("lbStatus");

  const btnClose = lb.querySelector(".lb-close");
  const btnPrev = lb.querySelector(".lb-prev");
  const btnNext = lb.querySelector(".lb-next");
  const btnCopy = lb.querySelector(".lb-copy");

  const pills = Array.from(document.querySelectorAll(".pill"));
  const search = document.getElementById("mediaSearch");

  const allItems = Array.from(grid.querySelectorAll(".m-item"));
  let active = allItems.slice(); // filtered list
  let idx = -1;

  // ----------------------------
  // Video thumbnail magic (YT/Vimeo)
  // ----------------------------
  const ytIdFrom = (url) => {
    if (!url) return "";
    const m1 = url.match(/[?&]v=([A-Za-z0-9_-]{6,})/);
    if (m1) return m1[1];
    const m2 = url.match(/youtu\.be\/([A-Za-z0-9_-]{6,})/);
    if (m2) return m2[1];
    const m3 = url.match(/\/embed\/([A-Za-z0-9_-]{6,})/);
    if (m3) return m3[1];
    return "";
  };

  const vimeoIdFrom = (url) => {
    if (!url) return "";
    const m = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
    return m ? m[1] : "";
  };

  const setVideoThumbs = () => {
    const vids = allItems.filter(el => el.dataset.kind === "video");
    vids.forEach(el => {
      const card = el.querySelector(".v-card");
      if (!card) return;

      // avoid double init
      if (card.querySelector(".v-thumb")) return;

      const embed = el.dataset.embed || "";
      const url = el.dataset.url || embed;

      let thumb = "";
      const yid = ytIdFrom(url) || ytIdFrom(embed);
      if (yid) {
        // hqdefault is reliable. maxresdefault sometimes 404.
        thumb = `https://i.ytimg.com/vi/${yid}/hqdefault.jpg`;
      } else {
        const vid = vimeoIdFrom(url);
        // Vimeo thumbs require API; we skip and use fallback gradient.
        thumb = "";
      }

      const div = document.createElement("div");
      div.className = "v-thumb";
      if (thumb) div.style.backgroundImage = `url('${thumb}')`;
      card.prepend(div);
    });
  };

  setVideoThumbs();

  // ----------------------------
  // Lightbox open/close/nav
  // ----------------------------
  const setHash = (id) => {
    // keep hash stable for deep link without scrolling jump
    history.replaceState(null, "", `#m-${id}`);
  };

  const clearHash = () => {
    // remove hash
    const url = window.location.href.replace(/#m-\d+$/, "");
    history.replaceState(null, "", url);
  };

  const render = (el) => {
    const kind = el.dataset.kind;
    const cap = el.dataset.caption || "";
    const id = el.dataset.id || "";
    caption.textContent = cap;

    // status
    if (statusEl) statusEl.textContent = active.length ? `${idx + 1} / ${active.length}` : "";

    // stage content
    // Keep nav buttons visible; we only replace media node.
    const existingMedia = stage.querySelector("img, iframe, .lb-loading");
    if (existingMedia) existingMedia.remove();

    // loading indicator
    const loading = document.createElement("div");
    loading.className = "lb-loading";
    loading.textContent = "Loading…";
    loading.style.color = "rgba(255,255,255,.7)";
    loading.style.fontWeight = "800";
    loading.style.padding = "20px";
    stage.prepend(loading);

    if (kind === "photo") {
      const img = document.createElement("img");
      img.src = el.getAttribute("href");
      img.alt = cap || "Photo";
      img.onload = () => loading.remove();
      img.onerror = () => { loading.textContent = "Failed to load image."; };
      stage.prepend(img);
    } else {
      const src = (el.dataset.embed || "").trim();

      // Safety: only allow known embed hosts
      const ok =
        src.startsWith("https://www.youtube-nocookie.com/embed/") ||
        src.startsWith("https://www.youtube.com/embed/") ||
        src.startsWith("https://player.vimeo.com/video/");

      if (!ok) {
        loading.textContent = "Video link is invalid or missing.";
        return;
      }

      const iframe = document.createElement("iframe");
      iframe.src = src + "?autoplay=1&rel=0&modestbranding=1";
      iframe.allow = "autoplay; encrypted-media; fullscreen; picture-in-picture";
      iframe.allowFullscreen = true;
      iframe.onload = () => loading.remove();
      stage.prepend(iframe);
    }

    if (id) setHash(id);
  };

  const open = (i) => {
    idx = i;
    const el = active[idx];
    if (!el) return;

    lb.hidden = false;
    document.body.style.overflow = "hidden";
    render(el);
  };

  const close = () => {
    lb.hidden = true;
    document.body.style.overflow = "";
    idx = -1;

    // clear media nodes
    stage.querySelectorAll("img, iframe, .lb-loading").forEach(n => n.remove());
    caption.textContent = "";
    if (statusEl) statusEl.textContent = "";

    clearHash();
  };

  const next = () => { if (active.length) open((idx + 1) % active.length); };
  const prev = () => { if (active.length) open((idx - 1 + active.length) % active.length); };

  grid.addEventListener("click", (e) => {
    const a = e.target.closest(".m-item");
    if (!a) return;

    // Reaction button? Don't open lightbox.
    if (e.target.closest(".rxn")) return;

    e.preventDefault();
    const i = active.indexOf(a);
    if (i >= 0) open(i);
  });

  btnClose?.addEventListener("click", close);
  btnNext?.addEventListener("click", next);
  btnPrev?.addEventListener("click", prev);

  // click outside shell closes
  lb.addEventListener("click", (e) => {
    if (e.target === lb) close();
  });

  window.addEventListener("keydown", (e) => {
    if (lb.hidden) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowRight") next();
    if (e.key === "ArrowLeft") prev();
  });

  // Copy link
  btnCopy?.addEventListener("click", async () => {
    const el = active[idx];
    if (!el) return;
    const id = el.dataset.id;
    const url = `${window.location.origin}${window.location.pathname}#m-${id}`;
    try{
      await navigator.clipboard.writeText(url);
      btnCopy.textContent = "Copied ✅";
      setTimeout(() => (btnCopy.textContent = "Copy link"), 900);
    }catch{
      btnCopy.textContent = "Copy failed";
      setTimeout(() => (btnCopy.textContent = "Copy link"), 900);
    }
  });

  // ----------------------------
  // Swipe on mobile (lightbox)
  // ----------------------------
  let touchX = 0;
  let touchY = 0;
  let touching = false;

  lb.addEventListener("touchstart", (e) => {
    if (lb.hidden) return;
    const t = e.touches[0];
    touchX = t.clientX;
    touchY = t.clientY;
    touching = true;
  }, { passive: true });

  lb.addEventListener("touchend", (e) => {
    if (lb.hidden || !touching) return;
    touching = false;

    const t = e.changedTouches[0];
    const dx = t.clientX - touchX;
    const dy = t.clientY - touchY;

    // horizontal swipe
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0) next();
      else prev();
    }
    // swipe down to close (nice on mobile)
    if (dy > 110 && Math.abs(dy) > Math.abs(dx) * 1.2) {
      close();
    }
  }, { passive: true });

  // ----------------------------
  // Filtering (pills) + Search
  // Smooth: we toggle a class and let CSS handle it
  // ----------------------------
  const matches = (el, { kind, q }) => {
    if (kind !== "all" && el.dataset.kind !== kind) return false;
    if (q) {
      const text = (el.dataset.caption || "").toLowerCase();
      if (!text.includes(q)) return false;
    }
    return true;
  };

  const applyFilters = () => {
    const kind = (document.querySelector(".pill.active")?.dataset.filter) || "all";
    const q = (search?.value || "").trim().toLowerCase();

    allItems.forEach(el => {
      const ok = matches(el, { kind, q });
      el.classList.toggle("is-hidden", !ok);
    });

    active = allItems.filter(el => !el.classList.contains("is-hidden"));

    // If lightbox open, keep it consistent:
    if (!lb.hidden) {
      // if current item got filtered out, close
      const current = active[idx];
      if (!current) close();
      else {
        // update idx to current element index in active
        const curEl = stage.querySelector("img, iframe") ? active[idx] : null;
        if (curEl) idx = active.indexOf(curEl);
        if (idx < 0 && active.length) idx = 0;
        if (active.length) open(idx);
      }
    }
  };

  pills.forEach(p => {
    p.type = "button";
    p.addEventListener("click", () => {
      pills.forEach(x => x.classList.remove("active"));
      p.classList.add("active");
      applyFilters();
    });
  });

  if (search) {
    let t = null;
    search.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(applyFilters, 70);
    });
  }

  // Hide helper class
  const style = document.createElement("style");
  style.textContent = `.is-hidden{ display:none !important; }`;
  document.head.appendChild(style);

  // ----------------------------
  // Reactions (LocalStorage V1, nicer UX)
  // ----------------------------
  const keyFor = (id) => `media_rxn_${id}`;
  const loadCounts = (id) => {
    try { return JSON.parse(localStorage.getItem(keyFor(id)) || "{}"); }
    catch { return {}; }
  };
  const saveCounts = (id, obj) => localStorage.setItem(keyFor(id), JSON.stringify(obj));

  const syncCountsUI = (wrap) => {
    const id = wrap.dataset.id;
    const counts = loadCounts(id);
    wrap.querySelectorAll(".rxn-count").forEach(span => {
      const k = span.dataset.k;
      span.textContent = String(counts[k] || 0);
    });
  };

  document.querySelectorAll(".m-reactions").forEach(syncCountsUI);

  grid.addEventListener("click", (e) => {
    const btn = e.target.closest(".rxn");
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const wrap = btn.closest(".m-reactions");
    const id = wrap.dataset.id;
    const emoji = btn.dataset.emoji; // fire/trophy

    const counts = loadCounts(id);
    counts[emoji] = (counts[emoji] || 0) + 1;
    saveCounts(id, counts);
    syncCountsUI(wrap);

    btn.classList.remove("pop");
    void btn.offsetWidth; // reflow to restart anim
    btn.classList.add("pop");
  });

  // ----------------------------
  // Deep link: open #m-123 on load
  // ----------------------------
  const openFromHash = () => {
    const m = window.location.hash.match(/^#m-(\d+)$/);
    if (!m) return;
    const id = m[1];
    const el = document.getElementById(`m-${id}`);
    if (!el) return;

    // ensure filters won't hide it
    pills.forEach(x => x.classList.remove("active"));
    const allPill = pills.find(x => x.dataset.filter === "all");
    if (allPill) allPill.classList.add("active");
    if (search) search.value = "";
    applyFilters();

    // scroll it into view then open
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    const i = active.indexOf(el);
    if (i >= 0) open(i);
  };

  openFromHash();
})();
