document.addEventListener('DOMContentLoaded', () => {
  // Character counters
  document.querySelectorAll('[data-count]').forEach(el => {
    const max = parseInt(el.dataset.count, 10);
    const counter = el.parentElement.querySelector('.counter');
    const update = () => {
      const n = el.value.length;
      counter.textContent = `${n}/${max}`;
      counter.style.color = n > max ? 'var(--danger)' : '';
    };
    el.addEventListener('input', update);
    update();
  });

  // Venue search filter
  const vSearch = document.getElementById('venue-search');
  const vSelect = document.getElementById('venue-select');
  if (vSearch && vSelect) {
    vSearch.addEventListener('input', () => {
      const q = vSearch.value.toLowerCase();
      Array.from(vSelect.options).forEach(opt => {
        if (!opt.value) return;
        opt.hidden = !opt.text.toLowerCase().includes(q);
      });
    });
  }

  // Drag & drop previews
  function setupDrop(idInput, idDrop, idPrev, portrait=false){
    const input = document.getElementById(idInput);
    const drop = document.getElementById(idDrop);
    const prev = document.getElementById(idPrev);
    if (portrait) prev.classList.add('portrait');

    const handleFiles = files => {
      const file = files?.[0];
      if (!file || !file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = e => prev.innerHTML = `<img src="${e.target.result}" alt="preview">`;
      reader.readAsDataURL(file);
    };

    input?.addEventListener('change', () => handleFiles(input.files));
    ['dragenter','dragover'].forEach(ev => drop?.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('drag'); }));
    ['dragleave','drop'].forEach(ev => drop?.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('drag'); }));
    drop?.addEventListener('drop', e => {
      const files = e.dataTransfer.files;
      if (input){ input.files = files; input.dispatchEvent(new Event('change')); }
      handleFiles(files);
    });
  }
  setupDrop('id_cover_image','drop-cover','preview-cover',false);
  setupDrop('id_flyer','drop-flyer','preview-flyer',true);

  // Date helpers
  const startEl = document.querySelector('input[name="start"]');
  const endEl = document.querySelector('input[name="end"]');
  document.getElementById('copy-start')?.addEventListener('click', () => {
    if (startEl && endEl) endEl.value = startEl.value;
  });
  document.getElementById('add-3h')?.addEventListener('click', () => {
    if (!startEl?.value || !endEl) return;
    const d = new Date(startEl.value);
    d.setHours(d.getHours() + 3);
    const iso = new Date(d.getTime() - (d.getTimezoneOffset()*60000)).toISOString().slice(0,16);
    endEl.value = iso;
  });

  // Validation
  const form = document.getElementById('event-form');
  form?.addEventListener('submit', e => {
    const errs = [];
    const name = document.getElementById('id_name');
    if (!name.value.trim()) errs.push('Event name is required.');
    if (!startEl.value) errs.push('Start date/time is required.');
    if (endEl.value && startEl.value && (new Date(endEl.value) < new Date(startEl.value)))
      errs.push('End must be after start.');

    const box = document.getElementById('errors');
    box.innerHTML = '';
    if (errs.length) {
      e.preventDefault();
      box.innerHTML = `<ul>${errs.map(x=>`<li>${x}</li>`).join('')}</ul>`;
      box.scrollIntoView({behavior:'smooth'});
    }
  });

  // Show/hide tour extras
  const toggle = document.getElementById('toggle-tour');
  const extras = document.getElementById('tour-extras');
  const updateExtras = () => { extras.style.display = toggle.checked ? 'grid' : 'none'; };
  toggle?.addEventListener('change', updateExtras);
  updateExtras();
});
