/* ===== Videos: filter + swap to YouTube iframe (request best quality) ===== */
(() => {
  const list = document.getElementById('videosList');
  const filter = document.getElementById('videoFilter');
  if (!list) return;

  // --- Filter by title ---
  const applyFilter = () => {
    const q = (filter?.value || '').trim().toLowerCase();
    list.querySelectorAll('.video-card').forEach(card => {
      const inTitle = (card.dataset.title || '').includes(q);
      card.style.display = (!q || inTitle) ? '' : 'none';
    });
  };
  filter?.addEventListener('input', applyFilter);

  // --- Lazy load + Highest quality with YouTube IFrame API ---
  // Load API once (it’s lightweight and cached by the browser).
  let ytApiLoading = false;
  let ytApiReady = false;
  const ensureYTAPI = () => {
    if (ytApiReady || ytApiLoading) return;
    ytApiLoading = true;
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
    // YouTube looks for a global callback:
    window.onYouTubeIframeAPIReady = () => { ytApiReady = true; };
  };

  // Preference order YouTube supports (it may ignore and adapt):
  const QUALITIES = ["highres","hd2160","hd1440","hd1080","hd720","large","medium","small"];

  // Create a Player via API so we can request quality
  const createPlayer = (container, id, title) => {
    // Insert a div for API to replace
    const apiMount = document.createElement('div');
    apiMount.id = 'yt-' + id + '-' + Math.random().toString(36).slice(2);
    container.innerHTML = '';
    container.appendChild(apiMount);

    // Some browsers require explicit origin for nocookie + API combos.
    const origin = window.location.origin;

    /* global YT */
    const player = new YT.Player(apiMount.id, {
      videoId: id,
      playerVars: {
        autoplay: 1,
        rel: 0,
        modestbranding: 1,
        playsinline: 1,
        // enablejsapi is implicit when using YT.Player; origin helps on some setups
        origin
      },
      events: {
        onReady: (ev) => {
          // Ask nicely for the highest available quality
          for (const q of QUALITIES) {
            try { ev.target.setPlaybackQuality(q); } catch(e) {}
          }
          ev.target.playVideo(); // ensure playback starts
        },
        onPlaybackQualityChange: (ev) => {
          // If YouTube downgrades, we could try once to bump—but generally YT adapts automatically.
          // Uncomment if you want to be more aggressive:
          // try { ev.target.setPlaybackQuality(QUALITIES[0]); } catch(e) {}
        }
      }
    });
    return player;
  };

  // Fallback if API isn’t ready yet: regular iframe (privacy-enhanced)
  const createSimpleIframe = (container, id, title) => {
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
    iframe.title = title || 'YouTube video';
    iframe.frameBorder = '0';
    iframe.allow =
      'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    iframe.allowFullscreen = true;
    iframe.loading = 'lazy';
    container.innerHTML = '';
    container.appendChild(iframe);
  };

  list.addEventListener('click', (e) => {
    const btn = e.target.closest('.video-lazy');
    if (!btn) return;

    const wrap = btn.closest('.video-player');
    const id = wrap?.dataset?.yt;
    if (!id) return;

    const title = btn.getAttribute('aria-label') || 'YouTube video';

    // Make sure API script is on the page
    ensureYTAPI();

    // If API is ready now, great; otherwise use fallback, and next clicks will use API.
    if (ytApiReady && window.YT && window.YT.Player) {
      createPlayer(wrap, id, title);
    } else {
      createSimpleIframe(wrap, id, title);
    }
  });
})();
