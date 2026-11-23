"""Video depolarını tarayıp data/animes.json'daki bölüm listesini otomatik günceller.

Bölümleri elle girmene gerek yok: video deposunda `sN/epM/index.m3u8` olan her klasör
bir bölüm sayılır, yanındaki `*.vtt` dosyaları altyazı olarak eklenir.

Kullanım (mes-anime klasöründeyken):
    python3 scripts/senkron.py                 # animes.json'daki tüm animeleri güncelle
    python3 scripts/senkron.py opm             # sadece opm
    python3 scripts/senkron.py yeni-repo --anime "Anime Adı" --category "Aksiyon" --poster data/x.jpg
                                               # yeni anime ekle (bir kere yeterli)

Kaynak: ../<repo> klasörü varsa oradan okur (hafif klon yeterli), yoksa GitHub API'den.
Var olan bölüm başlıkları korunur; yenilerine "N. Sezon M. Bölüm" verilir.
"""
import os, re, sys, json, argparse, urllib.request
from pathlib import Path

DB_PATH = Path("data/animes.json")
USER = os.environ.get("GH_USER", "mesflit")
LABELS = {"tr": "Türkçe", "en": "İngilizce", "jp": "Japonca", "ja": "Japonca"}
EP_RE = re.compile(r"^s(\d+)/ep(\d+)/(index\.m3u8|([a-z]{2,3})\.vtt)$")


def list_files_local(path: Path):
    for p in path.glob("s*/ep*/*"):
        yield p.relative_to(path).as_posix()


def list_files_github(repo: str, branch: str):
    url = f"https://api.github.com/repos/{USER}/{repo}/git/trees/{branch}?recursive=1"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except Exception as e:
        sys.exit(f"HATA: {repo} GitHub'dan okunamadı ({e}). Önce: bash scripts/hafif_klon.sh {repo}")
    if data.get("truncated"):
        print(f"⚠️  {repo}: GitHub listesi kesildi, bazı bölümler eksik olabilir. Yerel klon kullan.")
    return [t["path"] for t in data["tree"] if t["type"] == "blob"]


def scan(repo: str, branch: str):
    """{(sezon, bolum): set(diller)} döndürür; sadece index.m3u8 olanlar bölüm sayılır."""
    local = Path("..") / repo
    files = list_files_local(local) if (local / ".git").exists() else list_files_github(repo, branch)
    eps, langs = set(), {}
    for f in files:
        m = EP_RE.match(f)
        if not m:
            continue
        key = (int(m[1]), int(m[2]))
        if m[3] == "index.m3u8":
            eps.add(key)
        else:
            langs.setdefault(key, set()).add(m[4])
    return {k: langs.get(k, set()) for k in eps}, ("yerel" if (local / ".git").exists() else "GitHub")


def sub_order(lang):
    return (0 if lang == "tr" else 1 if lang == "en" else 2, lang)


def sync_anime(anime: dict, branch: str):
    repo = anime.get("repo", anime["id"])
    found, source = scan(repo, branch)
    if not found:
        print(f"⚠️  {repo}: hiç bölüm bulunamadı, dokunulmadı.")
        return 0, 0
    old = {e["id"]: e for e in anime.get("episodes", [])}
    base = f"https://raw.githubusercontent.com/{USER}/{repo}/{branch}"
    episodes, added = [], []
    for (s, n) in sorted(found):
        ep_id = f"s{s}-ep{n}"
        path = f"{base}/s{s}/ep{n}"
        prev = old.get(ep_id, {})
        ep = dict(prev)  # ekstra alanları (ör. elle verilmiş başlık) koru
        ep["id"] = ep_id
        ep["title"] = prev.get("title") or f"{s}. Sezon {n}. Bölüm"
        ep["m3u8"] = f"{path}/index.m3u8"
        ep["subtitles"] = [
            {"lang": l, "label": LABELS.get(l, l.upper()), "src": f"{path}/{l}.vtt"}
            for l in sorted(found[(s, n)], key=sub_order)
        ]
        if ep_id not in old:
            added.append(ep_id)
        episodes.append(ep)
    removed = [i for i in old if i not in {e["id"] for e in episodes}]
    anime["episodes"] = episodes
    print(f"✅ {anime['title']} ({source}): {len(episodes)} bölüm"
          + (f", yeni: {', '.join(added)}" if added else ", yeni bölüm yok")
          + (f", kaldırılan: {', '.join(removed)}" if removed else ""))
    return len(added), len(removed)


def main():
    p = argparse.ArgumentParser(description="Video depolarından animes.json'u günceller")
    p.add_argument("repos", nargs="*", help="Sadece bu depolar (boşsa hepsi)")
    p.add_argument("--anime", help="Yeni anime eklerken adı")
    p.add_argument("--category", default="Anime")
    p.add_argument("--poster", default="")
    p.add_argument("--branch", default="main")
    a = p.parse_args()

    db = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else []
    if not isinstance(db, list):
        sys.exit("HATA: animes.json beklenmeyen formatta, üzerine yazılmadı!")

    for repo in a.repos:
        if not any(x.get("repo", x["id"]) == repo for x in db):
            if not a.anime:
                sys.exit(f"HATA: '{repo}' animes.json'da yok. Yeni anime için --anime \"Ad\" ver.")
            db.append({"id": repo, "title": a.anime, "category": a.category,
                       "poster": a.poster, "episodes": []})
            print(f"➕ Yeni anime eklendi: {a.anime} ({repo})")

    targets = [x for x in db if not a.repos or x.get("repo", x["id"]) in a.repos]
    before = DB_PATH.read_text(encoding="utf-8") if DB_PATH.exists() else ""
    for anime in targets:
        sync_anime(anime, a.branch)
    after = json.dumps(db, ensure_ascii=False, indent=2) + "\n"
    if after != before:
        DB_PATH.write_text(after, encoding="utf-8")
        print("💾 data/animes.json güncellendi.")
    else:
        print("ℹ️  Değişiklik yok.")


if __name__ == "__main__":
    main()
