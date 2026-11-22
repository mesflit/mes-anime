# MesAnime

GitHub Pages üzerinde çalışan, şifreli ve parçalı (AES-256-CBC) video oynatma sistemi.

## İlk Kurulum

    pkg install -y git gh openssl-tool python
    export VIDEO_SECRET_KEY=$(openssl rand -hex 32)
    echo "export VIDEO_SECRET_KEY=$VIDEO_SECRET_KEY" >> ~/.bashrc
    gh secret set VIDEO_SECRET_KEY -b "$VIDEO_SECRET_KEY"

GitHub Pages Ayarı: Settings -> Pages -> Source -> GitHub Actions

## Yeni Bölüm Ekleme

    python3 scripts/pack.py /sdcard/Download/bolum1.mp4 "/videos/opm/season1/bolum1" "OnePunchMan S1 B1" "Aksiyon"

## Yayınlama

    git add videos/ data/ && git commit -m "feat: yeni bolum" && git push
