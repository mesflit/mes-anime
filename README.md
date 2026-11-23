# MesAnime

GitHub Pages üzerinde çalışan, şifreli ve parçalı (AES-128 HLS) anime izleme sitesi.

- **Bu depo (`mes-anime`)**: site (`index.html`), anime depolarının listesi (`data/depolar.txt`) ve yardımcı betikler.
- **Video depoları (ör. `mesflit/opm`)**: bölümlerin şifreli video parçaları, altyazıları ve
  o animenin bilgilerini tutan `mes.anime` dosyası.

Site açılırken `data/depolar.txt`'deki her deponun `mes.anime` dosyasını doğrudan GitHub'dan okur.
Yeni bölüm için mes-anime'ye dokunmak gerekmez, sadece video deposuna push edilir.

## Özellikler

- Türkçe altyazı (varsayılan), İngilizce yedek; seçilen dil (veya kapalı) hatırlanır
- Kaldığın yerden devam et, "İzlemeye Devam Et" satırı, izlenen bölümlerde ✓ işareti
- Sezon sekmeleri, otomatik sonraki bölüm, `Shift+N` / `Shift+P` kısayolları
- Paylaşılabilir bölüm linkleri (`#/izle/opm/s1-ep3`), sayfa yenilenince bölüm kaybolmaz
- Arama (anime adı ve kategoride)

## Depo yapısı

    mes-anime/
    ├── index.html                 # Sitenin tamamı (HTML + CSS + JS, tek dosya)
    ├── data/
    │   ├── depolar.txt            # Sitede görünecek anime depoları (her satıra bir tane)
    │   ├── opm.jpg                # Eski kapak (artık opm/poster.jpg kullanılıyor)
    │   └── processed.txt          # pipeline.py'nin kaydı (kullanılmıyor)
    ├── scripts/
    │   ├── pack.py                # Video -> şifreli HLS + altyazı + mes.anime güncelleme
    │   ├── mesanime.py            # Klasörleri tarayıp mes.anime oluşturur/günceller
    │   ├── altyazi.py             # Altyazı temizleme / çeviri / kaydetme
    │   ├── subs.py                # VTT ayrıştırma ve temizleme (altyazi.py ve pack.py kullanır)
    │   ├── hafif_klon.sh          # Video deposunu .ts dosyaları olmadan klonlar
    │   └── pipeline.py            # ESKİ: torrent + Doodstream hattı (kapalı, bkz. aşağı)
    └── .github/workflows/
        ├── deploy.yml             # master'a push -> anahtarı gömer, GitHub Pages'e yayınlar
        └── auto_fansub.yml        # ESKİ: pipeline.py'yi çalıştırır (sadece elle)

Video deposu ve betikler **yan yana** durmalı: betikler video deposunu `../<depo>` olarak arar.

    ~/
    ├── mes-anime/
    └── opm/

## İlk Kurulum

    pkg install -y git gh openssl-tool python ffmpeg
    export VIDEO_SECRET_KEY=$(openssl rand -hex 32)
    echo "export VIDEO_SECRET_KEY=$VIDEO_SECRET_KEY" >> ~/.bashrc
    gh secret set VIDEO_SECRET_KEY -b "$VIDEO_SECRET_KEY"

GitHub Pages ayarı: Settings -> Pages -> Source -> GitHub Actions

> `VIDEO_SECRET_KEY` bir kere belirlenir ve **asla değiştirilmez**. Değişirse daha önce
> şifrelenmiş tüm bölümler oynatılamaz (hepsinin yeniden kodlanması gerekir).

## Video deposunu videolar OLMADAN klonlama

Video deposu (opm) 8 GB'tan büyük. Yeni bölüm eklemek için tamamını indirmene gerek yok:

    git clone https://github.com/mesflit/mes-anime.git
    cd mes-anime
    bash scripts/hafif_klon.sh opm      # ../opm klasörüne sadece m3u8/vtt/mes.anime iner (~2-3 MB)

Zaten tam klonun varsa aynı komut `.ts` dosyalarını diskten kaldırır.

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
| `episodes[].title` | Bölüm adı. Elle değiştirilebilir, betikler üzerine yazmaz |
| `episodes[].subtitles` | O klasördeki `<dil>.vtt` dosyaları. Sıra = menüdeki sıra (`tr` önce) |
| `id` (isteğe bağlı) | Animenin site kimliği. Yoksa depo adı (`opm`) kullanılır |
| `episodes[].id` (isteğe bağlı) | Yoksa `path`'ten üretilir: `s1/ep1` -> `s1-ep1` |

İnce noktalar:

- **Kimlikleri değiştirme.** Anime kimliği (depo adı) ve bölüm kimliği (`s1-ep1`) izleme
  geçmişinin, "kaldığın yer"in ve paylaşılan linklerin anahtarıdır. Depo adını veya klasör
  adını değiştirirsen izleyicilerin ilerlemesi sıfırlanır.
- **Sezon numarası** bölüm kimliğinin başındaki `sN`'den okunur. Klasörler `sN/epM` düzeninde olmalı.
- **Bölüm sırası** dosyadaki sıradır. `mesanime.py` sezon ve bölüm numarasına göre sıralar
  (`ep0` sezonun ilk bölümü olur). Elle eklerken sırayı korumaya dikkat et.
