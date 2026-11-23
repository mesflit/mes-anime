#!/usr/bin/env bash
# Video deposunu videolar (.ts parçaları) OLMADAN klonlar.
# Sadece index.m3u8 ve .vtt gibi küçük dosyalar iner (8 GB yerine ~1-2 MB).
#
# Kullanım (mes-anime klasöründeyken):
#   bash scripts/hafif_klon.sh opm
#
# Yeni bölüm ekledikten sonra (.ts dosyaları sparse dışında olduğu için --sparse şart):
#   cd ../opm && git add --sparse -A && git commit -m "feat: yeni bolum" && git push
#   git sparse-checkout reapply   # yüklenen .ts dosyalarını diskten siler
set -euo pipefail
REPO="${1:-opm}"
USER_NAME="${GH_USER:-mesflit}"
DEST="../$REPO"

if [ -d "$DEST/.git" ]; then
  echo "ℹ️  $DEST zaten var; videolar diskten kaldırılıyor (sparse moda geçiliyor)..."
  cd "$DEST"
  git config remote.origin.promisor true
  git config remote.origin.partialclonefilter blob:none
  git sparse-checkout set --no-cone '/*' '!*.ts'
else
  git clone --filter=blob:none --no-checkout "https://github.com/$USER_NAME/$REPO.git" "$DEST"
  cd "$DEST"
  git sparse-checkout set --no-cone '/*' '!*.ts'
  git checkout
fi
# git add yaparken sparse uyarısını sustur
git config advice.updateSparsePath false
echo "✅ Hazır: $(du -sh .git | cut -f1) (.ts videolar indirilmedi)"
