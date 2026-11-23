#!/usr/bin/env python3
"""mes-anime yönetim aracı. Tüm işler tek komutla:

  Yeni anime (GitHub'da depo açar, mes.anime oluşturur, siteye ekler):
    python3 mes.py yeni deathnote "Death Note" --kategori Gerilim --kapak kapak.jpg

  Bölüm ekle (dosya ya da klasör; numara kendiliğinden devam eder, her bölüm ayrı gönderilir):
    python3 mes.py ekle deathnote /sdcard/Download/dn01.mkv
    python3 mes.py ekle deathnote /sdcard/Download/deathnote/          # klasördeki hepsi
    python3 mes.py ekle opm bolum.mkv --sezon 3 --bolum 13 --baslik "Final"

  Diğer:
    python3 mes.py guncelle opm          # klasörlere bakıp mes.anime'yi yenile ve gönder
    python3 mes.py klonla opm            # depoyu videolar olmadan ../opm'a indir
    python3 mes.py altyazi temizle opm   # tüm .vtt'leri temizle
    python3 mes.py altyazi cevir opm     # tr.vtt olmayan bölümleri çevir

Gönderme (git push) istemezsen her komuta --gonderme ekle.
"""
import argparse
import re
import sys
from pathlib import Path

from araclar import altyazi, depo, katalog, video
from araclar.ayar import VIDEO_UZANTILARI, gizli_anahtar, hata


def dogal_sira(p: Path):
    """bolum2 < bolum10 olacak şekilde sıralama anahtarı."""
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", p.name)]


def videolari_bul(yol: Path) -> list:
    if yol.is_file():
        return [yol]
    if yol.is_dir():
        return sorted((f for f in yol.iterdir() if f.suffix.lower() in VIDEO_UZANTILARI), key=dogal_sira)
    hata(f"{yol} bulunamadı")


# ---------- komutlar ----------

def k_yeni(a):
    depo.olustur(a.depo)
    yol = depo.hazirla(a.depo)
    katalog.guncelle(yol, a.ad, a.kategori or "Anime", a.kapak)
    if a.gonder:
        depo.gonder(yol, f"feat: {a.ad} eklendi")
    depo.siteye_ekle(a.depo, a.gonder)
    print(f"\n🎉 Hazır. Bölüm eklemek için:\n   python3 mes.py ekle {a.depo} <video veya klasör>")


def k_ekle(a):
    gizli_anahtar()                                   # anahtar yoksa en başta dur
    videolar = videolari_bul(Path(a.kaynak))
    if not videolar:
        hata(f"{a.kaynak} içinde video yok")
    if len(videolar) > 1 and (a.baslik or a.altyazi):
        hata("--baslik ve --altyazi sadece tek dosya eklerken kullanılabilir")
    yol = depo.hazirla(a.depo)
    if not katalog.oku(yol).get("title"):
        hata(f"{a.depo} için mes.anime yok. Önce: python3 mes.py yeni {a.depo} \"Anime Adı\"")
    no = a.bolum or katalog.sonraki_bolum(yol, a.sezon)

    print(f"🎬 {len(videolar)} video -> {a.depo} {a.sezon}. sezon, {no}. bölümden itibaren")
    for v in videolar:
        print(f"   {a.sezon}x{no:02d}  {v.name}")
        no += 1
    no -= len(videolar)

    for i, v in enumerate(videolar, 1):
        klasor = f"s{a.sezon}/ep{no}"
        print(f"\n━━ [{i}/{len(videolar)}] {klasor} ← {v.name}")
        video.hls_yap(v, yol / klasor, a.hiz)
        altyazi.hazirla(v, yol / klasor, a.altyazi, turkce=not a.ceviri_yok)
        katalog.guncelle(yol, basliklar={klasor: a.baslik} if a.baslik else None)
        if a.gonder:
            depo.gonder(yol, f"feat: S{a.sezon} B{no}")
        no += 1

    if not depo.sitede_mi(a.depo):
        print(f"\n⚠️  {a.depo} sitede listelenmiyor. Eklemek için: python3 mes.py yeni {a.depo} \"Ad\"")
    print("\n🎉 Bitti." + (" Birkaç dakika içinde sitede görünür." if a.gonder else " (gönderilmedi)"))


