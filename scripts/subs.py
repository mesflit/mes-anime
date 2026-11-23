"""Altyazı araçları: VTT temizleme ve çeviri için ortak fonksiyonlar.

ffmpeg ile ASS -> VTT dönüşümünde fansub notları ({...}), vektör çizimleri
(m 0 0 l ...) ve kare kare tekrarlanan tabela yazıları VTT'ye sızıyor.
Bu modül bunları temizler.
"""
import re

TIME_RE = re.compile(r"^((?:\d+:)?\d{2}:\d{2}\.\d{3})\s+-->\s+((?:\d+:)?\d{2}:\d{2}\.\d{3})")
DRAWING_RE = re.compile(r"^\s*m\s+-?\d+(\.\d+)?\s+-?\d+(\.\d+)?(\s+[lbmnsc](\s+-?\d+(\.\d+)?)+)+\s*$", re.I)


def to_sec(t):
    parts = [float(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def fmt(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def parse_vtt(text):
    cues = []
    blocks = re.split(r"\n\s*\n", text.replace("\r", "").strip())
    for b in blocks:
        lines = b.split("\n")
        for i, line in enumerate(lines):
            m = TIME_RE.match(line.strip())
            if m:
                body = "\n".join(lines[i + 1:])
                cues.append([to_sec(m.group(1)), to_sec(m.group(2)), body])
                break
    return cues


def clean_text(body):
    t = re.sub(r"\{[^}]*\}", "", body)          # fansub notları / ASS etiketleri
    t = re.sub(r"\\[Nn]", "\n", t)
    t = re.sub(r"\\h", " ", t)
    t = re.sub(r"</?(b|i|u|s|c[^>]*|font[^>]*)>", "", t)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
    lines = [l for l in lines if l and not DRAWING_RE.match(l)]
    return "\n".join(lines)


def clean_cues(cues, min_dur=0.25):
    out = []
    seen_at = {}
    for start, end, body in sorted(cues, key=lambda c: (c[0], c[1])):
        text = clean_text(body)
        if not text:
            continue
        flat = text.replace("\n", " ")
        # Aynı metnin kare kare tekrarlarını tek bir cue'da birleştir
        prev = seen_at.get(flat)
        if prev is not None and start <= prev[1] + 0.15:
            prev[1] = max(prev[1], end)
            continue
        cue = [start, end, text]
        out.append(cue)
        seen_at[flat] = cue
    out = [c for c in out if c[1] - c[0] >= min_dur]
    out.sort(key=lambda c: (c[0], c[1]))
    return out


def write_vtt(cues):
    parts = ["WEBVTT", ""]
    for s, e, t in cues:
        parts.append(f"{fmt(s)} --> {fmt(e)}")
        parts.append(t)
        parts.append("")
    return "\n".join(parts)
