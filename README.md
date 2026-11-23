# MesAnime

GitHub Pages üzerinde çalışan, şifreli ve parçalı (AES-128 HLS) anime izleme sitesi.

- **Bu depo (`mes-anime`)**: site (`index.html`), anime depolarının listesi (`data/depolar.txt`)
  ve yönetim aracı (`mes.py`).
- **Video depoları (ör. `mesflit/opm`)**: bölümlerin şifreli video parçaları, altyazıları ve
  o animenin bilgilerini tutan `mes.anime` dosyası.

Site açılırken `data/depolar.txt`'deki her deponun `mes.anime` dosyasını doğrudan GitHub'dan okur.
Yeni bölüm için mes-anime'ye dokunmak gerekmez, sadece video deposuna push edilir.

## Hızlı başlangıç

    python3 mes.py yeni deathnote "Death Note" --kategori Gerilim --kapak kapak.jpg
    python3 mes.py ekle deathnote /sdcard/Download/deathnote/

Bu kadar. İlk komut GitHub'da depoyu açar, `mes.anime`'yi oluşturur ve siteye ekler.
İkincisi klasördeki tüm videoları sırayla şifreler, altyazılarını hazırlar ve her bölümü
ayrı ayrı gönderir. Birkaç dakika sonra sitede görünür.

## Özellikler

- Türkçe altyazı (varsayılan), İngilizce yedek; seçilen dil (veya kapalı) hatırlanır
- Kaldığın yerden devam et, "İzlemeye Devam Et" satırı, izlenen bölümlerde ✓ işareti
- Sezon sekmeleri, otomatik sonraki bölüm, `Shift+N` / `Shift+P` kısayolları
- Paylaşılabilir bölüm linkleri (`#/izle/opm/s1-ep3`), sayfa yenilenince bölüm kaybolmaz
- **İndirme**: bölümü MP4, altyazıları SRT olarak indirme (bkz. "İndirme nasıl çalışır?")
- **Kalite seçimi**: bölümün 480p kopyası varsa Otomatik / 1080p / 480p menüsü; internet yavaşsa kendiliğinden düşer (kopyaları video deposundaki `resize.py` üretir)
- Arama (anime adı ve kategoride)

## Depo yapısı

    mes-anime/
    ├── index.html             # Sitenin tamamı (HTML + CSS + JS, tek dosya)
    ├── mes.py                 # Yönetim aracı: yeni / ekle / guncelle / klonla / altyazi
    ├── araclar/               # mes.py'nin modülleri
    │   ├── ayar.py            #   ortak ayarlar (GitHub kullanıcı adı, yollar, dil adları)
    │   ├── video.py           #   videoyu şifreli HLS'e çevirme
    │   ├── altyazi.py         #   altyazı çıkarma / temizleme / çeviri
    │   ├── katalog.py         #   mes.anime okuma / yazma / güncelleme
    │   └── depo.py            #   git: hafif klon, gönderme, yeni depo, depolar.txt
    ├── data/
    │   ├── depolar.txt        # Sitede görünecek anime depoları (her satıra bir tane)
    │   ├── opm.jpg            # Eski kapak (artık opm/poster.jpg kullanılıyor)
    │   └── processed.txt      # pipeline.py'nin kaydı (kullanılmıyor)
    ├── scripts/pipeline.py    # ESKİ: torrent + Doodstream hattı (kapalı, bkz. aşağı)
    └── .github/workflows/
        ├── deploy.yml         # master'a push -> anahtarı gömer, GitHub Pages'e yayınlar
        └── auto_fansub.yml    # ESKİ: pipeline.py'yi çalıştırır (sadece elle)

Video depoları mes-anime'nin **yanında** durur (`mes.py` onları `../<depo>` olarak arar, yoksa kendisi klonlar):

    ~/
    ├── mes-anime/
    ├── opm/
    └── deathnote/

## Kurulum (telefon veya PC, her cihazda bir kere)

Telefonda (Termux):

    pkg install -y git gh python ffmpeg
    pip install deep-translator          # otomatik Türkçe çeviri için
    gh auth login                        # "yeni" komutunun depo açabilmesi için
    git clone https://github.com/mesflit/mes-anime.git && cd mes-anime
    python3 mes.py anahtar               # şifre anahtarını siteden alıp bu cihaza kaydeder