def k_guncelle(a):
    yol = depo.hazirla(a.depo)
    katalog.guncelle(yol)
    if a.gonder:
        depo.gonder(yol, "chore: mes.anime güncellendi")


def k_klonla(a):
    depo.klonla(a.depo)


def k_altyazi(a):
    yol = depo.hazirla(a.depo)
    klasorler = sorted(p.parent for p in yol.glob("s*/ep*/index.m3u8"))
    for k in klasorler:
        if a.islem == "temizle":
            for f in k.glob("*.vtt"):
                print(f"🧹 {f.relative_to(yol)}: {altyazi.dosyayi_temizle(f)} satır")
        elif (k / "en.vtt").exists() and (a.hepsi or not (k / "tr.vtt").exists()):
            print(f"🇹🇷 {k.relative_to(yol)}")
            try:
                altyazi.cevir(k / "en.vtt", k / "tr.vtt")
            except RuntimeError as e:
                print(f"⚠️  {e}, atlandı")
    katalog.guncelle(yol)
    if a.gonder:
        depo.gonder(yol, f"chore: altyazılar ({a.islem})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest="komut", required=True, metavar="komut")

    def komut(ad, fonk, yardim):
        k = alt.add_parser(ad, help=yardim)
        k.add_argument("--gonderme", dest="gonder", action="store_false", help="git push yapma")
        k.set_defaults(fonk=fonk)
        return k

    k = komut("yeni", k_yeni, "yeni anime: depo aç, mes.anime oluştur, siteye ekle")
    k.add_argument("depo", help="depo adı (sitedeki kimlik olur, sonradan değiştirme!) örn: deathnote")
    k.add_argument("ad", help='anime adı, örn: "Death Note"')
    k.add_argument("--kategori", help="örn: Aksiyon")
    k.add_argument("--kapak", help="kapak resmi (yerel dosya) veya URL")

    k = komut("ekle", k_ekle, "video(lar)ı şifreleyip bölüm olarak ekle")
    k.add_argument("depo")
    k.add_argument("kaynak", help="video dosyası veya videoların olduğu klasör")
    k.add_argument("--sezon", type=int, default=1, help="sezon numarası (varsayılan 1)")
    k.add_argument("--bolum", type=int, help="ilk bölüm numarası (varsayılan: sezonun son bölümü + 1)")
    k.add_argument("--baslik", help="bölüm başlığı (varsayılan: N. Sezon M. Bölüm)")
    k.add_argument("--altyazi", action="append", help="hazır altyazı, örn: tr:altyazi.srt (tekrar verilebilir)")
    k.add_argument("--ceviri-yok", action="store_true", help="İngilizceden Türkçe çeviri yapma")
    k.add_argument("--hiz", default="veryfast", help="ffmpeg preset: ultrafast/veryfast/medium")

    k = komut("guncelle", k_guncelle, "klasörlere bakıp mes.anime'yi yenile")
    k.add_argument("depo")

    k = komut("klonla", k_klonla, "depoyu videolar olmadan ../<depo>'ya indir")
    k.add_argument("depo")

    k = komut("altyazi", k_altyazi, "altyazı temizle / çevir")
    k.add_argument("islem", choices=["temizle", "cevir"])
    k.add_argument("depo")
    k.add_argument("--hepsi", action="store_true", help="cevir: var olan tr.vtt'lerin de üzerine yaz")

    a = p.parse_args()
    try:
        a.fonk(a)
    except KeyboardInterrupt:
        sys.exit("\n⛔ Durduruldu. Yarım kalan bölümü tekrar eklemek için aynı komutu --bolum ile çalıştır.")


if __name__ == "__main__":
    main()
