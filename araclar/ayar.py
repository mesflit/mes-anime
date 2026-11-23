"""Ortak ayarlar ve yardımcılar."""
import os
import subprocess
import sys
from pathlib import Path

KULLANICI = os.environ.get("GH_USER", "mesflit")        # GitHub kullanıcı adı
KOK = Path(__file__).resolve().parent.parent              # mes-anime klasörü
DEPOLAR_TXT = KOK / "data" / "depolar.txt"
DILLER = {"tr": "Türkçe", "en": "İngilizce", "jp": "Japonca", "ja": "Japonca"}
VIDEO_UZANTILARI = {".mkv", ".mp4", ".avi", ".webm", ".mov", ".m4v"}
SITE = os.environ.get("MES_SITE", f"https://{KULLANICI}.github.io/mes-anime/")   # yayındaki site
ANAHTAR_DOSYASI = Path.home() / ".mes-anime-anahtar"     # anahtarın bu cihazdaki kopyası


def depo_yolu(depo: str) -> Path:
    """Video deposu mes-anime'nin yanında durur: ../<depo>"""
    return KOK.parent / depo


def calistir(komut, sessiz=False, **kw):
    """Komutu çalıştırır, hata olursa durur."""
    if not sessiz:
        print("▶", " ".join(str(k) for k in komut))
    return subprocess.run([str(k) for k in komut], check=True, **kw)


def cikti(komut) -> str:
    """Komutun çıktısını döndürür (hata olursa boş)."""
    r = subprocess.run([str(k) for k in komut], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def hata(mesaj: str):
    sys.exit(f"❌ {mesaj}")


def anahtari_siteden_al() -> str:
    """Yayındaki sitenin index.html'inden anahtarı okur.

    deploy.yml yayınlarken GitHub secret'ını (VIDEO_SECRET_KEY) sayfaya yazar; videoları oynatan
    anahtar budur. Böylece anahtar hiçbir cihazda yoksa bile kaybolmaz.
    """
    import re
    import urllib.request
    try:
        with urllib.request.urlopen(SITE, timeout=30) as r:
            sayfa = r.read().decode("utf-8", "ignore")
    except Exception as e:
        hata(f"Site okunamadı ({SITE}): {e}\n   Site başka adresteyse: MES_SITE=https://adres/ python3 mes.py anahtar")
    m = re.search(r'const SECRET_KEY = "([^"]*)"', sayfa)
    if not m:
        hata(f"{SITE} içinde anahtar bulunamadı. Adres doğru mu? (MES_SITE ile değiştirilebilir)")
    if not m[1] or m[1] == "__VIDEO_SECRET_KEY__":
        hata("Sitede anahtar yok: GitHub'da VIDEO_SECRET_KEY secret'ı tanımlanmamış.")
    return m[1]


def anahtari_kaydet(anahtar: str):
    ANAHTAR_DOSYASI.write_text(anahtar + "\n", encoding="utf-8")
    try:
        ANAHTAR_DOSYASI.chmod(0o600)
    except OSError:
        pass


def gizli_anahtar() -> str:
    """Sırayla: VIDEO_SECRET_KEY ortam değişkeni -> ~/.mes-anime-anahtar -> siteden al ve kaydet."""
    anahtar = os.environ.get("VIDEO_SECRET_KEY", "").strip()
    if not anahtar and ANAHTAR_DOSYASI.exists():
        anahtar = ANAHTAR_DOSYASI.read_text(encoding="utf-8").strip()
    if not anahtar:
        print(f"🔑 Anahtar bu cihazda yok, siteden alınıyor ({SITE})...")
        anahtar = anahtari_siteden_al()
        anahtari_kaydet(anahtar)
        print(f"🔑 Kaydedildi: {ANAHTAR_DOSYASI}")
    return anahtar
