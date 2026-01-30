(() => {
  const search = document.getElementById("albumSearch");
  const pills = Array.from(document.querySelectorAll(".pill[data-view]"));
  const yearChips = document.getElementById("yearChips");
  const yearHeadings = Array.from(document.querySelectorAll(".year-heading"));
  const cards = Array.from(document.querySelectorAll(".show-card"));

  const topShots = document.getElementById("topShots");
  const topShotsRail = document.getElementById("topShotsRail");

  if (!cards.length) return;

  // --- Helpers
  const norm = (s) => (s || "").toString().toLowerCase().trim();
  const getCount = (el) => parseInt(el.dataset.count || "0", 10) || 0;
  const getYear = (el) => (el.dataset.year || "").toString();

  // --- State
  let state = {
    q: "",
    view: "all",       // all | has-media | empty
    year: "all",       // all | undated | "2026" ...
  };

  // --- Apply filters
  const apply = () => {
    const q = norm(state.q);

    // Filter cards
    cards.forEach((c) => {
      const title = norm(c.dataset.title);
      const city  = norm(c.dataset.city);
      const st    = norm(c.dataset.state);
      const date  = norm(c.dataset.date);
      const year  = (c.dataset.year || "").toString() || (c.dataset.date ? c.dataset.date.slice(0,4) : "");

      const count = getCount(c);

      const matchesText =
        !q ||
        title.includes(q) ||
        city.includes(q) ||
        st.includes(q) ||
        date.includes(q) ||
        year.includes(q) ||
        (count.toString().includes(q));

      const matchesView =
        state.view === "all" ||
        (state.view === "has-media" && count > 0) ||
        (state.view === "empty" && count === 0);

      const matchesYear =
        state.year === "all" ||
        (state.year === "undated" && !year) ||
        (year === state.year);

      const ok = matchesText && matchesView && matchesYear;
      c.classList.toggle("is-hidden", !ok);
    });

    // Show/hide year headings based on whether any visible card under them exists
    // We infer by scanning forward until next heading.
    yearHeadings.forEach((h) => {
      let anyVisible = false;
      let el = h.nextElementSibling;
      while (el && !el.classList.contains("year-heading")) {
        if (el.classList && el.classList.contains("albums-grid")) {
          const inGrid = Array.from(el.querySelectorAll(".show-card"))
            .some(card => !card.classList.contains("is-hidden"));
          if (inGrid) anyVisible = true;
        }
        el = el.nextElementSibling;
      }
      h.classList.toggle("is-hidden", !anyVisible);
      // also hide the grid if nothing visible inside
      const grid = h.nextElementSibling;
      if (grid && grid.classList.contains("albums-grid")) {
        const gridVisible = Array.from(grid.querySelectorAll(".show-card"))
          .some(card => !card.classList.contains("is-hidden"));
        grid.classList.toggle("is-hidden", !gridVisible);
      }
    });

    // Update chips active state
    if (yearChips) {
      const chips = Array.from(yearChips.querySelectorAll(".chip"));
      chips.forEach((chip) => {
        const y = chip.dataset.year || (chip.textContent.trim().toLowerCase() === "all" ? "all" : chip.textContent.trim());
        chip.classList.toggle("active", (y === state.year));
      });
    }
  };

  // --- Search input
  if (search) {
    let t = null;
    search.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => {
        state.q = search.value;
        apply();
      }, 80);
    });
  }

  // --- Pills
  pills.forEach((p) => {
    p.addEventListener("click", () => {
      pills.forEach(x => x.classList.remove("active"));
      p.classList.add("active");
      state.view = p.dataset.view;
      apply();
    });
  });

  // --- Year chips: convert links into client-side filters
  if (yearChips) {
    const chips = Array.from(yearChips.querySelectorAll(".chip"));
    chips.forEach((chip) => {
      // Add dataset year so CSS/JS can track active state
      const label = chip.textContent.trim();
      const yearVal = label.toLowerCase() === "all" ? "all" : label;
      chip.dataset.year = yearVal;

      chip.addEventListener("click", (e) => {
        // Keep normal nav if user is holding ctrl/cmd
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

        // Prevent full reload — client-side filter feels snappier
        e.preventDefault();
        state.year = yearVal === "Undated" ? "undated" : yearVal;
        apply();
        // Smooth scroll to first visible year header
        const firstVisible = yearHeadings.find(h => !h.classList.contains("is-hidden"));
        if (firstVisible) firstVisible.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  // --- Build "Top shots this week" rail (pure front-end)
  const buildTopShots = () => {
    if (!topShots || !topShotsRail) return;

    // Use album cards as data source (we don't have media items here)
    // We'll prioritize: (count desc) + (most recent date)
    const parsed = cards
      .map((c) => {
        // pull background image from inline style --bg:url('...')
        const style = c.getAttribute("style") || "";
        const m = style.match(/--bg:url\('([^']+)'\)/) || style.match(/--bg:url\("([^"]+)"\)/);
        const bg = m ? m[1] : "";

        const year = getYear(c);
        const date = c.dataset.date || "";
        const count = getCount(c);

        const title = `${(c.dataset.city || "").trim()}${c.dataset.state ? ", " + c.dataset.state : ""}`.trim() || (c.dataset.title || "Album");
        const hrefEl = c.querySelector("a.show-card__link");
        const href = hrefEl ? hrefEl.getAttribute("href") : "#";

        return { c, bg, year, date, count, title, href };
      })
      .filter(x => x.count > 0 && x.bg) // only meaningful cards
      .sort((a, b) => {
        // Prefer more media, then newer date string
        if (b.count !== a.count) return b.count - a.count;
        return (b.date || "").localeCompare(a.date || "");
      })
      .slice(0, 10);

    if (!parsed.length) {
      topShots.hidden = true;
      return;
    }

    topShots.hidden = false;
    topShotsRail.innerHTML = "";

    parsed.forEach((x) => {
      const el = document.createElement("a");
      el.className = "shot";
      el.href = x.href;
      el.innerHTML = `
        <div class="shot__img" style="background-image:url('${x.bg}')"></div>
        <div class="shot__cta">Open →</div>
        <div class="shot__meta">
          <div class="shot__title">${escapeHtml(x.title)}</div>
          <div class="shot__sub">${x.date ? x.date : (x.year ? x.year : "Undated")} • ${x.count} media</div>
        </div>
      `;
      topShotsRail.appendChild(el);
    });
  };

  const escapeHtml = (s) =>
    (s || "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[ch]));

  // Initial
  buildTopShots();
  apply();

  // Little wow: hover parallax-ish using mouse position (lightweight)
  cards.forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = `translateY(-4px) scale(1.012) rotateX(${(-y * 3).toFixed(2)}deg) rotateY(${(x * 4).toFixed(2)}deg)`;
    });
    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  });
})();
