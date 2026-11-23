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


def gizli_anahtar() -> str:
    anahtar = os.environ.get("VIDEO_SECRET_KEY")
    if not anahtar:
        hata("VIDEO_SECRET_KEY tanımlı değil! Önce: source ~/.bashrc")
    return anahtar
