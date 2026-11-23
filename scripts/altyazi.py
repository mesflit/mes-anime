#!/usr/bin/env python3
"""Altyazı yönetimi.

Kullanım (video deposu ../opm gibi mes-anime'nin yanında klonlu olmalı):

  # Tüm en.vtt dosyalarını temizle (fansub notları, vektör çizimleri, tekrarlar)
  python3 scripts/altyazi.py temizle opm

  # en.vtt -> tr.vtt makine çevirisi (pip install deep-translator)
  python3 scripts/altyazi.py cevir opm

  # Depodaki tüm *.vtt dosyalarını data/animes.json'a kaydet
  python3 scripts/altyazi.py kaydet opm
"""
import argparse, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import subs  # noqa: E402

LABELS = {"tr": "Türkçe", "en": "İngilizce", "jp": "Japonca", "ja": "Japonca"}
ORDER = {"tr": 0, "en": 1}
DB = Path("data/animes.json")


def ep_dirs(repo_dir: Path):
    return sorted(p for p in repo_dir.glob("s*/ep*") if p.is_dir())


def cmd_temizle(a):
    for d in ep_dirs(Path("..") / a.repo):
        for f in d.glob("*.vtt"):
            raw = f.read_text(encoding="utf-8", errors="ignore")
            cues = subs.clean_cues(subs.parse_vtt(raw))
            f.write_text(subs.write_vtt(cues), encoding="utf-8")
            print(f"🧹 {f}: {len(cues)} satır")


def translate_batch(translator, texts):
    """Metinleri numaralı satırlar halinde tek istekte çevirir (hız + bağlam)."""
    joined = "\n".join(f"[{i}] {t.replace(chr(10), ' / ')}" for i, t in enumerate(texts))
    out = translator.translate(joined) or ""
    res = {}
    for line in out.split("\n"):
        m = re.match(r"\s*\[(\d+)\]\s*(.*)", line)
        if m:
            res[int(m.group(1))] = m.group(2).strip().replace(" / ", "\n")
    return [res.get(i) or translator.translate(t) or t for i, t in enumerate(texts)]


def cmd_cevir(a):
    from deep_translator import GoogleTranslator
    tr = GoogleTranslator(source="en", target="tr")
    for d in ep_dirs(Path("..") / a.repo):
        src, dst = d / "en.vtt", d / "tr.vtt"
        if not src.exists() or (dst.exists() and not a.force):
            continue
        cues = subs.clean_cues(subs.parse_vtt(src.read_text(encoding="utf-8")))
        uniq = list(dict.fromkeys(c[2] for c in cues))
        mapping = {}
        for i in range(0, len(uniq), 40):
            chunk = uniq[i:i + 40]
            for attempt in range(4):
                try:
                    mapping.update(zip(chunk, translate_batch(tr, chunk)))
                    break
                except Exception as e:
                    print("  tekrar deneniyor:", e); time.sleep(5 * (attempt + 1))
            print(f"  {d}: {min(i + 40, len(uniq))}/{len(uniq)}")
        dst.write_text(subs.write_vtt([[s, e, mapping.get(t, t)] for s, e, t in cues]), encoding="utf-8")
        print(f"🇹🇷 {dst}")


def cmd_kaydet(a):
    db = json.loads(DB.read_text(encoding="utf-8"))
    anime = next((x for x in db if x["id"] == a.repo), None)
    if not anime:
        sys.exit(f"HATA: animes.json içinde '{a.repo}' yok")
    repo_dir = Path("..") / a.repo
    for ep in anime["episodes"]:
        ep_path = ep["id"].replace("-", "/", 1)
        base = ep["m3u8"].rsplit("/", 1)[0]
        found = sorted((repo_dir / ep_path).glob("*.vtt"), key=lambda f: ORDER.get(f.stem, 9))
        if not found:
            continue
        ep["subtitles"] = [{"lang": f.stem, "label": LABELS.get(f.stem, f.stem.upper()), "src": f"{base}/{f.name}"} for f in found]
        print(f"📝 {ep['id']}: {', '.join(f.stem for f in found)}")
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    for name in ("temizle", "cevir", "kaydet"):
        s = sp.add_parser(name)
        s.add_argument("repo", help="Video deposu adı (örn: opm)")
        if name == "cevir":
            s.add_argument("--force", action="store_true", help="Var olan tr.vtt'nin üzerine yaz")
    args = p.parse_args()
    {"temizle": cmd_temizle, "cevir": cmd_cevir, "kaydet": cmd_kaydet}[args.cmd](args)
