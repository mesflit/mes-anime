// İzleme sayfası: başlık, önceki/sonraki, sezon sekmeleri, bölüm listesi
import { LANG_LABELS, SITE_ADI } from "./ayarlar.js";
import { durum } from "./durum.js";
import { go } from "./gezinme.js";
import { getProg, pct, store } from "./kayit.js";
import { renderDl } from "./indirme.js";
import { loadVideo } from "./oynatici.js";
import { seasonOf } from "./veri.js";
import { $, esc } from "./yardimci.js";

export function openEpisode(anime, epIndex) {
  $("homeView").classList.add("hidden");
  $("watchView").classList.remove("hidden");
  durum.current = { anime, index: epIndex };
  const ep = anime.episodes[epIndex];
  store.set("last:" + anime.id, ep.id);
  document.title = `${anime.title} — ${ep.title} | ${SITE_ADI}`;
  $("watchTitle").textContent = `${anime.title} — ${ep.title}`;
  const langs = (ep.subtitles || []).map(s => s.label || LANG_LABELS[s.lang] || s.lang);
  $("watchSub").textContent = [anime.category, langs.length ? "Altyazı: " + langs.join(", ") : "Altyazı yok"].filter(Boolean).join(" · ");

  $("prevBtn").disabled = epIndex <= 0;
  $("nextBtn").disabled = epIndex >= anime.episodes.length - 1;
  $("prevBtn").onclick = () => epIndex > 0 && go(anime, epIndex - 1);
  $("nextBtn").onclick = () => epIndex < anime.episodes.length - 1 && go(anime, epIndex + 1);

  renderEpisodes(anime, epIndex, seasonOf(ep));
  renderDl();
  loadVideo(anime, ep);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderEpisodes(anime, epIndex, season) {
  const seasons = [...new Set(anime.episodes.map(seasonOf))].sort((a, b) => a - b);
  const tabs = $("seasonTabs");
  tabs.innerHTML = "";
  tabs.classList.toggle("hidden", seasons.length < 2);
  seasons.forEach(s => {
    const t = document.createElement("button");
    t.className = "tab" + (s === season ? " active" : "");
    t.textContent = `${s}. Sezon`;
    t.setAttribute("aria-pressed", s === season);
    t.onclick = () => renderEpisodes(anime, epIndex, s);
    tabs.appendChild(t);
  });
  const list = $("epList");
  list.innerHTML = "";
  anime.episodes.forEach((e, i) => {
    if (seasonOf(e) !== season) return;
    const p = getProg(anime, e);
    const b = document.createElement("button");
    b.className = "ep-item" + (i === epIndex ? " active" : "") + (pct(p) >= 90 ? " done" : "");
    if (i === epIndex) b.setAttribute("aria-current", "true");
    const tr = (e.subtitles || []).some(s => s.lang === "tr");
    b.innerHTML = `${esc(e.title)}${tr ? "<small>TR</small>" : ""}${pct(p) ? `<div class="bar"><i style="width:${pct(p)}%"></i></div>` : ""}`;
    b.onclick = () => go(anime, i);
    list.appendChild(b);
    if (i === epIndex) setTimeout(() => b.scrollIntoView({ block: "nearest" }), 0);
  });
}

// Kısayollar: Shift+N sonraki, Shift+P önceki (oynatıcı kısayolları Plyr'da)
export function onKey(e) {
  if (!durum.current || /input|textarea/i.test(e.target.tagName)) return;
  if (e.shiftKey && e.key === "N") $("nextBtn").click();
  if (e.shiftKey && e.key === "P") $("prevBtn").click();
}
