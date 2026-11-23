// Anime listesi: data/depolar.txt -> her deponun mes.anime dosyası -> sitenin iç biçimi
import { DEPOLAR, LANG_LABELS } from "./ayarlar.js";

export const seasonOf = ep => { const m = /^s(\d+)-/i.exec(ep.id || ""); return m ? +m[1] : 1; };
export const hasTr = a => a.episodes.some(e => (e.subtitles || []).some(s => s.lang === "tr"));
const temizYol = p => p.replace(/^\/+|\/+$/g, "");

// "mesflit/opm" veya "mesflit/opm@dal" -> { id, title, category, poster, episodes: [...] }
export async function loadRepo(line) {
  const [repo, branch = "main"] = line.split("@");
  const base = `https://raw.githubusercontent.com/${repo}/${branch}`;
  const res = await fetch(`${base}/mes.anime?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${repo}: mes.anime bulunamadı (${res.status})`);
  const m = await res.json();
  const url = p => !p ? "" : /^https?:\/\//.test(p) ? p : `${base}/${p.replace(/^\/+/, "")}`;
  return {
    id: m.id || repo.split("/").pop(),
    title: m.title || repo,
    category: m.category || "Anime",
    poster: url(m.poster),
    episodes: (m.episodes || []).filter(e => e && e.path).map(e => {
      const dir = `${base}/${temizYol(e.path)}`;
      return {
        id: e.id || temizYol(e.path).replace(/\//g, "-"),
        title: e.title || e.path,
        m3u8: `${dir}/index.m3u8`,
        bandwidth: e.bandwidth, resolution: e.resolution,
        variants: (e.variants || []).filter(v => v && v.path).map(v => ({
          name: v.name, bandwidth: v.bandwidth, resolution: v.resolution,
          m3u8: `${dir}/${temizYol(v.path)}/index.m3u8`
        })),
        subtitles: (e.subtitles || []).map(s => typeof s === "string"
          ? { lang: s, label: LANG_LABELS[s] || s.toUpperCase(), src: `${dir}/${s}.vtt` }
          : { ...s, src: url(s.src) })
      };
    })
  };
}

// Döndürür: { animeler, hata }. Bir depo okunamazsa atlanır; hiçbiri okunamazsa hata dolu gelir.
export async function loadAnimes() {
  let lines;
  try {
    const res = await fetch(`${DEPOLAR}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    lines = (await res.text()).split(/\r?\n/).map(l => l.replace(/#.*/, "").trim()).filter(Boolean);
  } catch {
    return { animeler: [], hata: "Anime listesi yüklenemedi. İnternet bağlantını kontrol edip tekrar dene." };
  }
  const results = await Promise.allSettled(lines.map(loadRepo));
  results.forEach(r => r.status === "rejected" && console.warn(r.reason));
  const animeler = results.filter(r => r.status === "fulfilled").map(r => r.value);
  const hata = lines.length && !animeler.length ? "Animeler yüklenemedi. İnternet bağlantını kontrol edip tekrar dene." : "";
  return { animeler, hata };
}
