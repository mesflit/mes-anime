# MesAnime

GitHub Pages üzerinde çalışan, şifreli ve parçalı (AES-128 HLS) video oynatma sistemi.
Videolar ayrı depolarda (ör. `mesflit/opm`) durur, site `data/animes.json` üzerinden okur.

## Özellikler

- Türkçe altyazı (varsayılan), İngilizce yedek; seçilen dil hatırlanır
- Kaldığın yerden devam et, "İzlemeye Devam Et" satırı, izlenen bölümlerde ✓ işareti
- Sezon sekmeleri, otomatik sonraki bölüm, `Shift+N` / `Shift+P` kısayolları
- Paylaşılabilir bölüm linkleri (`#/izle/opm/s1-ep3`), sayfa yenilenince bölüm kaybolmaz

## İlk Kurulum

    pkg install -y git gh openssl-tool python ffmpeg
    export VIDEO_SECRET_KEY=$(openssl rand -hex 32)
    echo "export VIDEO_SECRET_KEY=$VIDEO_SECRET_KEY" >> ~/.bashrc
    gh secret set VIDEO_SECRET_KEY -b "$VIDEO_SECRET_KEY"

GitHub Pages Ayarı: Settings -> Pages -> Source -> GitHub Actions

## Video deposunu videolar OLMADAN klonlama

Video deposu (opm) 8 GB'tan büyük. Yeni bölüm eklemek için tamamını indirmene gerek yok:

    git clone https://github.com/mesflit/mes-anime.git
    cd mes-anime
    bash scripts/hafif_klon.sh opm      # ../opm klasörüne sadece m3u8/vtt iner (~1-2 MB)

Zaten tam klonun varsa aynı komut `.ts` dosyalarını diskten kaldırır.

## Yeni Bölüm Ekleme

    python3 scripts/pack.py /sdcard/Download/bolum.mkv opm s2/ep13 \
        --anime "One Punch Man" --title "2. Sezon 13. Bölüm" --extract-sub --tr

- `--extract-sub`: MKV içindeki altyazıyı çıkarır ve temizler (en.vtt)
- `--tr`: İngilizce altyazıyı otomatik Türkçeye çevirir (`pip install deep-translator`)
- `--sub tr:altyazi.srt`: Hazır Türkçe altyazın varsa onu ekler

## Yayınlama

    cd ../opm && git add --sparse -A && git commit -m "feat: yeni bolum" && git push
    git sparse-checkout reapply          # yüklenen .ts dosyalarını diskten siler
    cd ../mes-anime && git add data/ && git commit -m "feat: yeni bolum" && git push

## Bölümleri otomatik ekleme (elle animes.json yazmaya gerek yok)

Video deposuna `sN/epM/index.m3u8` (+ `tr.vtt`, `en.vtt`) klasörlerini push etmen yeterli.
Push edildiği anda `Bölümleri Senkronize Et` workflow'u çalışır, yeni bölümleri
`data/animes.json`'a ekler ve siteyi yeniden yayınlar. (Zamanlanmış çalışma yok.)
Elle çalıştırmak için: GitHub -> Actions -> "Bölümleri Senkronize Et" -> Run workflow.

### Push edilince güncelleme kurulumu (her video deposu için bir kere)

1. Token oluştur: GitHub -> Settings -> Developer settings -> Personal access tokens ->
   Fine-grained tokens -> Generate new token
   - Repository access: Only select repositories -> `mes-anime`
   - Permissions -> Contents: **Read and write**
2. Video deposunda (ör. opm): Settings -> Secrets and variables -> Actions -> New repository secret
   - Name: `MES_ANIME_TOKEN`, Secret: oluşturduğun token
3. `ornek/bildir.yml` dosyasını video deposuna `.github/workflows/bildir.yml` olarak kopyala:

       mkdir -p ../opm/.github/workflows
       cp ornek/bildir.yml ../opm/.github/workflows/
       cd ../opm && git add --sparse .github && git commit -m "ci: mes-anime'ye haber ver" && git push

Bu push'tan itibaren opm'a her push'ta site kendiliğinden güncellenir.

### Elle çalıştırma (hafif klon yeterli)

    python3 scripts/senkron.py          # tüm animeler
    python3 scripts/senkron.py opm      # sadece opm

Yeni anime eklemek için (bir kere; sonra bölümleri hep kendisi bulur, video deposuna da bildir.yml ekle):

    bash scripts/hafif_klon.sh yeni-repo
    python3 scripts/senkron.py yeni-repo --anime "Anime Adı" --category "Aksiyon" --poster data/kapak.jpg

- Var olan bölüm başlıkları korunur, yenilere "N. Sezon M. Bölüm" verilir (istersen sonradan elle değiştir).
- Bölüm sırası sezon ve bölüm numarasına göre otomatik dizilir.

## Altyazı araçları

    python3 scripts/altyazi.py temizle opm   # fansub notlarını/çöp satırları temizler
    python3 scripts/altyazi.py cevir opm     # tr.vtt olmayan bölümleri çevirir
    python3 scripts/altyazi.py kaydet opm    # bulunan tüm .vtt'leri animes.json'a yazar
