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
        res = subprocess.run(["ffmpeg", "-y", "-i", args.input, "-map", "0:s:0", str(vtt_out)])
        if res.returncode == 0 and vtt_out.exists():
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

    # 4. data/animes.json güncelle (Anime bazlı gruplu yapı)
    db_path = Path("data/animes.json")
    db_path.parent.mkdir(exist_ok=True)
    db = []
    if db_path.exists():
        try:
            loaded = json.loads(db_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list) and (not loaded or "episodes" in loaded[0]):
                db = loaded
        except Exception:
            db = []

    anime = next((a for a in db if a["id"] == args.repo), None)
    if not anime:
        anime = {
            "id": args.repo,
            "title": args.anime,
            "category": args.category,
            "poster": args.poster or "",
            "episodes": []
        }
        db.append(anime)
    elif args.poster:
        anime["poster"] = args.poster

    ep_id = args.ep_path.replace("/", "-")
    ep_obj = {
        "id": ep_id,
        "title": args.title,
        "m3u8": f"{base_url}/index.m3u8",
        "subtitles": subtitles
    }
    idx = next((i for i, e in enumerate(anime["episodes"]) if e["id"] == ep_id), None)
    if idx is None:
        anime["episodes"].append(ep_obj)
    else:
        anime["episodes"][idx] = ep_obj  # sırayı bozmadan güncelle

    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Tamamlandı: {out_dir} ({len(subtitles)} altyazı)")
    print(f"➡️  Yayınla: cd ../{args.repo} && git add --sparse -A && git commit -m 'feat: {args.title}' && git push")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Kaynak .mkv veya .mp4 dosyası")
    p.add_argument("repo", help="GitHub video depo adı (örn: opm)")
    p.add_argument("ep_path", help="Depo içi bölüm klasörü (örn: s1/ep1)")
    p.add_argument("--anime", required=True, help="Anime adı (örn: One Punch Man)")
    p.add_argument("--title", required=True, help="Bölüm başlığı (örn: S1 B1)")
    p.add_argument("--category", default="Aksiyon")
    p.add_argument("--poster", default="", help="Kapak görseli URL")
    p.add_argument("--lang", default="jpn", help="Ses dili (jpn veya 0)")
    p.add_argument("--preset", default="veryfast", help="FFmpeg preset (ultrafast/veryfast)")
    p.add_argument("--sub", action="append", help="Harici altyazı (örn: tr:altyazi.srt)")
    p.add_argument("--extract-sub", action="store_true", help="MKV içindeki ilk altyazıyı çıkar")
    p.add_argument("--tr", action="store_true", help="İngilizce altyazıyı otomatik Türkçeye çevir (deep-translator)")
    pack_hls(p.parse_args())
