import os
import sys
import json
import subprocess
import re

GITHUB_USER = "mesflit"
AES_KEY = os.getenv("VIDEO_SECRET_KEY", "")
AES_IV  = "abcdef9876543210abcdef9876543210"
CHUNK_SIZE = 20 * 1024 * 1024  # 20 MB
DB_PATH = "data/animes.json"

def pack_video(mp4_path, repo_name, sub_dir, ep_title, category="Aksiyon"):
    if len(AES_KEY) != 64:
        print("[!] Hata: VIDEO_SECRET_KEY tanımlı değil!")
        sys.exit(1)

    sub_dir = sub_dir.strip("/")
    repo_root = os.path.abspath(os.path.join("..", repo_name))
    out_dir = os.path.join(repo_root, sub_dir)
    os.makedirs(out_dir, exist_ok=True)

    anime_title = re.sub(r"\s+(S\d+|B\d+|E\d+|Bölüm).*", "", ep_title, flags=re.IGNORECASE).strip() or ep_title

    parts = []
    idx = 0
    with open(mp4_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            raw_path = os.path.join(out_dir, f"part_{idx:03d}.tmp")
            enc_name = f"part_{idx:03d}.enc"
            enc_path = os.path.join(out_dir, enc_name)

            with open(raw_path, "wb") as cf:
                cf.write(chunk)

            subprocess.run([
                "openssl", "enc", "-aes-256-cbc",
                "-K", AES_KEY, "-iv", AES_IV,
                "-in", raw_path, "-out", enc_path
            ], check=True)

            os.remove(raw_path)
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{repo_name}/main/{sub_dir}/{enc_name}"
            parts.append(raw_url)
            print(f"[+] Şifrelendi: {repo_name}/{sub_dir}/{enc_name}")
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

    ep_match = re.search(r"(?:B|E|Bölüm\s*)(\d+)", ep_title, flags=re.IGNORECASE)
    ep_num = int(ep_match.group(1)) if ep_match else len(db[anime_title]["episodes"]) + 1

    db[anime_title]["episodes"][ep_title] = {
        "episode": ep_num,
        "title": ep_title,
        "parts": parts
    }

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Tamamlandı! {len(parts)} parça -> {repo_root}")
    print(f"[✓] Linkler data/animes.json dosyasına işlendi.")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print('Kullanım: python3 scripts/pack.py <video.mp4> <repo_adi> <alt_klasor> "<Bölüm Başlığı>" [Kategori]')
        print('Örnek:    python3 scripts/pack.py bolum1.mp4 opm-s1 "ep1" "OnePunchMan S1 B1" "Aksiyon"')
        sys.exit(1)
    cat = sys.argv[5] if len(sys.argv) > 5 else "Aksiyon"
    pack_video(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], cat)
