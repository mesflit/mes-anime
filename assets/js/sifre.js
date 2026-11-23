// Video şifre anahtarı. Anahtar = SHA-256(VIDEO_SECRET_KEY)'in ilk 16 baytı.
// SECRET_KEY index.html'de tanımlı (deploy.yml yayınlarken doldurur). Türetmeyi değiştirme:
// mes-anime/araclar/video.py ve video depolarındaki resize.py aynı şeyi yapar.
/* global SECRET_KEY, Hls */
import { durum } from "./durum.js";

export async function initKey() {
  const gizli = typeof SECRET_KEY === "string" ? SECRET_KEY : "";
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(gizli));
  durum.aesKey = hash.slice(0, 16);
}

// hls.js özel yükleyici: oynatma listesindeki "enc.key" isteğini ağa çıkmadan bellekten verir
export const KeyInterceptLoader = window.Hls ? class extends Hls.DefaultConfig.loader {
  load(context, config, callbacks) {
    if (context.url && /enc\.key(\?|$)/.test(context.url)) {
      const now = performance.now();
      const stats = this.stats || {};
      Object.assign(stats, { loaded: 16, total: 16, trequest: now, tfirst: now, tload: now,
        loading: { start: now, first: now, end: now }, parsing: { start: now, end: now } });
      setTimeout(() => callbacks.onSuccess({ url: context.url, data: durum.aesKey.slice(0) }, stats, context, null), 0);
      return;
    }
    super.load(context, config, callbacks);
  }
} : null;
