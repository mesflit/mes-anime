#!/usr/bin/env python3
"""Video deposunun kökündeki `mes.anime` dosyasını oluşturur / günceller.

Site her anime deposundan sadece bu dosyayı okur. mes-anime tarafında yalnızca
`data/depolar.txt` içine depo yolunu yazmak yeterli (ör. `mesflit/opm`).

Kullanım (video deposu mes-anime'nin yanında, ör. ../opm, hafif klon yeterli):

  # Klasörleri tarayıp mes.anime'yi güncelle (yeni bölüm ekledikten sonra)
  python3 scripts/mesanime.py opm

  # İlk kez oluştururken anime bilgilerini ver (sonra gerek yok, dosyada kalır)
  python3 scripts/mesanime.py yeni-repo --anime "Anime Adı" --category "Aksiyon" --poster kapak.jpg

`sN/epM/index.m3u8` olan her klasör bir bölümdür, yanındaki `xx.vtt` dosyaları altyazıdır.
Var olan başlıklar korunur (elle düzenleyebilirsin); yenilere "N. Sezon M. Bölüm" verilir.
--poster yerel bir dosyaysa depoya poster.<uzantı> olarak kopyalanır.

mes.anime biçimi (JSON, yollar depo köküne göre):
  {
    "title": "One Punch Man",
    "category": "Aksiyon",
    "poster": "poster.jpg",
    "episodes": [
      {"path": "s1/ep1", "title": "1. Sezon 1. Bölüm", "subtitles": ["tr", "en"]}
    ]
  }
"""
import argparse, json, re, shutil, sys
from pathlib import Path

FILE = "mes.anime"
EP_RE = re.compile(r"^s(\d+)/ep(\d+)$")


def sub_order(lang):
    return (0 if lang == "tr" else 1 if lang == "en" else 2, lang)


def dump(meta: dict) -> str:
    """Her bölüm tek satır: elle düzenlemesi ve git diff'i okunaklı olsun."""
    head = {k: v for k, v in meta.items() if k != "episodes"}
    lines = [f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}," for k, v in head.items()]
    eps = [f"    {json.dumps(e, ensure_ascii=False)}" for e in meta.get("episodes", [])]
    return "{\n" + "\n".join(lines) + '\n  "episodes": [\n' + ",\n".join(eps) + "\n  ]\n}\n"


def update(repo_dir: Path, anime=None, category=None, poster=None) -> dict:
    if not repo_dir.is_dir():
        sys.exit(f"HATA: {repo_dir} yok. Önce: bash scripts/hafif_klon.sh {repo_dir.name}")
    path = repo_dir / FILE
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if anime:
        meta["title"] = anime
    if category:
        meta["category"] = category
    if poster:
        src = Path(poster)
        if src.is_file():
            dst = repo_dir / f"poster{src.suffix.lower()}"
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
            meta["poster"] = dst.name
        else:
            meta["poster"] = poster  # tam URL veya depodaki dosya adı
    if not meta.get("title"):
        sys.exit(f"HATA: {path} yok. İlk sefer için --anime \"Anime Adı\" ver.")
    meta.setdefault("category", "Anime")
    meta.setdefault("poster", "")

    old = {e["path"]: e for e in meta.get("episodes", [])}
    found = []
    for m3u8 in repo_dir.glob("s*/ep*/index.m3u8"):
        rel = m3u8.parent.relative_to(repo_dir).as_posix()
        m = EP_RE.match(rel)
        if m:
            found.append((int(m[1]), int(m[2]), rel, m3u8.parent))
    episodes, added = [], []
    for s, n, rel, d in sorted(found):
        ep = dict(old.get(rel, {}))
        ep["path"] = rel
        ep["title"] = ep.get("title") or f"{s}. Sezon {n}. Bölüm"
        ep["subtitles"] = sorted((f.stem for f in d.glob("*.vtt")), key=sub_order)
        episodes.append(ep)
        if rel not in old:
            added.append(rel)
    removed = [p for p in old if p not in {e["path"] for e in episodes}]
    meta["episodes"] = episodes

    path.write_text(dump(meta), encoding="utf-8")
    print(f"✅ {path}: {meta['title']}, {len(episodes)} bölüm"
          + (f" | yeni: {', '.join(added)}" if added else " | yeni bölüm yok")
          + (f" | silinen: {', '.join(removed)}" if removed else ""))
    return meta


def set_title(repo_dir: Path, ep_path: str, title: str):
    path = repo_dir / FILE
    meta = json.loads(path.read_text(encoding="utf-8"))
    for e in meta["episodes"]:
        if e["path"] == ep_path:
            e["title"] = title
    path.write_text(dump(meta), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Video deposu klasör adı (örn: opm -> ../opm)")
    p.add_argument("--anime", help="Anime adı")
    p.add_argument("--category", help="Kategori (örn: Aksiyon)")
    p.add_argument("--poster", help="Kapak: yerel dosya (depoya kopyalanır), depodaki dosya adı veya URL")
    a = p.parse_args()
    update(Path("..") / a.repo, a.anime, a.category, a.poster)
