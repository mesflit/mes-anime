import os
import re
import json
import subprocess
import feedparser
import requests
from deep_translator import GoogleTranslator

RSS_URL = "https://nyaa.si/?page=rss&u=SubsPlease"
ANILIST_URL = "https://graphql.anilist.co"
DB_PATH = "data/animes.json"
PROCESSED_PATH = "data/processed.txt"
UPLOAD_API_KEY = os.getenv("UPLOAD_API_KEY", "")

WATCHLIST = []
MAX_PER_RUN = 2

ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english }
    genres
    seasonYear
    status
    description(asHtml: false)
    coverImage { extraLarge }
  }
}
"""

def parse_filename(title):
    pattern = r"^\[(?P<group>.*?)\]\s+(?P<title>.*?)\s+-\s+(?P<episode>\d+(?:v\d+)?)\s+\((?P<quality>\d+p)\)"
    match = re.match(pattern, title)
    if not match:
        return None
    return {
        "title": match.group("title").strip(),
        "episode": int(re.sub(r"v\d+", "", match.group("episode"))),
        "quality": match.group("quality"),
    }

def load_processed():
    if not os.path.exists(PROCESSED_PATH):
        return set()
    with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_processed(entry_title):
    os.makedirs("data", exist_ok=True)
    with open(PROCESSED_PATH, "a", encoding="utf-8") as f:
        f.write(entry_title + "\n")

def translate_ass(eng_ass, tr_ass):
    translator = GoogleTranslator(source="en", target="tr")
    translated_lines = []
    with open(eng_ass, "r", encoding="utf-8-sig", errors="ignore") as f:
        for line in f:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) < 10:
                    translated_lines.append(line)
                    continue
                meta = ",".join(parts[:9])
                text = parts[9].strip()
                tags = re.findall(r"\{.*?\}", text)
                clean_text = re.sub(r"\{.*?\}", " ||| ", text).replace(r"\N", " \n ")
                try:
                    tr_text = translator.translate(clean_text) or clean_text
                    for tag in tags:
                        tr_text = tr_text.replace("|||", tag, 1)
                    tr_text = tr_text.replace("\n", r"\N")
                except Exception:
                    tr_text = text
                translated_lines.append(f"{meta},{tr_text}\n")
            else:
                translated_lines.append(line)
    with open(tr_ass, "w", encoding="utf-8") as f:
        f.writelines(translated_lines)

def upload_to_doodstream(mp4_path):
    if not UPLOAD_API_KEY:
        raise ValueError("UPLOAD_API_KEY tanımlı değil!")
    srv = requests.get(f"https://doodapi.com/api/upload/server?key={UPLOAD_API_KEY}", timeout=20).json()
    with open(mp4_path, "rb") as f:
        res = requests.post(srv["result"], data={"api_key": UPLOAD_API_KEY}, files={"file": f}, timeout=600).json()
    return f"https://dood.li/e/{res['result'][0]['filecode']}"

def update_database(parsed, embed_url):
    os.makedirs("data", exist_ok=True)
    db = json.load(open(DB_PATH, "r", encoding="utf-8")) if os.path.exists(DB_PATH) else {}
    title_key = parsed["title"]
    if title_key not in db:
        try:
            res = requests.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": {"search": title_key}}, timeout=15).json()
            media = res["data"]["Media"]
            db[title_key] = {
                "anilist_id": media["id"],
                "romaji_title": media["title"]["romaji"],
                "english_title": media["title"]["english"] or title_key,
                "categories": media["genres"] or ["Genel"],
                "year": media["seasonYear"] or 2026,
                "status": media["status"],
                "cover": media["coverImage"]["extraLarge"],
                "description": (media["description"] or "")[:400],
                "episodes": {},
            }
        except Exception:
            db[title_key] = {
                "anilist_id": None, "romaji_title": title_key, "english_title": title_key,
                "categories": ["Genel"], "year": 2026, "status": "RELEASING",
                "cover": "", "description": "", "episodes": {},
            }
    db[title_key]["episodes"][str(parsed["episode"])] = {
        "episode": parsed["episode"], "quality": parsed["quality"], "embed_url": embed_url
    }
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def process_entry(entry):
    parsed = parse_filename(entry.title)
    if not parsed or parsed["quality"] != "1080p":
        return False
    if WATCHLIST and not any(w.lower() in parsed["title"].lower() for w in WATCHLIST):
        return False
    os.makedirs("tmp", exist_ok=True)
    subprocess.run(["aria2c", "--seed-time=0", "--dir=tmp", "--summary-interval=0", entry.link], check=True)
    mkv_files = [f for f in os.listdir("tmp") if f.endswith(".mkv")]
    if not mkv_files:
        return False
    mkv_path = os.path.join("tmp", mkv_files[0])
    subprocess.run(["ffmpeg", "-y", "-i", mkv_path, "-map", "0:s:0", "tmp/eng.ass"], check=True)
    translate_ass("tmp/eng.ass", "tmp/tr.ass")
    subprocess.run([
        "ffmpeg", "-y", "-i", mkv_path, "-vf", "ass=tmp/tr.ass",
        "-c:v", "libx264", "-crf", "22", "-preset", "faster",
        "-c:a", "aac", "-b:a", "128k", "tmp/output.mp4"
    ], check=True)
    embed_url = upload_to_doodstream("tmp/output.mp4")
    update_database(parsed, embed_url)
    save_processed(entry.title)
    for f in os.listdir("tmp"):
        os.remove(os.path.join("tmp", f))
    return True

def main():
    processed = load_processed()
    feed = feedparser.parse(RSS_URL)
    count = 0
    for entry in feed.entries:
        if entry.title in processed:
            continue
        try:
            if process_entry(entry):
                count += 1
        except Exception as e:
            print(f"[!] Hata ({entry.title}): {e}")
        if count >= MAX_PER_RUN:
            break

if __name__ == "__main__":
    main()