- Geçersiz JSON (ör. fazladan virgül) o animenin sitede hiç görünmemesine yol açar.
  Elle düzenledikten sonra `python3 -m json.tool ../opm/mes.anime` ile kontrol et.

`mes.anime`'yi elle yazmana gerek yok, klasörlere bakıp kendisi oluşturur:

    python3 scripts/mesanime.py opm

Yeni klasörleri ekler, silinmiş klasörleri çıkarır, altyazı listelerini yeniler, var olan
başlıklara dokunmaz, yenilere "N. Sezon M. Bölüm" verir.

## Yeni Bölüm Ekleme

    python3 scripts/pack.py /sdcard/Download/bolum.mkv opm s3/ep13 --extract-sub --tr
    cd ../opm && git add --sparse -A && git commit -m "feat: S3 B13" && git push
    git sparse-checkout reapply          # yüklenen .ts dosyalarını diskten siler

`pack.py` `mes.anime`'yi kendisi günceller. Push ettikten birkaç dakika sonra bölüm sitede
görünür (GitHub raw önbelleği ~5 dk). mes-anime'ye push gerekmez.

| Seçenek | Açıklama |
|---|---|
| `--title "Ad"` | Bölüm başlığı (boşsa "N. Sezon M. Bölüm") |
| `--extract-sub` | MKV içindeki ilk altyazıyı çıkarır ve temizler (`en.vtt`) |
| `--tr` | İngilizce altyazıyı otomatik Türkçeye çevirir (`pip install deep-translator`) |
| `--sub tr:altyazi.srt` | Hazır altyazı ekler (birden çok kez verilebilir) |
| `--lang jpn` | Ses dili (varsayılan `jpn`; tek ses varsa `0`) |
| `--preset veryfast` | FFmpeg hızı (`ultrafast` daha hızlı, dosya daha büyük) |
| `--anime`, `--category`, `--poster` | Sadece yeni animenin ilk bölümünde gerekli |

İnce noktalar:

- `VIDEO_SECRET_KEY` tanımlı değilse `pack.py` durur (`source ~/.bashrc`).
- Altyazı resim formatındaysa (PGS/DVD), metne çevrilemez; `.sup` olarak videonun yanına
  kaydedilir, OCR ile `.srt` yapıp `--sub` ile eklemen gerekir.
- `git add --sparse -A` şart: hafif klonda `.ts` dosyaları sparse dışında olduğu için
  `--sparse` olmadan eklenmezler.
- GitHub tek dosyada 100 MB sınırı koyar; 6 sn'lik parçalar bunun çok altındadır.

Bölüm klasörlerini başka yolla (ör. hazır dosya kopyalayarak) eklediysen push etmeden önce:

    python3 scripts/mesanime.py opm

## Yeni Anime Ekleme

1. GitHub'da yeni, **herkese açık** bir video deposu oluştur (ör. `mesflit/yeni-repo`).
   Site dosyaları `raw.githubusercontent.com`'dan okuduğu için özel depolar çalışmaz.
2. Klonla, bölümleri ekle, `mes.anime` oluştur ve pushla:

       bash scripts/hafif_klon.sh yeni-repo
       python3 scripts/pack.py bolum1.mkv yeni-repo s1/ep1 --anime "Anime Adı" --category "Aksiyon" --poster kapak.jpg --extract-sub --tr
       cd ../yeni-repo && git add --sparse -A && git commit -m "feat: ilk bölüm" && git push

   (Bölümler hazırsa `pack.py` yerine: `python3 scripts/mesanime.py yeni-repo --anime "Anime Adı" --poster kapak.jpg`)
3. mes-anime'de `data/depolar.txt`'ye `mesflit/yeni-repo` satırını ekle ve master'a pushla.

`--poster` yerel bir dosyaysa depoya `poster.<uzantı>` olarak kopyalanır.

## data/depolar.txt

    # Yorum satırı
    mesflit/opm
    mesflit/baska-anime@dev      # main dışındaki bir dal

- Sıra = ana sayfadaki sıra.
- Bir deponun `mes.anime`'si okunamazsa (yok, bozuk JSON) o anime atlanır, diğerleri görünür.
  Sebep tarayıcı konsolunda yazar.

## Altyazı araçları

    python3 scripts/altyazi.py temizle opm   # fansub notlarını/çöp satırları temizler
    python3 scripts/altyazi.py cevir opm     # tr.vtt olmayan bölümleri çevirir (--force: hepsini)
    python3 scripts/altyazi.py kaydet opm    # mes.anime'yi klasörlere göre yeniler

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

## Eski / kullanılmayan

- `scripts/pipeline.py` + `auto_fansub.yml`: SubsPlease RSS'ten torrent indirip altyazıyı
  videoya gömen ve Doodstream'e yükleyen eski hat. Zamanlanmış çalışması kapalı; ürettiği
  `embed_url` bölümleri şu anki oynatıcıyla uyumlu değil ve hâlâ eski `data/animes.json`'a yazar.
  Kullanılmadıkça dokunmayın.
