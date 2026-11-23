// İndirme: şifreli parçaları indirip tarayıcıda çözer ve tek dosya yapar.
// mux.js ile MP4'e çevirir (her telefonda açılır); olmazsa .ts verir (VLC açar).
// Altyazılar ayrıca .srt olarak iner. Aynı anda tek bölüm iner.
/* global muxjs */
import { LANG_LABELS, MUX_JS, PARALEL_INDIRME } from "./ayarlar.js";
import { durum } from "./durum.js";
import { heightOf } from "./oynatici.js";
import { $, esc, fileName, loadScript, saveBlob, sleep } from "./yardimci.js";

// HLS oynatma listesini parçalara ayırır: [{ url, iv }] (iv null = şifresiz)
export function parsePlaylist(text, base) {
  const segs = []; let key = null, seq = 0;
  for (const raw of text.split(/\r?\n/)) {
    const l = raw.trim();
    if (!l) continue;
    if (l.startsWith("#EXT-X-MEDIA-SEQUENCE:")) seq = parseInt(l.slice(22)) || 0;
    else if (l.startsWith("#EXT-X-KEY:")) {
      const m = /METHOD=([^,]+)/.exec(l), iv = /IV=0x([0-9a-f]+)/i.exec(l);
      key = m && m[1] !== "NONE" ? { iv: iv ? iv[1].padStart(32, "0") : null } : null;
    } else if (!l.startsWith("#")) {
      let iv = null;
      if (key) {
        iv = new Uint8Array(16);
        if (key.iv) key.iv.match(/../g).forEach((h, i) => iv[i] = parseInt(h, 16));
        else new DataView(iv.buffer).setUint32(12, seq);   // IV yoksa sıra numarası
      }
      segs.push({ url: new URL(l, base).href, iv }); seq++;
    }
  }
  return segs;
}

export async function downloadEpisode(anime, ep, src = ep.m3u8, suffix = "") {
  if (durum.dl) return;
  const ctrl = new AbortController(), signal = ctrl.signal;
  const dl = durum.dl = { key: anime.id + "/" + ep.id, title: ep.title, pct: 0, ctrl, text: "Hazırlanıyor..." };
  renderDl();
  const name = fileName(`${anime.title} - ${ep.title}${suffix}`);
  try {
    const segs = parsePlaylist(await (await fetch(src, { signal })).text(), src);
    if (!segs.length) throw new Error("Bölüm listesi boş");
    const aes = await crypto.subtle.importKey("raw", durum.aesKey, "AES-CBC", false, ["decrypt"]);
    const get = async s => {
      for (let i = 0; ; i++) {
        try {
          const r = await fetch(s.url, { signal });
          if (!r.ok) throw new Error("HTTP " + r.status);
          let b = await r.arrayBuffer();
          if (s.iv) b = await crypto.subtle.decrypt({ name: "AES-CBC", iv: s.iv }, aes, b);
          return new Uint8Array(b);
        } catch (e) { if (signal.aborted || i >= 3) throw e; await sleep(1500 * (i + 1)); }
      }
    };

    let mux = null;
    const mp4 = [], ts = [];
    try {
      await loadScript(MUX_JS, () => window.muxjs);
      mux = new muxjs.mp4.Transmuxer({ remux: true });
      mux.on("data", d => { if (!mp4.length) mp4.push(new Blob([d.initSegment])); mp4.push(new Blob([d.data])); });
    } catch { mux = null; }

    let done = 0;
    for (let i = 0; i < segs.length; i += PARALEL_INDIRME) {
      const batch = await Promise.all(segs.slice(i, i + PARALEL_INDIRME).map(get));
      for (const b of batch) {
        if (mux) {
          mux.push(b); mux.flush();
          if (done === 0 && !mp4.length) mux = null;   // MP4'e çevrilemedi -> .ts
        }
        if (!mux) ts.push(new Blob([b]));
        done++;
      }
      dl.pct = Math.round(done / segs.length * 100);
      dl.text = `İndiriliyor %${dl.pct}`;
      renderDl();
    }
    if (mux && mp4.length) saveBlob(new Blob(mp4, { type: "video/mp4" }), name + ".mp4");
    else saveBlob(new Blob(ts, { type: "video/mp2t" }), name + ".ts");
    durum.dl = null; renderDl();
  } catch (e) {
    const cancelled = signal.aborted;
    durum.dl = null; renderDl();
    if (!cancelled) alert("İndirme başarısız: " + (e.message || e));
  }
}

