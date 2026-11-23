"""Bölümlere düşük kaliteli kopya (ör. 480p) ekler. Orijinal dosyalara DOKUNMAZ.

Bir bölüm için:
  1. Orijinal şifreli parçalar indirilir (diskte varsa oradan okunur)
  2. ffmpeg aynı anahtarla çözer, 480p'ye küçültür, aynı anahtarla şifreler
  3. Sonuç <bölüm>/480p/ klasörüne yazılır, mes.anime'ye "variants" olarak eklenir

Site, bölümde "variants" varsa kalite menüsü gösterir ve internet yavaşsa kendiliğinden düşer.
Bu iş ağırdır; normalde GitHub Actions'ta çalışır (.github/workflows/kalite.yml).
"""
import json
import re
import shutil
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .ayar import KULLANICI, calistir, cikti, gizli_anahtar
from .video import aes_anahtari


def _parcalar(m3u8: Path):
    """[(dosya_adı, süre), ...]"""
    sure, sonuc = 0.0, []
    for s in m3u8.read_text(encoding="utf-8").splitlines():
        s = s.strip()
        if s.startswith("#EXTINF:"):
            sure = float(s[8:].split(",")[0] or 0)
        elif s and not s.startswith("#"):
            sonuc.append((s, sure))
    return sonuc


def _indir(url: str, hedef: Path):
    for deneme in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(hedef, "wb") as f:
                shutil.copyfileobj(r, f)
            return
        except Exception:
            if deneme == 3:
                raise


def _bant(klasor: Path, parcalar) -> int:
    """Ortalama bit hızı (bit/sn): parça boyutları / toplam süre."""
    sure = sum(s for _, s in parcalar) or 1
    return int(sum((klasor / ad).stat().st_size for ad, _ in parcalar) * 8 / sure)


def _cozunurluk(m3u8: Path) -> tuple[int, int]:
    j = cikti(["ffprobe", "-v", "error", "-allowed_extensions", "ALL", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "json", m3u8])
    s = (json.loads(j or "{}").get("streams") or [{}])[0]
    return int(s.get("width") or 0), int(s.get("height") or 0)


def varyant_yap(depo: Path, bolum: str, yukseklik: int = 480, hiz: str = "veryfast") -> dict | None:
    """depo/bolum için <yukseklik>p kopyası üretir. Döndürür: mes.anime'ye yazılacak bilgi
    {"orijinal": {...}, "varyant": {...}} ya da orijinal zaten küçükse None."""
    kaynak = depo / bolum
    ad = f"{yukseklik}p"
    parcalar = _parcalar(kaynak / "index.m3u8")
    anahtar = aes_anahtari(gizli_anahtar())
    url = f"https://raw.githubusercontent.com/{KULLANICI}/{depo.name}/main/{bolum}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Orijinali geçici klasöre topla (oynatma listesi + parçalar + anahtar)
        shutil.copyfile(kaynak / "index.m3u8", tmp / "index.m3u8")
        (tmp / "enc.key").write_bytes(anahtar)

        def getir(dosya):
            yerel = kaynak / dosya
            if yerel.exists():
                shutil.copyfile(yerel, tmp / dosya)
            else:
                _indir(f"{url}/{dosya}", tmp / dosya)
        print(f"⬇️  {bolum}: {len(parcalar)} parça indiriliyor")
        with ThreadPoolExecutor(8) as havuz:
            list(havuz.map(getir, [d for d, _ in parcalar]))

        g, y = _cozunurluk(tmp / "index.m3u8")
        orijinal = {"bandwidth": _bant(tmp, parcalar), "resolution": f"{g}x{y}" if y else ""}
        if y and y <= yukseklik:
            print(f"ℹ️  {bolum}: orijinal zaten {y}p, {ad} gereksiz")
            return None

        cikis = kaynak / ad
        if cikis.exists():
            shutil.rmtree(cikis)
        cikis.mkdir(parents=True)
        (tmp / "keyinfo.txt").write_text(f"enc.key\n{tmp / 'enc.key'}\n")
        calistir([
            "ffmpeg", "-v", "warning", "-stats", "-y", "-allowed_extensions", "ALL", "-i", tmp / "index.m3u8",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", f"scale=-2:{yukseklik}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", hiz,
            "-crf", "26", "-maxrate", "1200k", "-bufsize", "2400k",
            "-c:a", "aac", "-b:a", "96k", "-ac", "2",
            "-hls_time", "6", "-hls_playlist_type", "vod",
            "-hls_key_info_file", tmp / "keyinfo.txt",
            "-hls_segment_filename", cikis / "seg_%03d.ts", cikis / "index.m3u8",
        ])

    yeni = _parcalar(cikis / "index.m3u8")
    genislik = round(g * yukseklik / y / 2) * 2 if y else 0   # ffmpeg scale=-2 ile aynı yuvarlama
    varyant = {"name": ad, "path": ad, "bandwidth": _bant(cikis, yeni),
               "resolution": f"{genislik}x{yukseklik}" if genislik else ""}
    print(f"✅ {bolum}/{ad}: {varyant['bandwidth'] // 1000} kbps (orijinal {orijinal['bandwidth'] // 1000} kbps)")
    return {"orijinal": orijinal, "varyant": varyant}


def eksik_bolumler(depo: Path, yukseklik: int = 480) -> list[str]:
    """mes.anime'de <yukseklik>p kopyası olmayan bölümler (sırayla)."""
    from . import katalog
    ad = f"{yukseklik}p"
    sonuc = []
    for e in katalog.oku(depo).get("episodes", []):
        if e.get("no_variants"):
            continue
        if not any(v.get("name") == ad for v in e.get("variants", [])) or not (depo / e["path"] / ad / "index.m3u8").exists():
            sonuc.append(e["path"])
    return sonuc


def kaydet(depo: Path, bolum: str, sonuc: dict | None):
    """Varyant bilgisini mes.anime'ye yazar."""
    from . import katalog
    bilgi = katalog.oku(depo)
    for e in bilgi.get("episodes", []):
        if e["path"] != bolum:
            continue
        if sonuc is None:                       # orijinal zaten küçük: bir daha deneme
            e["no_variants"] = True
            break
        e["bandwidth"] = sonuc["orijinal"]["bandwidth"]
        if sonuc["orijinal"]["resolution"]:
            e["resolution"] = sonuc["orijinal"]["resolution"]
        e["variants"] = [v for v in e.get("variants", []) if v.get("name") != sonuc["varyant"]["name"]]
        e["variants"].append(sonuc["varyant"])
        e["variants"].sort(key=lambda v: -int(re.sub(r"\D", "", v["name"]) or 0))
    katalog.yaz(depo, bilgi)
