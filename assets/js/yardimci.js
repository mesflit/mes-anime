// Küçük yardımcılar
export const $ = id => document.getElementById(id);
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const fileName = s => s.replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim();

export function saveBlob(blob, name) {
  const u = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: u, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 60000);
}

// Bir betiği sadece gerektiğinde yükler (ör. indirmede mux.js)
export function loadScript(src, varMi) {
  return new Promise((ok, no) => {
    if (varMi && varMi()) return ok();
    const s = Object.assign(document.createElement("script"), { src, onload: ok, onerror: () => no(new Error(src + " yüklenemedi")) });
    document.head.appendChild(s);
  });
}