export function vttToSrt(vtt) {
  const fix = t => { t = t.replace(".", ","); return t.split(":").length === 2 ? "00:" + t : t; };
  let n = 0;
  return vtt.replace(/\r/g, "").split(/\n\s*\n/).map(b => {
    const lines = b.split("\n");
    const i = lines.findIndex(l => l.includes("-->"));
    const m = i < 0 ? null : /([\d:.]+)\s+-->\s+([\d:.]+)/.exec(lines[i]);
    return m ? `${++n}\n${fix(m[1])} --> ${fix(m[2])}\n${lines.slice(i + 1).join("\n")}` : null;
  }).filter(Boolean).join("\n\n") + "\n";
}

async function downloadSub(anime, ep, s) {
  try {
    const r = await fetch(s.src, { cache: "no-cache" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    saveBlob(new Blob([vttToSrt(await r.text())], { type: "application/x-subrip" }),
             fileName(`${anime.title} - ${ep.title}.${s.lang}`) + ".srt");
  } catch (e) { alert("Altyazı indirilemedi: " + (e.message || e)); }
}

// Açık bölümün indirme düğmesini çizer: tek "⬇ İndir" düğmesi, tıklayınca menü açılır.
// İndirme sürerken düğmede yüzde ve alt çizgide ilerleme görünür, menüde "İptal" çıkar.
let menuAcik = false;

export function renderDl() {
  const kutu = $("dlBar");
  const c = durum.current, dl = durum.dl;
  if (!kutu || !c) return;
  const { anime } = c, ep = anime.episodes[c.index];
  const buBolum = dl && dl.key === anime.id + "/" + ep.id;

  kutu.innerHTML = "";
  const dugme = document.createElement("button");
  dugme.className = "btn dl-btn";
  dugme.setAttribute("aria-haspopup", "true");
  dugme.setAttribute("aria-expanded", String(menuAcik));
  dugme.textContent = dl ? `⬇ %${dl.pct}` : "⬇ İndir ▾";
  if (dl) dugme.title = `${dl.title} indiriliyor`;
  dugme.insertAdjacentHTML("beforeend", dl ? `<span class="dl-prog" style="width:${dl.pct}%"></span>` : "");
  dugme.onclick = e => {
    e.stopPropagation(); menuAcik = !menuAcik; renderDl();
    if (menuAcik) $("dlBar").querySelector(".dl-menu button:not(:disabled)")?.focus();
  };
  kutu.appendChild(dugme);
  if (!menuAcik) return;

  const menu = document.createElement("div");
  menu.className = "dl-menu";
  menu.setAttribute("role", "menu");
  const satir = (yazi, ek, fn, kapali) => {
    const b = document.createElement("button");
    b.setAttribute("role", "menuitem");
    b.innerHTML = `<span>${esc(yazi)}</span>${ek ? `<small>${esc(ek)}</small>` : ""}`;
    b.disabled = !!kapali;
    b.onclick = e => { e.stopPropagation(); menuAcik = false; fn(); renderDl(); };
    menu.appendChild(b);
  };

  if (dl) {
    menu.insertAdjacentHTML("beforeend", `<div class="dl-note" aria-live="polite">${esc(buBolum ? dl.text : `Başka bölüm iniyor: ${dl.title} (%${dl.pct})`)}</div>`);
    satir("✕ İndirmeyi iptal et", "", () => durum.dl && durum.dl.ctrl.abort());
    menu.appendChild(document.createElement("hr"));
  }
  const h = heightOf(ep);
  satir("Bölüm", h ? `${h}p · MP4` : "MP4", () => downloadEpisode(anime, ep), dl);
  (ep.variants || []).forEach(v => satir("Bölüm (küçük dosya)", `${v.name} · MP4`, () => downloadEpisode(anime, ep, v.m3u8, ` (${v.name})`), dl));
  if ((ep.subtitles || []).length) menu.appendChild(document.createElement("hr"));
  (ep.subtitles || []).forEach(s => satir(`${s.label || LANG_LABELS[s.lang] || s.lang} altyazı`, "SRT", () => downloadSub(anime, ep, s)));
  kutu.appendChild(menu);
}

// Menü dışına tıklayınca veya Esc'ye basınca kapat
document.addEventListener("click", e => { if (menuAcik && !e.target.closest("#dlBar")) { menuAcik = false; renderDl(); } });
document.addEventListener("keydown", e => { if (menuAcik && e.key === "Escape") { menuAcik = false; renderDl(); $("dlBar")?.querySelector("button")?.focus(); } });
// Bölüm değişince menü kapalı başlasın
window.addEventListener("hashchange", () => { menuAcik = false; });
