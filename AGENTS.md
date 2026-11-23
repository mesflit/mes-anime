# AGENTS.md — mes-anime

Bu dosya bu depoda çalışan yapay zekâ ajanları (Claude, Codex vb.) içindir. İnsanlar için: README.md.

## Proje özeti

GitHub Pages'te yayınlanan, AES-128 şifreli HLS videoları oynatan statik anime sitesi.
Site tek dosyadır (`index.html`, derleme adımı yok). Videolar ayrı, herkese açık depolardadır
(ör. `mesflit/opm`); site her deponun kökündeki `mes.anime` dosyasını çalışma anında
`raw.githubusercontent.com`'dan okur. Hangi depoların okunacağı `data/depolar.txt`'dedir.

Kullanıcı Türkçe konuşur; arayüz metinleri, betik çıktıları, commit mesajları ve belgeler
Türkçedir. Kullanıcı genelde telefondan (Termux) çalışır.

## Veri akışı

    data/depolar.txt ──> (her satır) https://raw.githubusercontent.com/<sahip>/<depo>/<dal>/mes.anime
                                         │
                                         ├─ poster    -> <base>/poster.jpg
                                         └─ episodes  -> <base>/<path>/index.m3u8, <base>/<path>/<dil>.vtt

`index.html` içindeki `loadRepo()` `mes.anime`'yi sitenin iç biçimine çevirir:
`{id, title, category, poster, episodes: [{id, title, m3u8, subtitles: [{lang, label, src}]}]}`.
Sitenin geri kalanı yalnızca bu iç biçimi bilir.

## Değişmezler (bozma)

- **Kimlikler kalıcıdır.** Anime `id` = depo adı (veya `mes.anime` içindeki `id`), bölüm
  `id` = `path`'teki `/` yerine `-` (`s1/ep1` -> `s1-ep1`). `localStorage` anahtarları
  (`ma:p:<anime>:<bölüm>`, `ma:last:<anime>`, `ma:subLang`, `ma:autoNext`) ve paylaşılan
  linkler (`#/izle/<anime>/<bölüm>`) bunlara bağlıdır. Biçimi değiştirme.
- **Sezon** bölüm kimliğinin `^s(\d+)-` kısmından okunur (`seasonOf`). Klasör düzeni `sN/epM`.
- **Şifreleme:** anahtar = `SHA-256(VIDEO_SECRET_KEY)[:16]`. `araclar/video.py` (`aes_anahtari`)
  ve `index.html` (`initKey`) aynı türetmeyi yapmalı. `index.m3u8` içindeki `URI="enc.key"`
  isteğini `KeyInterceptLoader` ağa çıkmadan karşılar; indirme (`downloadEpisode`) aynı
  `AES_KEY_BUF` ile WebCrypto AES-CBC çözer. Bunlardan biri değişirse tüm mevcut bölümler
  oynatılamaz/indirilemez.
- `index.html`'deki `const SECRET_KEY = "__VIDEO_SECRET_KEY__"` satırı `deploy.yml`'de `sed` ile doldurulur;
  `mes.py anahtar` anahtarı yayındaki sayfadan bu satırla okur. Satırın biçimini ve yer tutucunun adını
  değiştirme, gerçek anahtarı asla depoya yazma. Kullanıcının cihazlarında anahtar yoktu; tek kaynak
  GitHub secret'ı + yayındaki sayfa.
- `mes.anime` biçimi: README'deki tabloya bak. Betikler var olan `title` ve bilinmeyen
  alanları korur; bunu bozma (kullanıcı başlıkları elle düzenler).
- `araclar/katalog.py` (`yaz`) her bölümü tek satıra yazar (okunabilir diff için). Biçim JSON kalmalı.

## Dosyalar

