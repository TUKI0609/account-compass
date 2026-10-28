/* 카드 그림 저장·복사·X 공유.
   그림은 이 브라우저에서만 만든다. X로 여는 주소에는 보이는 문구만 넣고, CSV는 넣지 않는다. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  XA.SITE_ORIGIN = 'https://tuki0609.github.io/account-compass/';

  XA.siteUrl = function (query) {
    const u = new URL(XA.SITE_ORIGIN);
    const q = query || {};
    Object.keys(q).forEach((k) => {
      if (q[k] != null && q[k] !== '') u.searchParams.set(k, String(q[k]));
    });
    return u.toString();
  };

  XA.xIntentUrl = function (text) {
    return 'https://x.com/intent/post?text=' + encodeURIComponent(String(text || ''));
  };

  function canvasBlob(canvas) {
    return new Promise((resolve) => {
      if (!canvas || !canvas.toBlob) { resolve(null); return; }
      canvas.toBlob((b) => resolve(b), 'image/png');
    });
  }

  XA.downloadCanvas = function (canvas, filename) {
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = filename || 'card.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  XA.copyCanvas = function (canvas, filename) {
    return canvasBlob(canvas).then((blob) => {
      const clip = navigator.clipboard;
      if (blob && clip && typeof clip.write === 'function' && typeof ClipboardItem === 'function') {
        try {
          return clip.write([new ClipboardItem({ 'image/png': blob })]).then(
            () => ({ ok: true, how: 'clipboard' }),
            () => { XA.downloadCanvas(canvas, filename); return { ok: true, how: 'download' }; }
          );
        } catch (e) {
          XA.downloadCanvas(canvas, filename);
          return { ok: true, how: 'download' };
        }
      }
      XA.downloadCanvas(canvas, filename);
      return { ok: true, how: 'download' };
    });
  };

  XA.shareToX = function (canvas, caption, filename) {
    const url = XA.xIntentUrl(caption);
    return canvasBlob(canvas).then((blob) => {
      const file = blob ? new File([blob], filename || 'card.png', { type: 'image/png' }) : null;
      let can = false;
      try { can = !!(file && navigator.canShare && navigator.canShare({ files: [file] }) && typeof navigator.share === 'function'); } catch (e) { can = false; }
      if (can) {
        return navigator.share({ files: [file], text: caption }).then(
          () => ({ how: 'share', url: url }),
          (err) => {
            if (err && err.name === 'AbortError') return { how: 'abort', url: url };
            XA.downloadCanvas(canvas, filename);
            try { window.open(url, '_blank', 'noopener'); } catch (e2) { }
            return { how: 'intent', url: url };
          }
        );
      }
      XA.downloadCanvas(canvas, filename);
      try { window.open(url, '_blank', 'noopener'); } catch (e3) { }
      return { how: 'intent', url: url };
    });
  };
})();
