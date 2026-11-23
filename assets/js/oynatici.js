// Video oynatıcı: hls.js (şifreli HLS) + Plyr (arayüz), altyazılar, kalite menüsü, kaldığın yer
/* global Hls, Plyr */
import { LANG_LABELS, PLYR_IKONLAR } from "./ayarlar.js";
import { durum } from "./durum.js";
import { go } from "./gezinme.js";
import { getProg, pct, progKey, store } from "./kayit.js";
import { KeyInterceptLoader } from "./sifre.js";
import { $, esc } from "./yardimci.js";

const PLYR_TR = {
  restart: "Baştan başlat", rewind: "{seektime} sn geri", play: "Oynat", pause: "Duraklat",
  fastForward: "{seektime} sn ileri", seek: "Ara", played: "Oynatıldı", buffered: "Yüklendi",
  currentTime: "Geçen süre", duration: "Süre", volume: "Ses", mute: "Sessiz", unmute: "Sesi aç",
  enableCaptions: "Altyazıyı aç", disableCaptions: "Altyazıyı kapat", enterFullscreen: "Tam ekran",
  exitFullscreen: "Tam ekrandan çık", frameTitle: "Oynatıcı", captions: "Altyazı", settings: "Ayarlar",
  speed: "Hız", normal: "Normal", quality: "Kalite", loop: "Döngü", start: "Başlangıç", end: "Bitiş",
  all: "Tümü", reset: "Sıfırla", disabled: "Kapalı", enabled: "Açık", pip: "Resim içinde resim",
  qualityLabel: { 0: "Otomatik" }
};

/* ---------- kalite (480p kopyalar) ---------- */

export const heightOf = l => { const m = /x(\d+)$/.exec(l.resolution || "") || /(\d+)p$/.exec(l.name || ""); return m ? +m[1] : 0; };

// Orijinal + mes.anime'deki düşük kopyalar (resize.py üretir)
function qualityLevels(ep) {
  const all = [{ name: "orijinal", m3u8: ep.m3u8, bandwidth: ep.bandwidth, resolution: ep.resolution }, ...(ep.variants || [])];
  return all.map(l => ({ ...l, height: heightOf(l) }));
}

// Birden fazla kalite varsa tarayıcıda bir "master playlist" üretir; hls.js hıza göre seçer
function masterPlaylist(levels) {
  const txt = "#EXTM3U\n" + levels.map(l =>
    `#EXT-X-STREAM-INF:BANDWIDTH=${l.bandwidth || 5000000}${l.resolution ? ",RESOLUTION=" + l.resolution : ""}\n${l.m3u8}`
  ).join("\n") + "\n";
  const u = URL.createObjectURL(new Blob([txt], { type: "application/vnd.apple.mpegurl" }));
  durum.blobUrls.push(u);
  return u;
}

/* ---------- yardımcılar ---------- */

export function teardown() {
  if (durum.hls) { durum.hls.destroy(); durum.hls = null; }
  if (durum.player) { try { durum.player.destroy(); } catch {} durum.player = null; }
  $("playerBox").innerHTML = "";
  const old = durum.blobUrls; durum.blobUrls = [];
  setTimeout(() => old.forEach(u => URL.revokeObjectURL(u)), 1000);
}

function showMsg(text) {
  const m = document.createElement("div");
  m.className = "player-msg";
  m.textContent = text;
  $("playerBox").appendChild(m);
}

// raw.githubusercontent.com VTT'yi "text/plain + nosniff" ile sunar; bazı tarayıcılar
// bunu <track> olarak reddeder. Dosyayı çekip text/vtt Blob'u olarak veriyoruz.
async function subtitleUrl(src) {
  try {
    const r = await fetch(src, { cache: "no-cache" });
    if (!r.ok) throw 0;
    const u = URL.createObjectURL(new Blob([await r.text()], { type: "text/vtt" }));
    durum.blobUrls.push(u);
    return u;
  } catch { return null; }
}

/* ---------- bölümü yükle ---------- */

