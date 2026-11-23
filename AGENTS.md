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
- **Şifreleme:** anahtar = `SHA-256(VIDEO_SECRET_KEY)[:16]`. `pack.py` (Python) ve
  `index.html` (`initKey`) aynı türetmeyi yapmalı. `index.m3u8` içindeki `URI="enc.key"`
  isteğini `KeyInterceptLoader` ağa çıkmadan karşılar. Bu üçünden biri değişirse tüm
  mevcut bölümler oynatılamaz.
- `index.html`'deki `__VIDEO_SECRET_KEY__` yer tutucusu `deploy.yml`'de `sed` ile değiştirilir.
  Adını değiştirme, gerçek anahtarı asla depoya yazma.
- `mes.anime` biçimi: README'deki tabloya bak. Betikler var olan `title` ve bilinmeyen
  alanları korur; bunu bozma (kullanıcı başlıkları elle düzenler).
- `mesanime.py` her bölümü tek satıra yazar (okunabilir diff için). Biçim JSON kalmalı.

## Dosyalar

| Dosya | Görev |
|---|---|
| `index.html` | Tüm site. hls.js 1.5.17 + Plyr 3.7.8 (jsDelivr). Hash tabanlı yönlendirme |
| `data/depolar.txt` | `sahip/depo[@dal]`, `#` yorum. Sıra = ana sayfa sırası |
| `scripts/mesanime.py` | `../<depo>/sN/epM/index.m3u8` klasörlerini tarar, `../<depo>/mes.anime` yazar. `update()` ve `set_title()` başka betiklerden çağrılır |
| `scripts/pack.py` | ffmpeg ile 6 sn'lik AES-128 HLS üretir, altyazıyı çıkarır/çevirir, sonra `mesanime.update()` |
| `scripts/altyazi.py` | `temizle` / `cevir` / `kaydet` (kaydet = `mesanime.update`) |
| `scripts/subs.py` | VTT ayrıştır/temizle/yaz (fansub notları, ASS vektör çizimleri, tekrarlar) |
| `scripts/hafif_klon.sh` | Video deposunu `blob:none` + sparse (`!*.ts`) klonlar |
| `.github/workflows/deploy.yml` | `master`/`main` push -> anahtar enjekte -> Pages |
| `scripts/pipeline.py`, `auto_fansub.yml` | ESKİ, kullanılmıyor (Doodstream, eski `animes.json`). Kullanıcı istemedikçe dokunma |

Betikler mes-anime kökünden çalıştırılır ve video deposunu `../<depo>` olarak bekler.

## Sık görevler

- **Yeni bölüm (video dosyası var):** `python3 scripts/pack.py <video> <depo> sN/epM --extract-sub --tr`,
  sonra video deposunda `git add --sparse -A && git commit && git push`.
- **Bölüm klasörleri zaten depoda, liste eksik:** `python3 scripts/mesanime.py <depo>`, sonra
  video deposunda yalnızca `mes.anime`'yi commit + push.
- **Yeni anime:** video deposunda `mes.anime` oluştur (`--anime`, `--category`, `--poster`),
  sonra burada `data/depolar.txt`'ye satır ekle.
- **Video deposunu klonlarken** `.ts` dosyalarını indirme (depo 8 GB+): `bash scripts/hafif_klon.sh <depo>`
  veya `git clone --depth 1 --filter=blob:none --no-checkout` + `git sparse-checkout set --no-cone '/*' '!*.ts'`.

## Test

Otomatik test yok. Değişiklik sonrası:

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/mesanime.py opm` -> "yeni bölüm yok" ve `git -C ../opm diff` boş olmalı
  (biçim değişmediyse).
- Site: `python3 -m http.server` ile aç, tarayıcıda ana sayfa kartı, bölüm sayısı, sezon
  sekmeleri ve altyazı listesini kontrol et. Videolar yerelde yoksa `.ts` 404'leri normaldir.
  `raw.githubusercontent.com` isteklerini yerel `../opm` dosyalarına yönlendirerek (ör.
  Playwright `page.route`) çevrimdışı test edilebilir.

## Dikkat

- `raw.githubusercontent.com` ~5 dk önbellekler; push sonrası değişiklik hemen görünmeyebilir.
- Video depoları herkese açık olmalı (raw URL'leri kimlik doğrulamasız okunur).
- `scripts/__pycache__/` depoda izleniyor; bu dosyaları commit'e katma.
- Commit mesajları Türkçe, `feat:` / `fix:` / `style:` / `chore:` önekleriyle.
- Video deposuna ve `master`'a push etmeden önce kullanıcıdan onay al.
