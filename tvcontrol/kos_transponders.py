#!/usr/bin/env python3
"""Annotate the TV channel list with KingOfSat data for Astra 19.2E and pick the guest channels.

usage: kos_transponders.py kos_pos-19.2E.html channels.tsv [--guest] > out.tsv
  out columns: number, name, transponder ("12148 H 27500"), country, genre, encryption,
               audio languages, radio(1/0)
  --guest: keep only free, German-language channels from DE/AT/CH without shopping/adult ones
"""
import html
import re
import sys

SHOPPING = re.compile(r"teleshopping|shopping|adult|erotic", re.I)
SHOP_NAMES = re.compile(r"\b(QVC|HSE|Juwelo|1-2-3\.tv|sonnenklar|Channel21|Mediashop|Astro ?TV|"
                        r"Sex\w*|Erotik|Kontakte|EROTIKA|Beate-Uhse|Blue Hustler|Dorcel|Babestation\w*|"
                        r"Dates|Girls|Test-\w+)\b", re.I)
# religious channels (churches, bible, preachers) are not wanted in any guest list
RELIGIOUS_NAME = re.compile(r"\b(Bibel\w*|Bible\w*|Biblia|Kirche\w*|Church\w*|Gospel|Hope ?TV|Horeb|Radio Maria|RADIO MARIA|"
                            r"EWTN|K-TV|God ?TV|Gott\w*|Christ(?!mas)\w*|Jesus|Glaube\w*|Catholic|Katholisch\w*|Evangel\w*|"
                            r"Daystar|TBN|Trinity|Angel ?TV|Spirit ?TV|SonLife|Neue Zeit|Immaculata|Dieu|Adventist\w*|"
                            r"Faith|Pray\w*|Tabernacle|Shalom|Worship|Messiah|Apostol\w*|Vatican\w*|Telepace|Padre Pio|"
                            r"Lourdes|Madonna|Islam\w*|Quran|Koran|Sunnah|Torah|Hindu\w*|Bhakti|Aastha|Sanskar)\b", re.I)
RELIGIOUS_GROUP = re.compile(r"relig", re.I)
COUNTRIES = {"germany", "austria", "switzerland"}
# German-language channels registered under another country
ALLOW_FOREIGN = re.compile(r"^arte\b", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9äöü]", "", s.lower())


def cell(row, cls):
    m = re.search(r'<td class="[^"]*\b' + cls + r'\b[^"]*">(.*?)</td>', row, re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip() if m else ""


def channels(page):
    """{normalised name: dict(tp, country, genre, enc, langs, radio)} in page order (first hit wins)."""
    out, tp = {}, None
    token = re.compile(r'<td class="n?bld">(\d+)(?:\.\d+)? ([HV])</td>.*?<td><a class="bld">(\d+)</a></td>'
                       r'|<tr data-channel-id="\d*">(.*?)</tr>', re.S)
    for m in token.finditer(page):
        if m.group(1):
            tp = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            continue
        row = m.group(4)
        if not tp:
            continue
        sid = re.search(r'title="Id: ([^"]*)"', row)
        info = {
            "tp": tp,
            "country": cell(row, "pays"),
            "genre": cell(row, "genre"),
            "enc": cell(row, r"encryption-label") or ("Clear" if "Clear" in row else ""),
            "langs": " ".join(sorted(set(re.findall(r'<font color="blue">(\w+)</font>', row)))),
            "radio": "audio.png" in row,
        }
        enc = re.search(r'class="encryption-label">([^<]*)<', row)
        info["enc"] = enc.group(1).strip() if enc else ""
        names = [sid.group(1) if sid else None, cell(row, "ch")]
        for name in names:
            if name:
                out.setdefault(norm(name), info)
    return out


def guest_ok(name, i):
    return (i["enc"] == "Clear" and "ger" in i["langs"].split()
            # radio rows carry no country on KingOfSat; TV channels must name DE/AT/CH
            and (i["country"].lower() in COUNTRIES or (i["radio"] and not i["country"])
                 or ALLOW_FOREIGN.search(name))
            and not SHOPPING.search(i["genre"]) and not SHOP_NAMES.search(name)
            and not RELIGIOUS_GROUP.search(i["genre"]) and not RELIGIOUS_NAME.search(name)
            and not re.match(r"^(ALT_|\.$)", name))


def main(page_path, tsv_path, guest):
    info = channels(open(page_path, encoding="utf-8", errors="replace").read())
    for line in open(tsv_path, encoding="utf-8"):
        num, _, name = line.rstrip("\n").partition("\t")
        i = info.get(norm(name))
        if guest and (not i or not guest_ok(name, i)):
            continue
        i = i or {"tp": "", "country": "", "genre": "", "enc": "", "langs": "", "radio": False}
        print("\t".join([num, name, i["tp"], i["country"], i["genre"], i["enc"], i["langs"],
                         "1" if i["radio"] else "0"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--guest" in sys.argv)
