#!/usr/bin/env python3
"""Guest channel list (DE/EN) for the Sharp TV, grouped TV / Radio, Astra 19.2E transponder in the
rightmost column.

usage: channel_pdf.py selection.tsv out.pdf   (tsv from guest_selection.py)
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


DEFAULTS = re.compile(r"^ANTENNE BAYERN$|^arte HD$")


def row(c, y, num, name, tp, size=13, bold=False):
    w, _ = A4
    c.setFont("Helvetica-Bold", size + (1 if bold else 0))
    c.drawRightString(38 * mm, y, str(num))
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size + (1 if bold else 0))
    c.drawString(44 * mm, y, name)
    c.setFont("Helvetica", size - 3)
    c.setFillGray(0.4)
    c.drawRightString(w - 18 * mm, y, tp)
    c.setFillGray(0)


def main(tsv, out):
    """One list (max ~50 rows from guest_selection.py), grouped TV / Radio, transponder on the right."""
    groups = {"TV": [], "Radio": []}
    for line in open(tsv, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2 and p[0].isdigit():
            groups["Radio" if len(p) >= 8 and p[7] == "1" else "TV"].append((int(p[0]), p[1], p[2] if len(p) > 2 else ""))
    c = canvas.Canvas(out, pagesize=A4)
    w, h = A4

    def header():
        y = h - 20 * mm
        c.setFont("Helvetica-Bold", 20)
        c.drawString(18 * mm, y, "Senderliste  ·  Channel list")
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        c.drawString(18 * mm, y, "Nummer auf der Fernbedienung eintippen  ·  Type the number on the remote")
        y -= 4.5 * mm
        c.drawString(18 * mm, y, "Handy / phone (Haus-WLAN / home Wi-Fi): https://tv.heissa.de  ·  Astra 19,2° Ost")
        c.setFont("Helvetica", 8)
        c.setFillGray(0.4)
        c.drawRightString(w - 18 * mm, y, "Transponder: MHz Pol. SR")
        c.setFillGray(0)
        return y - 8 * mm

    y = header()
    line_h = 5.6 * mm
    for section in ("TV", "Radio"):
        rows = groups[section]
        if not rows:
            continue
        if y < 30 * mm:
            c.showPage(); y = header()
        c.setFont("Helvetica-Bold", 13)
        c.drawString(18 * mm, y, section)
        y -= 6.5 * mm
        for num, name, tp in rows:
            if y < 15 * mm:
                c.showPage(); y = header()
            dflt = bool(DEFAULTS.search(name))
            row(c, y, num, name + ("   (Standard / default)" if dflt else ""), tp, size=11, bold=dflt)
            y -= line_h
        y -= 4 * mm
    c.showPage()
    c.save()
    print(f"{out}: {len(groups['TV'])} TV + {len(groups['Radio'])} radio")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
