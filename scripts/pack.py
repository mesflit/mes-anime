import os
import sys
import json
import subprocess
import re

AES_KEY = os.getenv("VIDEO_SECRET_KEY", "")
AES_IV  = "abcdef9876543210abcdef9876543210"
CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB
DB_PATH = "data/animes.json"

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def pack_video(mp4_path, anime_title, episode_num, category="Aksiyon"):
    if len(AES_KEY) != 64:
        print("[!] Hata: VIDEO_SECRET_KEY 64 karakterlik hex olmalı!")
        print("Örnek: export VIDEO_SECRET_KEY=$(openssl rand -hex 32)")
        sys.exit(1)

    slug = slugify(anime_title)
    out_dir = f"videos/{slug}/ep{episode_num}"
    os.makedirs(out_dir, exist_ok=True)

    parts = []
    idx = 0
    with open(mp4_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            raw_path = f"{out_dir}/part_{idx:03d}.tmp"
            enc_path = f"{out_dir}/part_{idx:03d}.enc"

            with open(raw_path, "wb") as cf:
                cf.write(chunk)

            subprocess.run([
                "openssl", "enc", "-aes-256-cbc",
                "-K", AES_KEY, "-iv", AES_IV,
                "-in", raw_path, "-out", enc_path
            ], check=True)

            os.remove(raw_path)
            parts.append(enc_path)
            print(f"[+] Şifrelendi: {enc_path}")
            idx += 1

    os.makedirs("data", exist_ok=True)
    db = json.load(open(DB_PATH, "r", encoding="utf-8")) if os.path.exists(DB_PATH) else {}

    if anime_title not in db:
        db[anime_title] = {
            "romaji_title": anime_title,
            "categories": [category],
            "year": 2026,
            "cover": "",
            "episodes": {}
        }

    db[anime_title]["episodes"][str(episode_num)] = {
        "episode": int(episode_num),
        "parts": parts
    }

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"[✓] Tamamlandı! {len(parts)} şifreli parça oluşturuldu.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Kullanım: python3 scripts/pack.py <video.mp4> <Anime Adı> <Bölüm No> [Kategori]")
        sys.exit(1)
    cat = sys.argv[4] if len(sys.argv) > 4 else "Aksiyon"
    pack_video(sys.argv[1], sys.argv[2], sys.argv[3], cat)
