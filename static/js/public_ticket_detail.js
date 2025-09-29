(() => {
  const $ = (sel, p = document) => p.querySelector(sel);

  // Elements
  const wrap = $('.ticket-card');
  const btnICS = $('#btnAddICS');
  const btnGCal = $('#btnGCal');
  const btnCopy = $('#btnCopy');
  const btnShare = $('#btnShare');
  const btnSaveQR = $('#btnSaveQR');
  const btnZoomQR = $('#btnZoomQR');
  const qrImage = $('#qrImage');

  // Extract event data from data-attrs
  const evName = wrap?.dataset.evName || 'Event';
  const evStartISO = wrap?.dataset.evStart || null;
  const evEndISO = wrap?.dataset.evEnd || null;
  const evVenue = wrap?.dataset.evVenue || '';
  const evLocation = wrap?.dataset.evLocation || '';
  const shareUrl = (document.querySelector('link[rel=canonical]')?.href) || window.location.href;

  function formatICSDate(d) {
    // YYYYMMDDTHHMMSSZ (use UTC)
    const pad = (n) => String(n).padStart(2, '0');
    const y = d.getUTCFullYear();
    const m = pad(d.getUTCMonth() + 1);
    const day = pad(d.getUTCDate());
    const h = pad(d.getUTCHours());
    const min = pad(d.getUTCMinutes());
    const s = pad(d.getUTCSeconds());
    return `${y}${m}${day}T${h}${min}${s}Z`;
  }

  function buildICS() {
    if (!evStartISO) return null;
    const dtStart = new Date(evStartISO);
    const dtEnd = evEndISO ? new Date(evEndISO) : new Date(dtStart.getTime() + 2 * 60 * 60 * 1000); // default 2h
    const uid = crypto.randomUUID ? crypto.randomUUID() : (Date.now() + '@tjaofficial.com');

    const ics = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//TJA Official//Ticket//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      `UID:${uid}`,
      `SUMMARY:${evName.replace(/\n/g,' ')}`,
      `DTSTART:${formatICSDate(dtStart)}`,
      `DTEND:${formatICSDate(dtEnd)}`,
      `LOCATION:${(evVenue || evLocation).replace(/\n/g,' ')}`,
      `DESCRIPTION:${('Your ticket for ' + evName + '\\n' + shareUrl).replace(/\n/g,'\\n')}`,
      'END:VEVENT',
      'END:VCALENDAR'
    ].join('\r\n');

    return ics;
  }

  function downloadICS() {
    const ics = buildICS();
    if (!ics) return;
    const blob = new Blob([ics], {type: 'text/calendar'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${evName.replace(/\s+/g,'_')}.ics`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
  }

  function buildGoogleCalUrl() {
    if (!evStartISO) return '#';
    const s = new Date(evStartISO);
    const e = evEndISO ? new Date(evEndISO) : new Date(s.getTime() + 2 * 60 * 60 * 1000);
    const fmt = (d) => {
      // YYYYMMDDTHHMMSSZ
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getUTCFullYear()}${pad(d.getUTCMonth()+1)}${pad(d.getUTCDate())}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`;
    };
    const dates = `${fmt(s)}/${fmt(e)}`;
    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: evName,
      dates,
      details: `Your ticket for ${evName}\n${shareUrl}`,
      location: evVenue || evLocation,
    });
    return `https://www.google.com/calendar/render?${params.toString()}`;
  }

  function copyLink() {
    navigator.clipboard.writeText(shareUrl).then(() => {
      toast('Link copied');
    }).catch(() => {
      prompt('Copy link:', shareUrl);
    });
  }

  function shareLink() {
    if (navigator.share) {
      navigator.share({title: evName, text: 'My ticket', url: shareUrl}).catch(()=>{});
    } else {
      copyLink();
    }
  }

  function toast(msg) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    Object.assign(el.style, {
      position: 'fixed', left: '50%', bottom: '20px',
      transform: 'translateX(-50%)', background: '#222', color: '#eee',
      padding: '8px 12px', borderRadius: '10px', border: '1px solid #333',
      zIndex: '99', opacity: '0', transition: 'opacity .2s ease',
    });
    document.body.appendChild(el);
    requestAnimationFrame(()=>{ el.style.opacity = '1'; });
    setTimeout(()=>{ el.style.opacity = '0'; setTimeout(()=>el.remove(), 200); }, 1400);
  }

  function saveQR() {
    if (!qrImage) return;
    // If already a PNG, just download the src
    const a = document.createElement('a');
    a.href = qrImage.src; 
    a.download = 'ticket-qr.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // Modal
  const modal = $('#qrModal');
  function openModal() { if (modal) modal.hidden = false; }
  function closeModal() { if (modal) modal.hidden = true; }

  // Wire up
  if (btnICS) btnICS.addEventListener('click', downloadICS);
  if (btnGCal) btnGCal.href = buildGoogleCalUrl();
  if (btnCopy) btnCopy.addEventListener('click', copyLink);
  if (btnShare) btnShare.addEventListener('click', shareLink);
  if (btnSaveQR) btnSaveQR.addEventListener('click', saveQR);
  if (btnZoomQR) btnZoomQR.addEventListener('click', openModal);
  modal?.addEventListener('click', (e) => {
    if (e.target.hasAttribute('data-close') || e.target.classList.contains('modal')) closeModal();
  });
})();