export async function loadVideo(anime, ep) {
  teardown();
  const token = {};
  loadVideo.token = token;
  const box = $("playerBox");

  if (ep.embed_url) {
    box.innerHTML = `<iframe src="${esc(ep.embed_url)}" title="${esc(ep.title)}" allowfullscreen allow="autoplay; fullscreen; picture-in-picture"></iframe>`;
    return;
  }

  const video = document.createElement("video");
  video.setAttribute("playsinline", "");
  video.setAttribute("controls", "");
  video.crossOrigin = "anonymous";
  box.appendChild(video);

  // Altyazı tercihi: kullanıcı seçimi > Türkçe > ilk altyazı
  const subs = ep.subtitles || [];
  const pref = store.get("subLang", "tr");
  const chosen = subs.find(s => s.lang === pref) || subs.find(s => s.lang === "tr") || subs[0];
  const urls = await Promise.all(subs.map(s => subtitleUrl(s.src)));
  if (loadVideo.token !== token) return;
  subs.forEach((s, i) => {
    if (!urls[i]) return;
    const track = document.createElement("track");
    track.kind = "captions";
    track.label = s.label || LANG_LABELS[s.lang] || s.lang;
    track.srclang = s.lang;
    track.src = urls[i];
    video.appendChild(track);
  });

  // Kalite seçenekleri (sadece 480p kopyası olan bölümlerde)
  const levels = qualityLevels(ep);
  const qOptions = levels.length > 1 ? [0, ...new Set(levels.map(l => l.height).filter(Boolean))] : [];
  const qPref = qOptions.includes(store.get("quality", 0)) ? store.get("quality", 0) : 0;
  const setQuality = q => {
    store.set("quality", q);
    const hls = durum.hls;
    if (!hls || !hls.levels || !hls.levels.length) return;
    const i = q ? hls.levels.findIndex(l => l.height === q) : -1;
    if (hls.currentLevel !== i || (i === -1 && !hls.autoLevelEnabled)) hls.currentLevel = i;
  };

  if (window.Hls && Hls.isSupported()) {
    const hls = durum.hls = new Hls({ loader: KeyInterceptLoader, maxBufferLength: 30 });
    hls.on(Hls.Events.MANIFEST_PARSED, () => { if (qPref) setQuality(qPref); });
    let mediaRetry = 0;
    hls.on(Hls.Events.ERROR, (_, data) => {
      if (!data.fatal) return;
      if (data.type === Hls.ErrorTypes.NETWORK_ERROR) { setTimeout(() => durum.hls && durum.hls.startLoad(), 1500); }
      else if (data.type === Hls.ErrorTypes.MEDIA_ERROR && mediaRetry++ < 3) { hls.recoverMediaError(); }
      else { showMsg("Video oynatılamadı. Lütfen sayfayı yenileyin."); }
    });
    hls.loadSource(levels.length > 1 ? masterPlaylist(levels) : ep.m3u8);
    hls.attachMedia(video);
  } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = ep.m3u8;
  } else {
    showMsg("Tarayıcınız bu videoyu desteklemiyor.");
  }

  const player = durum.player = new Plyr(video, {
    iconUrl: PLYR_IKONLAR,
    blankVideo: "",
    captions: { active: !!chosen && pref !== "off", update: true, language: chosen ? chosen.lang : "auto" },
    controls: ["play-large", "rewind", "play", "fast-forward", "progress", "current-time", "duration", "mute", "volume", "captions", "settings", "pip", "fullscreen"],
    settings: ["captions", "quality", "speed"],
    // Kalite menüsü sadece kopyası olan bölümlerde. Yoksa "quality" HİÇ verilmemeli:
    // undefined verilirse Plyr'ın varsayılan ayarı silinir ve oynatıcı çöker.
    ...(qOptions.length && durum.hls ? { quality: { default: qPref, options: qOptions, forced: true, onChange: setQuality } } : {}),
    seekTime: 10,
    keyboard: { focused: true, global: true },
    i18n: PLYR_TR
  });

  // Plyr kalite menüsünde kayıtlı seçimi işaretle (kendisi yapmıyor)
  if (qOptions.length && durum.hls) player.once("ready", () => { player.quality = qPref; });

  // Kaldığın yerden devam
  const saved = getProg(anime, ep);
  player.once("loadedmetadata", () => {
    if (saved && saved.t > 10 && pct(saved) < 95) player.currentTime = saved.t;
  });
  let lastSave = 0;
  player.on("timeupdate", () => {
    const t = player.currentTime, d = player.duration;
    if (!d || Math.abs(t - lastSave) < 5) return;
    lastSave = t;
    store.set(progKey(anime, ep), { t, d, at: Date.now() });
  });

  // Aynı anda yalnızca seçili altyazı açık olsun. Telefonların yerel tam ekranında
  // (iOS) tarayıcı altyazıyı kendisi çizer; orada "showing", Plyr'da "hidden" gerekir.
  const nativeFs = () => !!(document.webkitFullscreenElement === video || video.webkitDisplayingFullscreen);
  const syncTracks = () => {
    const on = player.currentTrack >= 0 && player.captions && player.captions.active !== false && store.get("subLang", "tr") !== "off";
    const lang = player.language;
    [...video.textTracks].forEach(t => {
      const want = on && t.language === lang ? (nativeFs() ? "showing" : "hidden") : "disabled";
      if (t.mode !== want) t.mode = want;
    });
  };
  ["languagechange", "captionsenabled", "captionsdisabled", "enterfullscreen", "exitfullscreen", "ready"].forEach(e => player.on(e, () => setTimeout(syncTracks, 0)));
  video.addEventListener("webkitbeginfullscreen", () => setTimeout(syncTracks, 0));
  video.addEventListener("webkitendfullscreen", () => setTimeout(syncTracks, 0));
  video.textTracks.addEventListener("change", () => setTimeout(syncTracks, 0));
  player.on("languagechange", () => store.set("subLang", player.language || "tr"));
  player.on("captionsdisabled", () => store.set("subLang", "off"));
  player.on("captionsenabled", () => { if (store.get("subLang", "tr") === "off") store.set("subLang", player.language || "tr"); });

  // Bitince: izlendi say, istenirse sonraki bölüme geç
  player.on("ended", () => {
    const d = player.duration;
    store.set(progKey(anime, ep), { t: d, d, at: Date.now() });
    const c = durum.current;
    if ($("autoNext").checked && c && c.index < anime.episodes.length - 1) go(anime, c.index + 1);
  });
}
