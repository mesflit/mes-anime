// Sayfanın paylaşılan durumu. Modüller bunu okur/yazar.
export const durum = {
  animeler: [],       // loadAnimes() sonucu
  yukleniyor: true,   // anime listesi henüz gelmedi
  hata: "",           // liste yüklenemediyse mesaj
  aesKey: null,       // initKey() ile üretilen 16 baytlık anahtar
  hls: null,          // açık bölümün hls.js nesnesi
  player: null,       // açık bölümün Plyr nesnesi
  blobUrls: [],       // kapatınca serbest bırakılacak blob: adresleri
  current: null,      // { anime, index } açık bölüm
  dl: null,           // süren indirme { key, title, pct, ctrl, text }
};
window.mesAnime = durum; // tarayıcı konsolunda hata ayıklamak için
