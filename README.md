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
`Bölümleri Senkronize Et` workflow'u her saat başı video depolarını tarar, yeni bölümleri
`data/animes.json`'a ekler ve siteyi yeniden yayınlar. Beklemek istemezsen:
GitHub -> Actions -> "Bölümleri Senkronize Et" -> Run workflow.

Telefondan/elle çalıştırmak için (hafif klon yeterli):

    python3 scripts/senkron.py          # tüm animeler
    python3 scripts/senkron.py opm      # sadece opm

Yeni anime eklemek için (bir kere; sonra bölümleri hep kendisi bulur):

    bash scripts/hafif_klon.sh yeni-repo
    python3 scripts/senkron.py yeni-repo --anime "Anime Adı" --category "Aksiyon" --poster data/kapak.jpg

- Var olan bölüm başlıkları korunur, yenilere "N. Sezon M. Bölüm" verilir (istersen sonradan elle değiştir).
- Bölüm sırası sezon ve bölüm numarasına göre otomatik dizilir.

### Anında güncelleme (isteğe bağlı)

Saat başını beklemeden, video deposu push edildiği an çalışsın istersen video deposuna
`.github/workflows/bildir.yml` ekle ve `MES_ANIME_TOKEN` adında (mes-anime'ye "Contents: write"
yetkili, fine-grained) bir token'ı o deponun secret'ı olarak kaydet:

    on: { push: { branches: [main] } }
    jobs:
      bildir:
        runs-on: ubuntu-latest
        steps:
          - run: gh api repos/mesflit/mes-anime/dispatches -f event_type=yeni-bolum
            env: { GH_TOKEN: "${{ secrets.MES_ANIME_TOKEN }}" }

## Altyazı araçları

    python3 scripts/altyazi.py temizle opm   # fansub notlarını/çöp satırları temizler
    python3 scripts/altyazi.py cevir opm     # tr.vtt olmayan bölümleri çevirir
    python3 scripts/altyazi.py kaydet opm    # bulunan tüm .vtt'leri animes.json'a yazar
