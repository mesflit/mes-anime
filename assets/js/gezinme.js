// Sayfa adresleri: #/ (ana sayfa), #/izle/<anime>/<bölüm>
export const go = (anime, idx) => {
  location.hash = `#/izle/${encodeURIComponent(anime.id)}/${encodeURIComponent(anime.episodes[idx].id)}`;
};
