"""Altyazı: videodan çıkarma, dışarıdan ekleme, temizleme ve İngilizce -> Türkçe çeviri.

Her bölüm klasöründe altyazılar <dil>.vtt adıyla durur (tr.vtt, en.vtt).
"""
import re
import shutil
import tempfile
import time
from pathlib import Path

from .ayar import calistir
from .video import akislar

RESIM_KODEKLERI = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle", "xsub"}

# ---------- VTT okuma / yazma / temizleme ----------

ZAMAN = re.compile(r"^((?:\d+:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d+:)?\d{2}:\d{2}[.,]\d{3})")
CIZIM = re.compile(r"^\s*m\s+-?\d+(\.\d+)?\s+-?\d+(\.\d+)?(\s+[lbmnsc](\s+-?\d+(\.\d+)?)+)+\s*$", re.I)


def _sn(t):
    p = [float(x) for x in t.replace(",", ".").split(":")]
    while len(p) < 3:
        p.insert(0, 0.0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def _zaman(sn):
    sn = max(0.0, sn)
    return f"{int(sn // 3600):02d}:{int(sn % 3600 // 60):02d}:{sn % 60:06.3f}"


def oku(metin: str) -> list:
    """VTT/SRT metnini [[başlangıç, bitiş, yazı], ...] listesine çevirir."""
    satirlar = []
    for blok in re.split(r"\n\s*\n", metin.replace("\r", "").strip()):
        b = blok.split("\n")
        for i, s in enumerate(b):
            m = ZAMAN.match(s.strip())
            if m:
                satirlar.append([_sn(m[1]), _sn(m[2]), "\n".join(b[i + 1:])])
                break
    return satirlar


def yaz(satirlar: list) -> str:
    parca = ["WEBVTT", ""]
    for b, s, t in satirlar:
        parca += [f"{_zaman(b)} --> {_zaman(s)}", t, ""]
    return "\n".join(parca)


def _temiz_yazi(t):
    t = re.sub(r"\{[^}]*\}", "", t)                       # fansub notları / ASS etiketleri
    t = re.sub(r"\\[Nn]", "\n", t).replace("\\h", " ")
    t = re.sub(r"</?(b|i|u|s|c[^>]*|font[^>]*)>", "", t)
    sat = [re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")]
    return "\n".join(x for x in sat if x and not CIZIM.match(x))


def temizle(satirlar: list, en_kisa=0.25) -> list:
    """Fansub notlarını, vektör çizimlerini ve kare kare tekrarları temizler."""
    sonuc, son = [], {}
    for b, s, t in sorted(satirlar, key=lambda x: (x[0], x[1])):
        t = _temiz_yazi(t)
        if not t:
            continue
        duz = t.replace("\n", " ")
        onceki = son.get(duz)
        if onceki and b <= onceki[1] + 0.15:              # aynı yazının tekrarı -> birleştir
            onceki[1] = max(onceki[1], s)
            continue
        son[duz] = [b, s, t]
        sonuc.append(son[duz])
    return [x for x in sonuc if x[1] - x[0] >= en_kisa]


def dosyayi_temizle(vtt: Path) -> int:
    satirlar = temizle(oku(vtt.read_text(encoding="utf-8", errors="ignore")))
    vtt.write_text(yaz(satirlar), encoding="utf-8")
    return len(satirlar)

# ---------- videodan çıkarma / dışarıdan ekleme ----------


def ekle(kaynak: Path, hedef: Path):
    """Hazır altyazı dosyasını (.srt, .ass, .vtt) temiz VTT olarak hedefe yazar."""
    calistir(["ffmpeg", "-v", "error", "-y", "-i", kaynak, hedef])
    dosyayi_temizle(hedef)


def cikar(video: Path, klasor: Path) -> str | None:
    """Videodaki metin altyazıyı (İngilizce öncelikli) klasor/en.vtt olarak çıkarır.

    Döndürür: yazılan dil ("en") veya None. Resim altyazıyı .sup olarak videonun yanına kaydeder.
    """
    liste = akislar(video, "s")
    if not liste:
        print("⚠️  Videoda gömülü altyazı yok.")
        return None
    metin = [(i, s) for i, s in enumerate(liste) if s.get("codec_name") not in RESIM_KODEKLERI]
    if not metin:
        sup = video.with_suffix(".sup")
        calistir(["ffmpeg", "-v", "error", "-y", "-i", video, "-map", "0:s:0", "-c", "copy", sup], sessiz=True)
        print(f"⚠️  Altyazı resim formatında, metne çevrilemez. OCR için kaydedildi: {sup}")
        print("    .srt bulursan: --altyazi tr:dosya.srt")
        return None
    ing = [x for x in metin if x[1].get("tags", {}).get("language", "").lower() in ("eng", "en")]
    i = (ing or metin)[0][0]
    hedef = klasor / "en.vtt"
    calistir(["ffmpeg", "-v", "error", "-y", "-i", video, "-map", f"0:s:{i}", hedef])
    n = dosyayi_temizle(hedef)
    print(f"📝 en.vtt: {n} satır")
    return "en"

# ---------- çeviri ----------


def ceviri_var_mi() -> bool:
    try:
        import deep_translator  # noqa: F401
        return True
    except ImportError:
        return False


def _toplu_cevir(cevirmen, yazilar):
    """Satırları numaralayıp tek istekte çevirir (hız + bağlam)."""
    giden = "\n".join(f"[{i}] {t.replace(chr(10), ' / ')}" for i, t in enumerate(yazilar))
    gelen = {}
    for s in (cevirmen.translate(giden) or "").split("\n"):
        m = re.match(r"\s*\[(\d+)\]\s*(.*)", s)
        if m:
            gelen[int(m[1])] = m[2].strip().replace(" / ", "\n")
    return [gelen.get(i) or cevirmen.translate(t) or t for i, t in enumerate(yazilar)]


def cevir(en_vtt: Path, tr_vtt: Path):
    """en.vtt -> tr.vtt makine çevirisi (pip install deep-translator)."""
    from deep_translator import GoogleTranslator
    cevirmen = GoogleTranslator(source="en", target="tr")
    satirlar = temizle(oku(en_vtt.read_text(encoding="utf-8")))
    essiz = list(dict.fromkeys(t for _, _, t in satirlar))
    karsilik = {}
    for i in range(0, len(essiz), 40):
        grup = essiz[i:i + 40]
        for deneme in range(4):
            try:
                karsilik.update(zip(grup, _toplu_cevir(cevirmen, grup)))
                break
            except Exception as e:
                if deneme == 3:
                    raise RuntimeError(f"çeviri başarısız ({type(e).__name__})") from e
                print(f"  tekrar deneniyor ({type(e).__name__})")
                time.sleep(5 * (deneme + 1))
        print(f"  🇹🇷 çeviri {min(i + 40, len(essiz))}/{len(essiz)}")
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".vtt", encoding="utf-8") as f:
        f.write(yaz([[b, s, karsilik.get(t, t)] for b, s, t in satirlar]))
    shutil.move(f.name, tr_vtt)


def hazirla(video: Path, klasor: Path, harici: list[str] | None = None, turkce: bool = True):
    """Bir bölümün altyazılarını hazırlar:
    1) --altyazi dil:dosya ile verilenler, 2) yoksa videodan İngilizce, 3) Türkçe yoksa çeviri.
    """
    for h in harici or []:
        dil, yol = h.split(":", 1) if ":" in h else ("tr", h)
        ekle(Path(yol), klasor / f"{dil}.vtt")
        print(f"📝 {dil}.vtt eklendi ({yol})")
    if not (klasor / "en.vtt").exists():
        cikar(video, klasor)
    if turkce and not (klasor / "tr.vtt").exists() and (klasor / "en.vtt").exists():
        if ceviri_var_mi():
            try:
                cevir(klasor / "en.vtt", klasor / "tr.vtt")
            except RuntimeError as e:
                print(f"⚠️  Türkçe altyazı yapılamadı: {e}. Sonra: python3 mes.py altyazi cevir <depo>")
        else:
            print("⚠️  Türkçe çeviri atlandı: pip install deep-translator")
