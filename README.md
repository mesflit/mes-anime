# MesAnime

GitHub Pages üzerinde çalışan, şifreli ve parçalı (AES-128 HLS) video oynatma sistemi.
Videolar ayrı depolarda (ör. `mesflit/opm`) durur. Her video deposunun kökünde bir `mes.anime`
dosyası vardır; site hangi depolara bakacağını `data/depolar.txt`'den öğrenir.

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

## Nasıl çalışır?

- `data/depolar.txt` (mes-anime): sadece depo yolları, her satıra bir tane:

      mesflit/opm

- `mes.anime` (her video deposunun kökünde): anime adı, kapak ve bölümler.

      {
        "title": "One Punch Man",
        "category": "Aksiyon",
        "poster": "poster.jpg",
        "episodes": [
          {"path": "s1/ep1", "title": "1. Sezon 1. Bölüm", "subtitles": ["tr", "en"]}
        ]
      }

  `path` bölüm klasörüdür (içinde `index.m3u8` ve `tr.vtt`/`en.vtt`). Başlıkları elle
  değiştirebilirsin. Site açılırken bu dosyayı doğrudan depodan okur, mes-anime'de bir şey
  değiştirmeye gerek yoktur.

`mes.anime`'yi elle yazmana gerek yok, klasörlere bakıp kendisi oluşturur:

    python3 scripts/mesanime.py opm

Yeni klasörleri ekler, var olan başlıklara dokunmaz, yenilere "N. Sezon M. Bölüm" verir.

## Yeni Bölüm Ekleme

    python3 scripts/pack.py /sdcard/Download/bolum.mkv opm s2/ep13 --extract-sub --tr
    cd ../opm && git add --sparse -A && git commit -m "feat: yeni bolum" && git push
    git sparse-checkout reapply          # yüklenen .ts dosyalarını diskten siler

`pack.py` `mes.anime`'yi kendisi günceller. Push ettikten birkaç dakika sonra bölüm sitede
görünür (mes-anime'ye push gerekmez).

- `--title "Özel Başlık"`: bölüme kendi başlığını ver (boşsa "N. Sezon M. Bölüm")
- `--extract-sub`: MKV içindeki altyazıyı çıkarır ve temizler (en.vtt)
- `--tr`: İngilizce altyazıyı otomatik Türkçeye çevirir (`pip install deep-translator`)
- `--sub tr:altyazi.srt`: Hazır Türkçe altyazın varsa onu ekler

Bölüm klasörlerini başka yolla (ör. hazır dosya kopyalayarak) eklediysen push etmeden önce:

    python3 scripts/mesanime.py opm

## Yeni Anime Ekleme

    bash scripts/hafif_klon.sh yeni-repo
    python3 scripts/mesanime.py yeni-repo --anime "Anime Adı" --category "Aksiyon" --poster kapak.jpg
    cd ../yeni-repo && git add --sparse -A && git commit -m "feat: mes.anime" && git push

Sonra mes-anime'de `data/depolar.txt`'ye `mesflit/yeni-repo` satırını ekleyip push et. Bu kadar.

## Altyazı araçları

    python3 scripts/altyazi.py temizle opm   # fansub notlarını/çöp satırları temizler
    python3 scripts/altyazi.py cevir opm     # tr.vtt olmayan bölümleri çevirir
    python3 scripts/altyazi.py kaydet opm    # bulunan tüm .vtt'leri mes.anime'ye yazar