PC'de: git, Python, ffmpeg ve [gh](https://cli.github.com) kur, sonra son dört satır aynı
(Windows'ta `python3` yerine `python`).

GitHub Pages ayarı (bir kere): Settings -> Pages -> Source -> GitHub Actions

## Şifre anahtarı (VIDEO_SECRET_KEY)

Videolar bu anahtarla şifrelenir. **Tüm cihazlarda aynı anahtar olmalı**, yoksa o cihazla
eklenen bölümler sitede oynamaz.

- Asıl anahtar GitHub'da secret olarak durur (Settings -> Secrets -> Actions -> `VIDEO_SECRET_KEY`).
  GitHub onu bir daha göstermez, ama site yayınlanırken sayfaya yazılır.
- `python3 mes.py anahtar` bu yüzden anahtarı **yayındaki siteden** alır ve cihazda
  `~/.mes-anime-anahtar` dosyasına kaydeder. Cihazda anahtar yoksa `ekle` de bunu kendisi yapar.
  Yani telefonda da PC'de de elle bir şey ayarlamana gerek yok.
- `mes.py` anahtarı sırayla şuradan arar: `VIDEO_SECRET_KEY` ortam değişkeni -> `~/.mes-anime-anahtar` -> site.
- `python3 mes.py anahtar` cihazdaki anahtarın sitedekiyle aynı olup olmadığını da kontrol eder.
  "AYNI DEĞİL" derse `~/.bashrc`'deki eski `export VIDEO_SECRET_KEY=...` satırını sil.
- Not almak istersen: `python3 mes.py anahtar --goster`
- Site başka adresteyse: `MES_SITE=https://adres/ python3 mes.py anahtar`
- **GitHub'daki secret'ı asla değiştirme.** Değişirse eski bölümlerin hepsi oynatılamaz
  (yeniden kodlanmaları gerekir).

İlk kez kuruluyorsa (secret hiç yoksa):

    gh secret set VIDEO_SECRET_KEY -R mesflit/mes-anime -b "$(openssl rand -hex 32)"

sonra master'a bir push yap (site yayınlansın) ve `python3 mes.py anahtar`.

## İki cihazdan çalışmak

Cihaz değiştirdiğinde önce diğer cihazın gönderdiklerini al:

    cd ~/mes-anime && git pull
    cd ~/opm && git pull               # çalışacağın anime deposunda

Aynı animeye aynı anda iki cihazdan bölüm ekleme.

## mes.py komutları

Hepsi mes-anime klasöründen çalıştırılır. `python3 mes.py <komut> -h` ayrıntıları gösterir.
Gönderme (git push) istemezsen her komuta `--gonderme` ekle.

### yeni — yeni anime

    python3 mes.py yeni <depo> "<Anime Adı>" [--kategori Aksiyon] [--kapak resim.jpg]

1. GitHub'da `mesflit/<depo>` yoksa **herkese açık** olarak açar (`gh` gerekir; yoksa elle aç)
2. Videolar olmadan `../<depo>`'ya klonlar
3. `mes.anime` oluşturur, kapağı depoya `poster.jpg` olarak kopyalar ve gönderir
4. `data/depolar.txt`'ye ekler ve mes-anime'yi gönderir

`<depo>` adı sitedeki kimlik olur (linkler `#/izle/<depo>/...`). **Sonradan değiştirme.**

### ekle — bölüm ekle

    python3 mes.py ekle <depo> <video veya klasör> [seçenekler]

| Seçenek | Açıklama |
|---|---|
| `--sezon 2` | Sezon numarası (varsayılan 1) |
| `--bolum 5` | İlk bölüm numarası (varsayılan: o sezonun son bölümü + 1) |
| `--baslik "Ad"` | Bölüm başlığı (tek dosyada; varsayılan "N. Sezon M. Bölüm") |
| `--altyazi tr:dosya.srt` | Hazır altyazı (tek dosyada; tekrar verilebilir). Dil yazılmazsa `tr` |
| `--ceviri-yok` | İngilizceden Türkçeye çevirme |
| `--hiz ultrafast` | ffmpeg hızı (`ultrafast` hızlı ama büyük dosya, `medium` yavaş ama küçük) |

Her video için sırayla:

1. **Video**: Japonca ses varsa onu, yoksa ilk sesi seçer; 6 sn'lik AES-128 şifreli HLS yapar
2. **Altyazı**: `--altyazi` verilenler -> yoksa videodaki metin altyazı (İngilizce öncelikli) `en.vtt`
   -> `tr.vtt` yoksa otomatik çeviri. Hepsi temizlenir (fansub notları, ASS çizimleri, tekrarlar)
3. **mes.anime** güncellenir
4. **Gönderilir** (commit + push) ve yüklenen `.ts` dosyaları diskten silinir

Klasör verilirse videolar doğal sırayla işlenir (`bolum2` < `bolum10`); başlamadan önce
hangi dosyanın hangi bölüm olacağı listelenir. Her bölüm ayrı gönderildiği için yarıda
kesilirse yapılanlar kaybolmaz; kalanlar için aynı komutu kalan dosyalarla tekrar çalıştır
(numara kendiliğinden devam eder).

### guncelle — listeyi yenile

    python3 mes.py guncelle <depo>

Bölüm klasörlerini elle eklediysen / sildiysen `mes.anime`'yi klasörlere göre yeniler ve gönderir.

### klonla — videolar olmadan indir

    python3 mes.py klonla <depo>

Video deposu 8 GB+; bu komut sadece `m3u8`/`vtt`/`mes.anime` indirir (~3 MB).
Zaten tam klon varsa `.ts` dosyalarını diskten kaldırır. (`ekle` ve diğerleri gerekirse kendisi klonlar.)

### altyazi — toplu altyazı işleri

    python3 mes.py altyazi temizle <depo>          # tüm .vtt'leri temizle
    python3 mes.py altyazi cevir <depo> [--hepsi]  # tr.vtt olmayanları çevir (--hepsi: hepsini)

## mes.anime dosyası

Her video deposunun kökünde durur. JSON biçimindedir, yollar depo köküne göredir:

    {
      "title": "One Punch Man",
      "category": "Aksiyon",
      "poster": "poster.jpg",
      "episodes": [
        {"path": "s1/ep1", "title": "1. Sezon 1. Bölüm", "subtitles": ["tr", "en"]},
        {"path": "s3/ep0", "title": "3. Sezon 0. Bölüm", "subtitles": ["tr", "en"]}
      ]
    }

| Alan | Açıklama |
|---|---|
| `title` | Sitede görünen anime adı |
| `category` | Kartta ve aramada görünür (ör. `Aksiyon`) |
| `poster` | Depodaki dosya adı (`poster.jpg`) veya tam URL. Boşsa kartta isim yazar |
| `episodes[].path` | Bölüm klasörü. İçinde `index.m3u8` olmalı |
| `episodes[].title` | Bölüm adı. Elle değiştirilebilir, `mes.py` üzerine yazmaz |
| `episodes[].subtitles` | O klasördeki `<dil>.vtt` dosyaları (`tr` önce) |
| `episodes[].variants` | Düşük kalite kopyaları: `[{"name": "480p", "path": "480p", "bandwidth": ..., "resolution": "854x480"}]`. Video deposundaki `resize.py` yazar |
| `episodes[].bandwidth`, `resolution` | Orijinalin bit hızı ve çözünürlüğü (`resize.py` yazar) |
| `episodes[].no_variants` | Orijinal zaten küçük, kopya gerekmez (`resize.py` yazar) |
| `id` (isteğe bağlı) | Animenin site kimliği. Yoksa depo adı (`opm`) kullanılır |
| `episodes[].id` (isteğe bağlı) | Yoksa `path`'ten üretilir: `s1/ep1` -> `s1-ep1` |

İnce noktalar:

- **Kimlikleri değiştirme.** Anime kimliği (depo adı) ve bölüm kimliği (`s1-ep1`) izleme
  geçmişinin, "kaldığın yer"in ve paylaşılan linklerin anahtarıdır. Depo adını veya klasör
  adını değiştirirsen izleyicilerin ilerlemesi sıfırlanır.
- **Sezon numarası** bölüm kimliğinin başındaki `sN`'den okunur. Klasörler `sN/epM` düzeninde olmalı.
- **Bölüm sırası** dosyadaki sıradır. `mes.py` sezon ve bölüm numarasına göre sıralar
  (`ep0` sezonun ilk bölümü olur).
- Geçersiz JSON (ör. fazladan virgül) o animenin sitede hiç görünmemesine yol açar.
  Elle düzenledikten sonra `python3 -m json.tool ../opm/mes.anime` ile kontrol et.

## data/depolar.txt

    # Yorum satırı
    mesflit/opm
    mesflit/baska-anime@dev      # main dışındaki bir dal

- Sıra = ana sayfadaki sıra. `mes.py yeni` satırı kendisi ekler.
- Bir deponun `mes.anime`'si okunamazsa (yok, bozuk JSON) o anime atlanır, diğerleri görünür.
  Sebep tarayıcı konsolunda yazar.

## İndirme nasıl çalışır?

İzleme sayfasında videonun altında **"⬇ Bölümü indir (MP4)"** ve her altyazı için
**"⬇ ... altyazı"** düğmeleri var.

- Bölüm, tarayıcıda parça parça indirilir (6 parça aynı anda), şifresi çözülür ve
  [mux.js](https://github.com/videojs/mux.js) ile tek bir **MP4** dosyasına çevrilir.
  mux.js yüklenemezse veya çeviremezse dosya **.ts** olarak verilir (VLC / MX Player açar).
- İlerleme yüzdesi gösterilir, "✕ İptal" ile durdurulabilir. Aynı anda tek bölüm iner;
  başka bölüme geçince indirme arka planda sürer.
- Altyazılar **.srt** olarak iner (videoyla aynı adla kaydedip oynatıcıda seç).
- Dosya bellekte birleştirildiği için çok eski telefonlarda uzun bölümler zorlanabilir.
- Not: İndirme, şifrelemenin amacını (videonun siteden dışarı çıkmaması) bilerek devre dışı bırakır.

## Yayın (deploy) ve şifreleme nasıl çalışır?

- `master`'a her push'ta `deploy.yml` çalışır: `index.html` içindeki `__VIDEO_SECRET_KEY__`
  yerine GitHub secret'ı yazılır ve site GitHub Pages'e yüklenir.
- Videolar AES-128 ile şifrelidir. Anahtar = `SHA-256(VIDEO_SECRET_KEY)`'in ilk 16 baytı.
  `index.m3u8` anahtarı `enc.key` diye ister; site bu isteği ağa çıkarmadan tarayıcıda üretir.
  Yani video depoları tek başına indirilse bile parçalar oynatılamaz.
- Not: anahtar yayınlanan sayfanın içinde durduğu için bu, sıradan indirmeye karşı bir
  önlemdir, kararlı birine karşı tam koruma değildir.
- Altyazılar şifresizdir. `raw.githubusercontent.com` VTT'yi `text/plain` sunduğu için
  site onları indirip `text/vtt` olarak oynatıcıya verir.
- İzleme ilerlemesi ve ayarlar sadece tarayıcıda (`localStorage`, `ma:` önekli) tutulur.
- Push sonrası değişikliklerin görünmesi GitHub raw önbelleği yüzünden ~5 dk sürebilir.

## Sorun giderme

| Durum | Çözüm |
|---|---|
| `Site okunamadı` | İnternet var mı? Site adresi farklıysa `MES_SITE=https://adres/` |
| Yeni bölüm sitede oynamıyor ama eskiler oynuyor | Anahtar farklı: `python3 mes.py anahtar` ile kontrol et, bölümü tekrar ekle |
| `rejected` (push reddedildi) | Diğer cihaz önce göndermiş: o depoda `git pull`, sonra tekrar |
| `Türkçe çeviri atlandı` | `pip install deep-translator`, sonra `python3 mes.py altyazi cevir <depo>` |
| `Altyazı resim formatında` | Videonun yanına `.sup` kaydedildi. `.srt` bul, `--altyazi tr:dosya.srt` ile tekrar ekle |
| `gh yok` | `pkg install gh && gh auth login` ya da depoyu github.com/new'den elle aç (herkese açık) |
| Anime sitede yok | `data/depolar.txt`'de var mı? Deponun `mes.anime`'si geçerli JSON mu? |
| Bölüm yanlış numarayla eklendi | Klasörü sil (`git rm -r s1/ep5`), `python3 mes.py guncelle <depo>`, doğru `--bolum` ile tekrar ekle |

## Eski / kullanılmayan

- `scripts/pipeline.py` + `auto_fansub.yml`: SubsPlease RSS'ten torrent indirip altyazıyı
  videoya gömen ve Doodstream'e yükleyen eski hat. Zamanlanmış çalışması kapalı; ürettiği
  `embed_url` bölümleri şu anki oynatıcıyla uyumlu değil ve hâlâ eski `data/animes.json`'a yazar.
  Kullanılmadıkça dokunmayın.
