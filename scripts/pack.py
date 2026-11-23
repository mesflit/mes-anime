import os, sys, json, hashlib, tempfile, subprocess, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import subs  # noqa: E402


def clean_vtt(path: Path):
    cues = subs.clean_cues(subs.parse_vtt(path.read_text(encoding="utf-8", errors="ignore")))
    path.write_text(subs.write_vtt(cues), encoding="utf-8")

def get_aes_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()[:16]

def run(cmd):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True)

def pack_hls(args):
    secret = os.environ.get("VIDEO_SECRET_KEY")
    if not secret:
        sys.exit("HATA: VIDEO_SECRET_KEY ortam değişkeni tanımlı değil! (source ~/.bashrc yap)")

    out_dir = Path("..") / args.repo / args.ep_path
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url = f"https://raw.githubusercontent.com/mesflit/{args.repo}/main/{args.ep_path}"

    # 1. Geçici AES-128 anahtar ve keyinfo dosyası oluştur (repo'ya GİRMEZ)
    with tempfile.TemporaryDirectory() as tmp:
        key_file = Path(tmp) / "enc.key"
        key_info = Path(tmp) / "keyinfo.txt"
        key_file.write_bytes(get_aes_key(secret))
        key_info.write_text(f"enc.key\n{key_file}\n")

        # 2. FFmpeg ile doğrudan 6 sn'lik AES-128 şifreli HLS üret
        audio_map = f"0:a:m:language:{args.lang}" if args.lang != "0" else "0:a:0"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", args.input,
            "-map", "0:v:0", "-map", f"{audio_map}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", args.preset,
            "-c:a", "aac", "-b:a", "128k",
            "-hls_time", "6",
            "-hls_playlist_type", "vod",
            "-hls_key_info_file", str(key_info),
            "-hls_segment_filename", str(out_dir / "seg_%03d.ts"),
            str(out_dir / "index.m3u8")
        ]
        run(ffmpeg_cmd)

    # 3. Altyazıları (.vtt) hazırla ve temizle
    labels = {"tr": "Türkçe", "en": "İngilizce", "jp": "Japonca"}
    subtitles = []
    # Harici altyazılar (--sub tr:dosya.srt)
    for item in (args.sub or []):
        lang, sub_path = item.split(":", 1)
        vtt_out = out_dir / f"{lang}.vtt"
        run(["ffmpeg", "-y", "-i", sub_path, str(vtt_out)])
        clean_vtt(vtt_out)
        subtitles.append({"lang": lang, "label": labels.get(lang, lang.upper()), "src": f"{base_url}/{lang}.vtt"})

    # MKV içindeki gömülü ilk altyazıyı otomatik çıkar (isteğe bağlı)
    if args.extract_sub:
        vtt_out = out_dir / "en.vtt"
        codec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "s:0", "-show_entries",
                                "stream=codec_name", "-of", "csv=p=0", args.input],
                               capture_output=True, text=True).stdout.strip()
        if codec in ("hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle"):
            # Resim altyazı: metne çevrilemez, OCR için .sup olarak kenara kaydet (repoya girmez)
            sup = Path(args.input).with_suffix(".sup")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.input, "-map", "0:s:0", "-c", "copy", str(sup)])
            print(f"⚠️  UYARI: Altyazı resim formatında ({codec}), metne çevrilemedi!")
            print(f"    OCR için kaydedildi: {sup}")
        elif not codec:
            print("⚠️  UYARI: Bu dosyada gömülü altyazı yok.")
        res = subprocess.run(["ffmpeg", "-y", "-i", args.input, "-map", "0:s:0", str(vtt_out)]) if codec and vtt_out.parent.exists() and codec not in ("hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle") else None
        if res and res.returncode == 0 and vtt_out.exists() and vtt_out.stat().st_size > 10:
            clean_vtt(vtt_out)
            subtitles.append({"lang": "en", "label": "İngilizce", "src": f"{base_url}/en.vtt"})

    # İngilizceden otomatik Türkçe çeviri (--tr)
    has_tr = any(s["lang"] == "tr" for s in subtitles)
    if args.tr and not has_tr and (out_dir / "en.vtt").exists():
        run([sys.executable, str(Path(__file__).parent / "altyazi.py"), "cevir", args.repo])
        if (out_dir / "tr.vtt").exists():
            has_tr = True
    if has_tr or (out_dir / "tr.vtt").exists():
        subtitles = [s for s in subtitles if s["lang"] != "tr"]
        subtitles.insert(0, {"lang": "tr", "label": "Türkçe", "src": f"{base_url}/tr.vtt"})

    # 4. Deponun mes.anime dosyasını güncelle (site bölümleri buradan okur)
    import mesanime  # noqa: E402
    mesanime.update(Path("..") / args.repo, args.anime, args.category, args.poster)
    ep_obj = next(e for e in json.loads((Path("..") / args.repo / mesanime.FILE).read_text(encoding="utf-8"))["episodes"]
                  if e["path"] == args.ep_path.strip("/"))
    if args.title and ep_obj["title"] != args.title:
        mesanime.set_title(Path("..") / args.repo, ep_obj["path"], args.title)

    print(f"✅ Tamamlandı: {out_dir} ({len(subtitles)} altyazı)")
    print(f"➡️  Yayınla: cd ../{args.repo} && git add --sparse -A && git commit -m 'feat: {args.ep_path}' && git push")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Kaynak .mkv veya .mp4 dosyası")
    p.add_argument("repo", help="GitHub video depo adı (örn: opm)")
    p.add_argument("ep_path", help="Depo içi bölüm klasörü (örn: s1/ep1)")
    p.add_argument("--anime", help="Anime adı (sadece ilk bölümde gerekli, sonra mes.anime'de kalır)")
    p.add_argument("--title", help="Bölüm başlığı (boşsa: N. Sezon M. Bölüm)")
    p.add_argument("--category", help="Kategori (örn: Aksiyon)")
    p.add_argument("--poster", help="Kapak: yerel dosya, depodaki dosya adı veya URL")
    p.add_argument("--lang", default="jpn", help="Ses dili (jpn veya 0)")
    p.add_argument("--preset", default="veryfast", help="FFmpeg preset (ultrafast/veryfast)")
    p.add_argument("--sub", action="append", help="Harici altyazı (örn: tr:altyazi.srt)")
    p.add_argument("--extract-sub", action="store_true", help="MKV içindeki ilk altyazıyı çıkar")
    p.add_argument("--tr", action="store_true", help="İngilizce altyazıyı otomatik Türkçeye çevir (deep-translator)")
    pack_hls(p.parse_args())
