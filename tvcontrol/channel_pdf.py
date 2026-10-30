#!/usr/bin/env python3
"""Guest channel list (DE/EN) for the Sharp TV: favourites first, then all channels,
with the Astra 19.2E transponder in the rightmost column.

usage: channel_pdf.py channels_tp.tsv out.pdf   (tsv: number<TAB>name<TAB>"freq pol SR")
"""
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# (section, [(label, regex on the TV's channel name)]); first match in the list wins
FAVOURITES = [
    ("Radio", [
        ("Antenne Bayern", r"^ANTENNE BAYERN$"),
        ("Bayern 1", r"^Bayern 1$"),
        ("Bayern 3", r"^BAYERN 3$"),
        ("BR24", r"^BR24$"),
        ("Rock Antenne", r"^ROCK ANTENNE$"),
        ("Klassik Radio", r"^Klassik Radio$"),
    ]),
    ("TV", [
        ("Das Erste", r"^Das Erste HD$"),
        ("ZDF", r"^ZDF HD$"),
        ("BR", r"^BR Fernsehen S(ü|ue)d HD$"),
        ("arte", r"^arte HD$"),
        ("3sat", r"^3sat HD$"),
        ("phoenix", r"^phoenix HD$"),
        ("ZDFneo", r"^zdf_neo HD$|^ZDFneo HD$"),
        ("ONE", r"^ONE HD$"),
        ("tagesschau24", r"^tagesschau24 HD$"),
        ("RTL", r"^RTL Television$|^RTL Austria$"),
        ("SAT.1", r"^SAT\.1$|^SAT\.1 A$"),
        ("ProSieben", r"^ProSieben$|^ProSieben Austria$"),
        ("VOX", r"^VOX$|^VOX Austria$"),
        ("kabel eins", r"^kabel eins$|^Kabel 1 Austria$"),
        ("n-tv", r"^ntv$|^ntv Austria$"),
    ]),
    ("English", [
        ("BBC News", r"^BBC News$"),
        ("CNN International", r"^CNN Int"),
        ("Sky News", r"^Sky News"),
    ]),
]
# placeholder/alternate feeds that only confuse guests
HIDE = re.compile(r"^(ALT_|\.$)")


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and not HIDE.search(parts[1].strip()):
            rows.append((int(parts[0]), parts[1].strip(), parts[2] if len(parts) > 2 else ""))
    return sorted(set(rows))


def row(c, y, num, name, tp, size=13):
    w, _ = A4
    c.setFont("Helvetica-Bold", size)
    c.drawRightString(38 * mm, y, str(num))
    c.setFont("Helvetica", size)
    c.drawString(44 * mm, y, name)
    c.setFont("Helvetica", size - 3)
    c.setFillGray(0.4)
    c.drawRightString(w - 18 * mm, y, tp)
    c.setFillGray(0)


def main(tsv, out):
    rows = load(tsv)
    c = canvas.Canvas(out, pagesize=A4)
    w, h = A4

    # page 1: favourites
    y = h - 22 * mm
    c.setFont("Helvetica-Bold", 22)
    c.drawString(18 * mm, y, "Senderliste  ·  Channel list")
    y -= 8 * mm
    c.setFont("Helvetica", 10.5)
    c.drawString(18 * mm, y, "Nummer auf der Fernbedienung eintippen  ·  Type the number on the remote")
    y -= 5 * mm
    c.drawString(18 * mm, y, "Handy / phone (Haus-WLAN / home Wi-Fi): https://tv.heissa.de")
    y -= 5 * mm
    c.drawString(18 * mm, y, "Satellit / satellite: Astra 19,2° Ost (Live-TV)")
    c.setFont("Helvetica", 8.5)
    c.setFillGray(0.4)
    c.drawRightString(w - 18 * mm, y, "Transponder: MHz Pol. SR")
    c.setFillGray(0)
    y -= 10 * mm
    missing = []
    for section, items in FAVOURITES:
        hits = []
        for label, pat in items:
            m = next((r for r in rows if re.search(pat, r[1], re.I)), None)
            if m:
                hits.append((label, m))
            else:
                missing.append(label)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(18 * mm, y, section)
        y -= 7 * mm
        if not hits:
            c.setFont("Helvetica-Oblique", 11)
            c.drawString(44 * mm, y, "folgt  ·  coming soon")
            y -= 7 * mm
        for label, (num, name, tp) in hits:
            row(c, y, num, label + ("  (Standard / default)" if label == "Antenne Bayern" else ""), tp)
            y -= 6.8 * mm
        y -= 4 * mm
    c.showPage()

    # full list, one column, transponder on the right
    line_h, top, bottom = 5.2 * mm, h - 25 * mm, 15 * mm
    per_page = int((top - bottom) / line_h)
    for start in range(0, len(rows), per_page):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, h - 15 * mm, "Alle Sender · All channels (Astra 19,2° E)")
        for i, (num, name, tp) in enumerate(rows[start:start + per_page]):
            row(c, top - i * line_h, num, name, tp, size=10.5)
        c.showPage()
    c.save()
    print(f"{out}: {len(rows)} channels, favourites missing: {missing or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
