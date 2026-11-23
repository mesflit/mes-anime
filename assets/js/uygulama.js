// Giriş noktası: açılış ve sayfa yönlendirme
import { durum } from "./durum.js";
import { store } from "./kayit.js";
import { renderHome, showHome } from "./anasayfa.js";
import { onKey, openEpisode } from "./izleme.js";
import { initKey } from "./sifre.js";
import { loadAnimes } from "./veri.js";
import { $ } from "./yardimci.js";

function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  if (parts[0] === "izle" && parts[1]) {
    const anime = durum.animeler.find(a => a.id === parts[1]);
    if (anime && anime.episodes.length) {
      let idx = anime.episodes.findIndex(e => e.id === parts[2]);
      if (idx < 0) idx = Math.max(0, anime.episodes.findIndex(e => e.id === store.get("last:" + anime.id, null)));
      return openEpisode(anime, idx);
    }
  }
  showHome();
}

async function boot() {
  $("search").addEventListener("input", () => { if (location.hash.length > 2) location.hash = "#/"; renderHome(); });
  $("autoNext").checked = store.get("autoNext", true);
  $("autoNext").onchange = e => store.set("autoNext", e.target.checked);
  document.addEventListener("keydown", onKey);
  showHome();                                   // "yükleniyor" göster

  const [, sonuc] = await Promise.all([initKey(), loadAnimes()]);
  durum.animeler = sonuc.animeler;
  durum.hata = sonuc.hata;
  durum.yukleniyor = false;
  window.addEventListener("hashchange", route);
  route();
}

boot();
