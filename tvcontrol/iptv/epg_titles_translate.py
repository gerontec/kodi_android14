#!/home/gh/python/venv_py311/bin/python3
"""Translate Cyrillic EPG titles to English for the guest pages (runs on dell, CPU, NLLB-600M).

Fetches epg.xml.gz from kellertreppe, translates only titles not in the cache, writes the cache back
to kellertreppe as /var/lib/tvremote/epg_titles_en.json ({original title: english}).
cron (dell): 15 5 * * *  (after the EPG build on kellertreppe)
"""
import gzip
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

KT = "pi@192.168.178.218"
REMOTE_EPG = "/home/pi/tvrestore/m3u/epg.xml.gz"
REMOTE_OUT = "/var/lib/tvremote/epg_titles_en.json"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "epg_titles_en.json")
MODEL = "facebook/nllb-200-distilled-600M"
MODEL_CACHE = os.path.join(HERE, "nllb_cache")      # shared with inference_server.py
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# Russian EPG genre prefixes confuse the model: strip them and put an English label in front
PREFIX = {"х/ф": "Film", "т/с": "Series", "м/ф": "Cartoon", "м/с": "Cartoon series", "д/ф": "Documentary",
          "д/с": "Documentary series", "мульт": "Cartoon", "худ. фильм": "Film"}
PREFIX_RE = re.compile(r"^\s*(" + "|".join(re.escape(k) for k in PREFIX) + r")\.?\s*", re.I)


def split_prefix(title):
    """'х/ф Поездка в Висбаден' -> ('Film', 'Поездка в Висбаден'); separators like ┊ become ' - '."""
    m = PREFIX_RE.match(title)
    label = PREFIX[m.group(1).lower()] if m else ""
    rest = title[m.end():] if m else title
    rest = re.sub(r"\s*[┊|]\s*", " - ", rest).strip()
    # trailing episode/part number stays untranslated: "Мой милый доктор - 4" -> core + " 4"
    m = re.search(r"(?:\s*-\s*|\s+)(\d+(?:\s*[-/]\s*\d+)?)\s*$", rest)
    return label, (rest[:m.start()].strip() if m else rest), (m.group(1) if m else "")


def titles(local_gz):
    root = ET.parse(gzip.open(local_gz)).getroot()
    return sorted({(p.findtext("title") or "").strip() for p in root.findall("programme")} - {""})


def translate(texts):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    torch.set_num_threads(8)                        # leave cores for cams-ai and the rest
    tok = AutoTokenizer.from_pretrained(MODEL, cache_dir=MODEL_CACHE, src_lang="rus_Cyrl")
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL, cache_dir=MODEL_CACHE).eval()
    eng = tok.convert_tokens_to_ids("eng_Latn")
    out = {}
    for i in range(0, len(texts), 16):
        batch = texts[i:i + 16]
        parts = [split_prefix(t) for t in batch]
        enc = tok([p[1] or t for p, t in zip(parts, batch)], return_tensors="pt", padding=True,
                  truncation=True, max_length=64)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=eng, max_new_tokens=64, num_beams=4)
        for src, (label, _, num), en in zip(batch, parts, tok.batch_decode(gen, skip_special_tokens=True)):
            en = en.strip().rstrip(".") + (f" ({num})" if num else "")
            out[src] = f"{label}: {en}" if label else en
    return out


def main():
    local = "/tmp/epg_for_translate.xml.gz"
    subprocess.run(["scp", "-q", f"{KT}:{REMOTE_EPG}", local], check=True, timeout=120)
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) and "--fresh" not in sys.argv else {}
    todo = [t for t in titles(local) if CYRILLIC.search(t) and t not in cache]
    print(f"{len(todo)} new titles to translate ({len(cache)} cached)", flush=True)
    if todo:
        cache.update(translate(todo))
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["scp", "-q", CACHE, f"{KT}:{REMOTE_OUT}"], check=True, timeout=120)
    print("published", len(cache), "translations")


if __name__ == "__main__":
    sys.exit(main())
