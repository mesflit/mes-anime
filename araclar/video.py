"""Videoyu AES-128 şifreli HLS'e (index.m3u8 + seg_XXX.ts) çevirir.

Anahtar = SHA-256(VIDEO_SECRET_KEY)'in ilk 16 baytı. Site (index.html) aynı anahtarı
tarayıcıda üretir; bu türetmeyi değiştirirsen eski bölümler oynatılamaz.
"""
import hashlib
import json
import tempfile
from pathlib import Path

from .ayar import calistir, cikti, gizli_anahtar

PARCA_SURESI = 6  # saniye


def aes_anahtari(gizli: str) -> bytes:
    return hashlib.sha256(gizli.encode("utf-8")).digest()[:16]


def akislar(girdi: Path, tur: str) -> list:
    """ffprobe ile 'a' (ses) veya 's' (altyazı) akışlarını listeler."""
    j = cikti(["ffprobe", "-v", "error", "-select_streams", tur, "-show_entries",
               "stream=codec_name:stream_tags=language,title", "-of", "json", girdi])
    return json.loads(j or "{}").get("streams", [])


def ses_sec(girdi: Path) -> int:
    """Japonca ses varsa onu, yoksa ilk sesi seçer (ses sırası numarası)."""
    for i, s in enumerate(akislar(girdi, "a")):
        if s.get("tags", {}).get("language", "").lower() in ("jpn", "ja", "jp"):
            return i
    return 0


def hls_yap(girdi: Path, cikis: Path, hiz: str = "veryfast"):
    """girdi videosunu cikis klasörüne şifreli HLS olarak yazar."""
    cikis.mkdir(parents=True, exist_ok=True)
    for eski in cikis.glob("seg_*.ts"):
        eski.unlink()
    ses = ses_sec(girdi)
    with tempfile.TemporaryDirectory() as tmp:
        anahtar = Path(tmp) / "enc.key"
        bilgi = Path(tmp) / "keyinfo.txt"
        anahtar.write_bytes(aes_anahtari(gizli_anahtar()))
        bilgi.write_text(f"enc.key\n{anahtar}\n")  # oynatma listesine "enc.key" yazılır, dosya depoya girmez
        calistir([
            "ffmpeg", "-v", "warning", "-stats", "-y", "-i", girdi,
            "-map", "0:v:0", "-map", f"0:a:{ses}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", hiz,
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-hls_time", str(PARCA_SURESI), "-hls_playlist_type", "vod",
            "-hls_key_info_file", bilgi,
            "-hls_segment_filename", cikis / "seg_%03d.ts",
            cikis / "index.m3u8",
        ])