| Dosya | Görev |
|---|---|
| `index.html` | Tüm site. hls.js 1.5.17 + Plyr 3.7.8 (jsDelivr); indirmede mux.js 7.0.3 sadece gerekince yüklenir. Hash tabanlı yönlendirme |
| `data/depolar.txt` | `sahip/depo[@dal]`, `#` yorum. Sıra = ana sayfa sırası |
| `mes.py` | Tek giriş noktası (argparse): `yeni`, `ekle`, `guncelle`, `klonla`, `altyazi`. Sadece iş akışı; işin kendisi `araclar/`'da |
| `araclar/ayar.py` | `KULLANICI` (GH_USER, varsayılan mesflit), `KOK`, `depo_yolu()`, `calistir()`, `gizli_anahtar()` (ortam değişkeni -> `~/.mes-anime-anahtar` -> yayındaki sitenin `SECRET_KEY`'i; `MES_SITE` ile adres değişir) |
| `araclar/video.py` | `hls_yap()`: ffprobe ile ses seçimi (jpn öncelikli), ffmpeg ile 6 sn'lik AES-128 HLS |
| `araclar/altyazi.py` | VTT `oku/yaz/temizle`, `cikar()` (metin altyazı, eng öncelikli; resimse .sup), `cevir()` (deep-translator, başarısızsa RuntimeError, sahte tr.vtt yazmaz), `hazirla()` |
| `araclar/katalog.py` | `mes.anime`: `oku/yaz/guncelle`, `bolumler()`, `sonraki_bolum()` |
| `araclar/depo.py` | `klonla()` (blob:none + sparse `!*.ts`, boş depoyu da açar), `gonder()` (add --sparse, commit, push, sparse reapply), `olustur()` (gh), `siteye_ekle()` |
| `.github/workflows/deploy.yml` | `master`/`main` push -> anahtar enjekte -> Pages |
| `scripts/pipeline.py`, `auto_fansub.yml` | ESKİ, kullanılmıyor (Doodstream, eski `animes.json`). Kullanıcı istemedikçe dokunma |

`mes.py` mes-anime kökünden çalıştırılır ve video deposunu `../<depo>` olarak bekler
(yoksa `depo.hazirla()` klonlar). Yeni iş eklerken mantığı `araclar/` içine koy, `mes.py`'ye
sadece komut ekle.

## Sık görevler

- **Yeni anime:** `python3 mes.py yeni <depo> "Ad" --kategori X --kapak resim.jpg`
- **Yeni bölüm(ler):** `python3 mes.py ekle <depo> <video|klasör> [--sezon N] [--bolum M]`
- **Bölüm klasörleri depoda, liste eksik:** `python3 mes.py guncelle <depo>`
- **Video deposunu klonlarken** `.ts` dosyalarını indirme (depo 8 GB+): `python3 mes.py klonla <depo>`
  veya `git clone --depth 1 --filter=blob:none --no-checkout` + `git sparse-checkout set --no-cone '/*' '!*.ts'`.
  Hafif klonda `git ls-tree -l`, `git log -p` gibi blob içeriğine bakan komutlar videoları indirmeye başlar.

## Test

Otomatik test yok. Değişiklik sonrası:

- `python3 -m py_compile mes.py araclar/*.py`
- `python3 mes.py guncelle opm --gonderme` -> yeni bölüm yazmamalı ve `git -C ../opm diff` boş olmalı.
- `ekle` testi: `git init` ile sahte bir `../deneme` deposu, `katalog.guncelle(..., ad=...)`, ffmpeg
  `lavfi testsrc` + `sine` + gömülü `.srt` ile test videosu, `VIDEO_SECRET_KEY=... python3 mes.py ekle deneme video.mkv --gonderme`.
- İndirme testi: test videosunu `VIDEO_SECRET_KEY=__VIDEO_SECRET_KEY__` ile kodla (yerel sayfa bu
  yer tutucuyu anahtar olarak kullanır), Playwright ile düğmeye bas, çıkan MP4'ü
  `ffmpeg -v error -i x.mp4 -f null -` ile doğrula. Chromium'u `LANG=C.UTF-8` ile çalıştır,
  yoksa Türkçe karakterli dosya adları "download" olur.
- Site: `python3 -m http.server` ile aç, tarayıcıda ana sayfa kartı, bölüm sayısı, sezon
  sekmeleri ve altyazı listesini kontrol et. Videolar yerelde yoksa `.ts` 404'leri normaldir.
  `raw.githubusercontent.com` isteklerini yerel `../opm` dosyalarına yönlendirerek (ör.
  Playwright `page.route`) çevrimdışı test edilebilir.

## Dikkat

- `raw.githubusercontent.com` ~5 dk önbellekler; push sonrası değişiklik hemen görünmeyebilir.
- Video depoları herkese açık olmalı (raw URL'leri kimlik doğrulamasız okunur).
- Commit mesajları Türkçe, `feat:` / `fix:` / `style:` / `chore:` önekleriyle.
- Video deposuna ve `master`'a push etmeden önce kullanıcıdan onay al.
