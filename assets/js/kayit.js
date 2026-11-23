// Tarayıcıda saklanan ayarlar ve izleme ilerlemesi (localStorage, "ma:" önekli).
// Anahtar biçimlerini değiştirme: izleyicilerin ilerlemesi bunlara bağlı.
export const store = {
  get(k, d) { try { const v = localStorage.getItem("ma:" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("ma:" + k, JSON.stringify(v)); } catch {} }
};
export const progKey = (a, e) => `p:${a.id}:${e.id}`;
export const getProg = (a, e) => store.get(progKey(a, e), null);
export const pct = p => p && p.d ? Math.min(100, Math.round(p.t / p.d * 100)) : 0;
