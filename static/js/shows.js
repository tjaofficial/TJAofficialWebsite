// /* ===== Shows: filter, month index, active month, ICS export ===== */
// (() => {
//   const list = document.getElementById('showsList');
//   if (!list) return;

//   const filterInput = document.getElementById('showFilter');
//   const togglePast = document.getElementById('togglePast');
//   const cards = Array.from(list.querySelectorAll('.show-card'));
//   const groups = Array.from(list.querySelectorAll('.month-group'));
//   const headings = Array.from(list.querySelectorAll('.month-heading'));
//   const monthIndex = document.getElementById('monthIndex');

//   // Build month index from headings
//   const entries = headings.map(h => {
//     const id = 'm-' + (h.textContent || '').toLowerCase().replace(/\s+/g, '-');
//     h.id = id;
//     return { id, text: h.textContent };
//   });
//   if (monthIndex && entries.length) {
//     monthIndex.innerHTML = entries.map(e => `<a href="#${e.id}">${e.text}</a>`).join('');
//   }

//   // Active month highlighting
//   if ('IntersectionObserver' in window && monthIndex) {
//     const links = Array.from(monthIndex.querySelectorAll('a'));
//     const map = Object.fromEntries(links.map(a => [a.getAttribute('href').slice(1), a]));
//     const io = new IntersectionObserver((obs) => {
//       obs.forEach(entry => {
//         if (entry.isIntersecting) {
//           links.forEach(l => l.classList.remove('is-active'));
//           const a = map[entry.target.id];
//           if (a) a.classList.add('is-active');
//         }
//       });
//     }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });
//     headings.forEach(h => io.observe(h));
//   }

//   // Filter logic
//   const applyFilter = () => {
//     const q = (filterInput?.value || '').trim().toLowerCase();
//     const now = new Date(); now.setHours(0,0,0,0);

//     cards.forEach(card => {
//       const city = card.dataset.city || '';
//       const state = card.dataset.state || '';
//       const venue = card.dataset.venue || '';
//       const dt = card.dataset.date ? new Date(card.dataset.date) : null;
//       const isPast = dt ? dt < now : false;

//       if (!togglePast?.checked && isPast) {
//         card.style.display = 'none';
//         return;
//       }

//       const textMatch = [city, state, venue].some(v => v.includes(q));
//       card.style.display = textMatch ? '' : 'none';
//     });

//     // Hide month groups with no visible cards
//     groups.forEach(g => {
//       const visible = Array.from(g.querySelectorAll('.show-card')).some(c => c.style.display !== 'none');
//       g.style.display = visible ? '' : 'none';
//     });
//   };

//   filterInput?.addEventListener('input', applyFilter);
//   togglePast?.addEventListener('change', applyFilter);
//   applyFilter();

//   // Add-to-Calendar (.ics) generator
//   const pad = n => String(n).padStart(2, '0');
//   const makeICS = (title, startISO, location, desc = 'Live show') => {
//     // Default to 2 hours duration
//     const start = new Date(startISO);
//     const end = new Date(start.getTime() + 2 * 60 * 60 * 1000);

//     const fmt = (d) =>
//       d.getUTCFullYear() +
//       pad(d.getUTCMonth() + 1) +
//       pad(d.getUTCDate()) + 'T' +
//       pad(d.getUTCHours()) +
//       pad(d.getUTCMinutes()) +
//       pad(d.getUTCSeconds()) + 'Z';

//     const body = [
//       'BEGIN:VCALENDAR',
//       'VERSION:2.0',
//       'PRODID:-//TJAofficial//Shows//EN',
//       'CALSCALE:GREGORIAN',
//       'METHOD:PUBLISH',
//       'BEGIN:VEVENT',
//       'UID:' + crypto.randomUUID(),
//       'DTSTAMP:' + fmt(new Date()),
//       'DTSTART:' + fmt(start),
//       'DTEND:' + fmt(end),
//       'SUMMARY:' + (title || 'TJA Live'),
//       'LOCATION:' + (location || ''),
//       'DESCRIPTION:' + desc,
//       'END:VEVENT',
//       'END:VCALENDAR'
//     ].join('\r\n');

//     return new Blob([body], { type: 'text/calendar;charset=utf-8' });
//   };

//   list.addEventListener('click', (e) => {
//     const btn = e.target.closest('.addCal');
//     if (!btn) return;
//     const card = e.target.closest('.show-card');
//     if (!card) return;

//     const title = card.dataset.title || 'TJA — Live';
//     const start = card.dataset.datetime || card.dataset.date;
//     const location = card.dataset.location || '';
//     const blob = makeICS(title, start, location);
//     const url = URL.createObjectURL(blob);
//     const a = document.createElement('a');
//     a.href = url; a.download = (title.replace(/\s+/g, '_').toLowerCase()) + '.ics';
//     document.body.appendChild(a);
//     a.click();
//     a.remove();
//     setTimeout(() => URL.revokeObjectURL(url), 500);
//   });
// })();

/* ===== Shows hero countdown ===== */
(() => {
	const wrap = document.querySelector('.next-show .countdown');
	if (!wrap) return;
	const targetISO = wrap.dataset.dt;
	if (!targetISO) return;
	const dd = wrap.querySelector('[data-dd]');
	const hh = wrap.querySelector('[data-hh]');
	const mm = wrap.querySelector('[data-mm]');
	const ss = wrap.querySelector('[data-ss]');
	const tick = () => {
		const t = new Date(targetISO).getTime() - Date.now();
		if (t <= 0) { dd.textContent=hh.textContent=mm.textContent=ss.textContent='00'; return; }
		const d = Math.floor(t / (1000*60*60*24));
		const h = Math.floor((t / (1000*60*60)) % 24);
		const m = Math.floor((t / (1000*60)) % 60);
		const s = Math.floor((t / 1000) % 60);
		const pad = (n) => String(n).padStart(2,'0');
		dd.textContent = pad(d); hh.textContent = pad(h); mm.textContent = pad(m); ss.textContent = pad(s);
	};
	tick(); setInterval(tick, 1000);
})();
