import os
import sys
import json
import subprocess
import re

AES_KEY = os.getenv("VIDEO_SECRET_KEY", "")
AES_IV  = "abcdef9876543210abcdef9876543210"
CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB
DB_PATH = "data/animes.json"

def pack_video(mp4_path, out_dir, ep_title, anime_title=None, category="Aksiyon"):
    if len(AES_KEY) != 64:
        print("[!] Hata: VIDEO_SECRET_KEY tanımlı değil!")
        sys.exit(1)

    # Başındaki / işaretini kaldır (repo içine yazması için)
    out_dir = out_dir.lstrip("/")
    os.makedirs(out_dir, exist_ok=True)

    # Anime adı verilmediyse "OnePunchMan S1 B1" -> "OnePunchMan" olarak ayıkla
    if not anime_title:
        anime_title = re.sub(r"\s+(S\d+|B\d+|E\d+|Bölüm).*", "", ep_title, flags=re.IGNORECASE).strip() or ep_title

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

    # Sıralama için bölüm numarasını çek (yoksa sıradaki sayıyı ver)
    ep_match = re.search(r"(?:B|E|Bölüm\s*)(\d+)", ep_title, flags=re.IGNORECASE)
    ep_num = int(ep_match.group(1)) if ep_match else len(db[anime_title]["episodes"]) + 1

    db[anime_title]["episodes"][ep_title] = {
        "episode": ep_num,
        "title": ep_title,
        "parts": parts
    }

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"[✓] Tamamlandı! '{anime_title}' altına '{ep_title}' ({len(parts)} parça) eklendi.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('Kullanım: python3 scripts/pack.py <video.mp4> "/videos/opm/season1/bolum1" "OnePunchMan S1 B1" [Kategori]')
        sys.exit(1)
    cat = sys.argv[4] if len(sys.argv) > 4 else "Aksiyon"
    pack_video(sys.argv[1], sys.argv[2], sys.argv[3], category=cat)
