"""Video deposunun kökündeki mes.anime dosyası (site bölüm listesini buradan okur).

Biçim (JSON, yollar depo köküne göre):
  {
    "title": "One Punch Man", "category": "Aksiyon", "poster": "poster.jpg",
    "episodes": [{"path": "s1/ep1", "title": "1. Sezon 1. Bölüm", "subtitles": ["tr", "en"]}]
  }
Bölüm klasörleri sN/epM düzenindedir. Var olan başlıklar ve bilinmeyen alanlar korunur.
"""
import json
import re
import shutil
from pathlib import Path

from .ayar import hata

DOSYA = "mes.anime"
KLASOR = re.compile(r"^s(\d+)/ep(\d+)$")


def _sira(dil):
    return (0 if dil == "tr" else 1 if dil == "en" else 2, dil)


def oku(depo: Path) -> dict:
    yol = depo / DOSYA
    if not yol.exists():
        return {}
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        hata(f"{yol} bozuk JSON: {e}")


def yaz(depo: Path, bilgi: dict):
    """Her bölüm tek satır: elle düzenlemesi ve git diff'i kolay olsun."""
    bas = [f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},"
           for k, v in bilgi.items() if k != "episodes"]
    bol = [f"    {json.dumps(e, ensure_ascii=False)}" for e in bilgi.get("episodes", [])]
    (depo / DOSYA).write_text("{\n" + "\n".join(bas) + '\n  "episodes": [\n' + ",\n".join(bol) + "\n  ]\n}\n",
                              encoding="utf-8")


def bolumler(depo: Path) -> list:
    """Diskteki bölümler: [(sezon, bölüm, 'sN/epM'), ...] sıralı. index.m3u8 olanlar sayılır."""
    bulunan = []
    for m3u8 in depo.glob("s*/ep*/index.m3u8"):
        yol = m3u8.parent.relative_to(depo).as_posix()
        m = KLASOR.match(yol)
        if m:
            bulunan.append((int(m[1]), int(m[2]), yol))
    return sorted(bulunan)


def sonraki_bolum(depo: Path, sezon: int) -> int:
    """Sezondaki en büyük bölüm numarası + 1 (hiç yoksa 1)."""
    return max((b for s, b, _ in bolumler(depo) if s == sezon), default=0) + 1


def guncelle(depo: Path, ad=None, kategori=None, kapak=None, basliklar: dict | None = None) -> dict:
    """Klasörleri tarayıp mes.anime'yi yeniler. basliklar: {'s1/ep1': 'Özel başlık'}"""
    if not depo.is_dir():
        hata(f"{depo} yok. Önce: python3 mes.py klonla {depo.name}")
    bilgi = oku(depo)
    if ad:
        bilgi["title"] = ad
    if kategori:
        bilgi["category"] = kategori
    if kapak:
        kaynak = Path(kapak)
        if kaynak.is_file():                                     # yerel resim -> depoya kopyala
            hedef = depo / f"poster{kaynak.suffix.lower()}"
            if kaynak.resolve() != hedef.resolve():
                shutil.copyfile(kaynak, hedef)
            bilgi["poster"] = hedef.name
        else:
            bilgi["poster"] = kapak                              # URL veya depodaki dosya adı
    if not bilgi.get("title"):
        hata(f"{depo / DOSYA} yok. Yeni anime için: python3 mes.py yeni {depo.name} \"Anime Adı\"")
    bilgi.setdefault("category", "Anime")
    bilgi.setdefault("poster", "")

    eski = {e["path"]: e for e in bilgi.get("episodes", [])}
    yeni_liste, eklenen = [], []
    for s, b, yol in bolumler(depo):
        e = dict(eski.get(yol, {}))
        e["path"] = yol
        e["title"] = (basliklar or {}).get(yol) or e.get("title") or f"{s}. Sezon {b}. Bölüm"
        e["subtitles"] = sorted((f.stem for f in (depo / yol).glob("*.vtt")), key=_sira)
        if "variants" in e:                                      # klasörü silinen kaliteleri çıkar
            e["variants"] = [v for v in e["variants"] if (depo / yol / v.get("path", "") / "index.m3u8").exists()]
            if not e["variants"]:
                del e["variants"]
        yeni_liste.append(e)
        if yol not in eski:
            eklenen.append(yol)
    silinen = [y for y in eski if y not in {e["path"] for e in yeni_liste}]
    bilgi["episodes"] = yeni_liste
    yaz(depo, bilgi)
    print(f"📋 mes.anime: {bilgi['title']}, {len(yeni_liste)} bölüm"
          + (f" | yeni: {', '.join(eklenen)}" if eklenen else "")
          + (f" | silinen: {', '.join(silinen)}" if silinen else ""))
    return bilgi
