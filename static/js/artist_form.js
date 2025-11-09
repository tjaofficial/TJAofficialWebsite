(function () {
  // --- Basic helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // --- Formset state
  const container = $('#video-rows');
  if (!container) return;

  const totalFormsInput = $('#id_videos-TOTAL_FORMS, #id_artistvideo_set-TOTAL_FORMS') ||
                          $('#id_artistvideo_set-TOTAL_FORMS');

  // Backward compatibility with default inline prefix name guesses
  let totalForms = null;
  let prefix = null;
  (function detectPrefix() {
    // common Django inline formset prefixes:
    //   <related_name>_set  OR  the explicit prefix we set in the view ("videos")
    const management = $$('input[name$="TOTAL_FORMS"]', document);
    for (const m of management) {
      if (m.name.endsWith('TOTAL_FORMS')) {
        const p = m.name.replace('-TOTAL_FORMS', '');
        // prefer explicit "videos"
        if (p === 'videos') {
          prefix = p;
          totalForms = m;
          break;
        }
        prefix = prefix || p;
        totalForms = totalForms || m;
      }
    }
  })();

  if (!prefix || !totalForms) return;

  // --- Delete buttons toggle the hidden DELETE checkbox
  function wireDeleteButtons(scope) {
    $$('.delete-row', scope || container).forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.currentTarget.closest('.video-row');
        const pref = e.currentTarget.dataset.target;
        const del = $(`input[name="${pref}-DELETE"]`, row);
        if (del) {
          // toggle delete
          const willDelete = del.checked ? false : true;
          del.checked = willDelete;
          row.classList.toggle('to-delete', willDelete);
          e.currentTarget.textContent = willDelete ? 'Undo Delete' : 'Delete';
        } else {
          // If this is a brand-new row (no DELETE field yet), just remove the element & renumber later
          row.remove();
          renumber();
        }
      });
    });
  }

  // =========================
  // Improved Embed Preview
  // =========================

  function parseYouTubeId(url) {
    if (!url) return null;
    // youtu.be short
    let m = url.match(/youtu\.be\/([A-Za-z0-9_-]{6,})/);
    if (m) return m[1];
    // watch?v=
    m = url.match(/[?&]v=([A-Za-z0-9_-]{6,})/);
    if (m) return m[1];
    // shorts/<id>
    m = url.match(/youtube\.com\/shorts\/([A-Za-z0-9_-]{6,})/);
    if (m) return m[1];
    return null;
  }

  function youtubeEmbedUrls(url) {
    const id = parseYouTubeId(url);
    if (!id) return null;
    const origin = encodeURIComponent(window.location.origin);
    const baseParams = `enablejsapi=1&origin=${origin}&playsinline=1&rel=0&modestbranding=1`;
    return {
      primary: `https://www.youtube-nocookie.com/embed/${id}?${baseParams}`,
      fallback: `https://www.youtube.com/embed/${id}?${baseParams}`,
      watch: `https://www.youtube.com/watch?v=${id}`
    };
  }

  function vimeoEmbedUrl(url) {
    const m = url && url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
    if (!m) return null;
    return `https://player.vimeo.com/video/${m[1]}`;
  }

  function renderPreview(previewEl, url) {
    // Try YouTube first
    const yt = youtubeEmbedUrls(url);
    if (yt) {
      previewEl.innerHTML = `
        <div class="embed-wrapper" data-mode="yt" data-primary="1">
          <iframe src="${yt.primary}" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen loading="lazy"></iframe>
          <div class="embed-actions">
            <button type="button" class="btn outline try-alt" data-alt="${yt.fallback}">Try alternate embed</button>
            <a class="btn" href="${yt.watch}" target="_blank" rel="noopener">Open on YouTube</a>
          </div>
        </div>
      `;
      wireAltButton(previewEl);
      return;
    }

    // Vimeo
    const v = vimeoEmbedUrl(url);
    if (v) {
      previewEl.innerHTML = `
        <div class="embed-wrapper" data-mode="vimeo">
          <iframe src="${v}" allow="autoplay; fullscreen; picture-in-picture"
                  allowfullscreen loading="lazy"></iframe>
        </div>
      `;
      return;
    }

    // Fallback empty
    previewEl.innerHTML = `<div class="preview-empty">Embed preview will appear here</div>`;
  }

  function wireAltButton(scope) {
    const btn = scope.querySelector('.try-alt');
    if (!btn) return;
    btn.addEventListener('click', (e) => {
      const alt = e.currentTarget.getAttribute('data-alt');
      const wrapper = e.currentTarget.closest('.embed-wrapper');
      if (!alt || !wrapper) return;
      const iframe = wrapper.querySelector('iframe');
      iframe.src = alt;
      // remove the alt button after swapping (prevents flip-flopping)
      e.currentTarget.remove();
    });
  }

  function wirePreview(scope) {
    $$('.video-row input[type="url"]', scope || container).forEach(inp => {
      // Initial render on page load (for existing values)
      {
        const row = inp.closest('.video-row');
        const preview = $('.preview', row);
        if (preview && inp.value) renderPreview(preview, inp.value.trim());
      }
      // Live updates
      inp.addEventListener('input', (e) => {
        const row = e.currentTarget.closest('.video-row');
        const preview = $('.preview', row);
        if (!preview) return;
        const url = e.currentTarget.value.trim();
        if (!url) {
          preview.innerHTML = `<div class="preview-empty">Embed preview will appear here</div>`;
          return;
        }
        renderPreview(preview, url);
      });
    });
  }

  // --- Add new row
  const addBtn = $('#add-video');
  const emptyTpl = $('#video-empty-form');

  function renumber() {
    const rows = $$('.video-row', container);
    rows.forEach((row, idx) => {
      row.dataset.index = idx;
      // fix any names/ids inside row
      $$('input, select, textarea', row).forEach(el => {
        if (el.name && el.name.includes('__prefix__')) {
          el.name = el.name.replace('__prefix__', `${prefix}-${idx}`);
        }
        if (el.id && el.id.includes('__prefix__')) {
          el.id = el.id.replace('__prefix__', `${prefix}-${idx}`);
        }
      });
    });
    // update management
    const total = rows.length;
    $$('input[name$="TOTAL_FORMS"]', document).forEach(m => {
      if (m.name.startsWith(prefix)) m.value = total;
    });
  }

  function addRow() {
    const idx = Number($(`input[name="${prefix}-TOTAL_FORMS"]`).value);
    let html = '';
    if (emptyTpl) {
      let title = `<input type="text" name="${prefix}-${idx}-title" id="id_${prefix}-${idx}-title">`;
      let url = `<input type="url" name="${prefix}-${idx}-url" id="id_${prefix}-${idx}-url" placeholder="https://">`;
      let sort = `<input type="number" name="${prefix}-${idx}-sort" id="id_${prefix}-${idx}-sort" value="${idx*10}">`;
      let del = `<input type="checkbox" name="${prefix}-${idx}-DELETE" id="id_${prefix}-${idx}-DELETE" style="display:none">`;

      html = emptyTpl.innerHTML
        .replaceAll('__index__', idx)
        .replace('__TITLE_INPUT__', title)
        .replace('__URL_INPUT__', url)
        .replace('__SORT_INPUT__', sort)
        .replace('__DELETE_INPUT__', del)
        .replaceAll('__PREFIX__', `${prefix}-${idx}`);
    }

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html.trim();
    const row = wrapper.firstElementChild;
    container.appendChild(row);

    // increment TOTAL_FORMS
    const total = $(`input[name="${prefix}-TOTAL_FORMS"]`);
    total.value = String(Number(total.value) + 1);

    wireDeleteButtons(row);
    wirePreview(row);
  }

  if (addBtn) addBtn.addEventListener('click', addRow);

  // Initial wiring
  wireDeleteButtons();
  wirePreview();
})();
