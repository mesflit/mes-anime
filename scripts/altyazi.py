#!/usr/bin/env python3
"""Altyazı yönetimi.

Kullanım (video deposu ../opm gibi mes-anime'nin yanında klonlu olmalı):

  # Tüm en.vtt dosyalarını temizle (fansub notları, vektör çizimleri, tekrarlar)
  python3 scripts/altyazi.py temizle opm

  # en.vtt -> tr.vtt makine çevirisi (pip install deep-translator)
  python3 scripts/altyazi.py cevir opm

  # Depodaki tüm *.vtt dosyalarını mes.anime'ye kaydet
  python3 scripts/altyazi.py kaydet opm
"""
import argparse, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import subs  # noqa: E402

LABELS = {"tr": "Türkçe", "en": "İngilizce", "jp": "Japonca", "ja": "Japonca"}
ORDER = {"tr": 0, "en": 1}


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
    import mesanime  # noqa: E402
    mesanime.update(Path("..") / a.repo)


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
