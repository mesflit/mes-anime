// Ana sayfa: anime kartları, arama, "İzlemeye Devam Et"
import { SITE_ADI } from "./ayarlar.js";
import { durum } from "./durum.js";
import { go } from "./gezinme.js";
import { getProg, pct, store } from "./kayit.js";
import { teardown } from "./oynatici.js";
import { hasTr, seasonOf } from "./veri.js";
import { $, esc } from "./yardimci.js";

const sonIndex = a => Math.max(0, a.episodes.findIndex(e => e.id === store.get("last:" + a.id, null)));
const arkaPlan = url => url ? `style="background-image:url('${esc(url)}')"` : "";

export function showHome() {
  teardown();
  durum.current = null;
  document.title = SITE_ADI;
  $("watchView").classList.add("hidden");
  $("homeView").classList.remove("hidden");
  renderHome();
}

export function renderHome() {
  const q = $("search").value.toLocaleLowerCase("tr").trim();
  const grid = $("animeGrid"), bos = $("emptyState");
  grid.innerHTML = "";

  // Yükleniyor / hata durumları
  if (durum.yukleniyor) {
    bos.innerHTML = `<div class="spinner" aria-hidden="true"></div>Animeler yükleniyor...`;
    bos.classList.remove("hidden");
    $("continueRow").classList.add("hidden");
    return;
  }
  if (durum.hata) {
    bos.innerHTML = `${esc(durum.hata)}<br><button class="btn" onclick="location.reload()">Tekrar dene</button>`;
    bos.classList.remove("hidden");
    return;
  }

  const list = durum.animeler.filter(a => (a.title + " " + (a.category || "")).toLocaleLowerCase("tr").includes(q));
  bos.textContent = durum.animeler.length ? "Sonuç bulunamadı." : "Henüz anime eklenmemiş.";
  bos.classList.toggle("hidden", list.length > 0);
  list.forEach(anime => {
    const card = document.createElement("button");
    card.className = "card";
    card.onclick = () => go(anime, sonIndex(anime));
    const seasons = new Set(anime.episodes.map(seasonOf)).size;
    card.setAttribute("aria-label", `${anime.title}, ${anime.episodes.length} bölüm`);
    card.innerHTML = `
      <div class="poster" ${arkaPlan(anime.poster)}>
        ${anime.poster ? "" : esc(anime.title)}
        ${hasTr(anime) ? `<span class="badge tr">TR Altyazı</span>` : ""}
        <span class="badge">${anime.episodes.length} Bölüm</span>
      </div>
      <div class="card-body">
        <div class="card-title">${esc(anime.title)}</div>
        <div class="card-meta">${esc(anime.category || "Anime")}${seasons > 1 ? ` · ${seasons} Sezon` : ""}</div>
      </div>`;
    grid.appendChild(card);
  });
  renderContinue(q);
}

function renderContinue(q) {
  const items = [];
  durum.animeler.forEach(a => {
    const lastId = store.get("last:" + a.id, null);
    const idx = a.episodes.findIndex(e => e.id === lastId);
    if (idx < 0) return;
    const p = getProg(a, a.episodes[idx]);
    items.push({ a, idx, p, at: (p && p.at) || 0 });
  });
  items.sort((x, y) => y.at - x.at);
  const grid = $("continueGrid");
  grid.innerHTML = "";
  $("continueRow").classList.toggle("hidden", !items.length || !!q);
  items.forEach(({ a, idx, p }) => {
    const ep = a.episodes[idx];
    const card = document.createElement("button");
    card.className = "card";
    card.onclick = () => go(a, idx);
    card.setAttribute("aria-label", `Devam et: ${a.title}, ${ep.title}`);
    card.innerHTML = `
      <div class="poster wide" ${arkaPlan(a.poster)}>
        <span class="badge">▶ Devam</span>
      </div>
      <div class="bar"><i style="width:${pct(p)}%"></i></div>
      <div class="card-body">
        <div class="card-title">${esc(a.title)}</div>
        <div class="card-meta">${esc(ep.title)}</div>
      </div>`;
    grid.appendChild(card);
  });
}
