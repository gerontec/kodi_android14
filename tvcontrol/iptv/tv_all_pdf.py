#!/usr/bin/env python3
"""tv_all.pdf: one section (one or more pages) per subdomain.

  sat.heissa.de  guest selection of the Astra list (Live TV programme numbers)
  de/at/ch/it/us.heissa.de  Kodi IPTV lists; number = Kodi channel number (order in de/all.m3u)

usage: tv_all_pdf.py selection.tsv m3u_dir tv_all.pdf
"""
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

SECTIONS = [
    ("de", "de.heissa.de", "Deutschland · Kabel (FRITZ!Box) + IPTV  (Kodi)"),
    ("at", "at.heissa.de", "Österreich · IPTV  (Kodi)"),
    ("ch", "ch.heissa.de", "Schweiz · IPTV  (Kodi)"),
    ("it", "it.heissa.de", "Italia · IPTV  (Kodi)"),
    ("us", "us.heissa.de", "USA · IPTV  (Kodi)"),
    ("fr", "fr.heissa.de", "France · IPTV via French IP  (Kodi)"),
    ("ru", "ru.heissa.de", "Russia · IPTV via US exit (no EU blocking)  (Kodi)"),
]
W, H = A4
PROJECT = "https://github.com/gerontec/kodi_android14"


def m3u(path):
    out, info = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            info = line
        elif line and not line.startswith("#") and info:
            g = re.search(r'group-title="([^"]*)"', info)
            out.append((info.rpartition(",")[2].strip(), g.group(1) if g else "", line))
            info = None
    return out


def page_header(c, host, title, cont=False):
    # project link top right on every page (clickable in the PDF)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.1, 0.3, 0.7)
    c.drawRightString(W - 15 * mm, H - 10 * mm, PROJECT)
    tw = c.stringWidth(PROJECT, "Helvetica", 8)
    c.linkURL(PROJECT, (W - 15 * mm - tw, H - 11 * mm, W - 15 * mm, H - 7.5 * mm), relative=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(15 * mm, H - 18 * mm, host + ("  (Forts.)" if cont else ""))
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, H - 24 * mm, title)
    c.setStrokeGray(0.7)
    c.line(15 * mm, H - 26.5 * mm, W - 15 * mm, H - 26.5 * mm)
    return H - 33 * mm


def section(c, host, title, rows, bold=()):
    """rows: list of (group, number, name); two columns, group headings, continues on new pages."""
    # keep groups together, in order of first appearance; entry order inside a group unchanged
    order = {}
    for g, _, _ in rows:
        order.setdefault(g, len(order))
    rows = sorted(rows, key=lambda r: order[r[0]])
    y_top = page_header(c, host, title)
    col_w, line_h, bottom = (W - 30 * mm) / 2, 4.6 * mm, 14 * mm
    col, y, last_group = 0, y_top, None

    def newline():
        nonlocal col, y, y_top
        y -= line_h
        if y < bottom:
            if col == 0:
                col, y = 1, y_top
            else:
                c.showPage()
                y_top = page_header(c, host, title, cont=True)
                col, y = 0, y_top

    for group, num, name in rows:
        x = 15 * mm + col * col_w
        if group != last_group:
            if last_group is not None:
                newline()
            x = 15 * mm + col * col_w
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, group)
            newline()
            x = 15 * mm + col * col_w
            last_group = group
        b = name in bold
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(x + 10 * mm, y, str(num))
        c.setFont("Helvetica-Bold" if b else "Helvetica", 8.5)
        c.drawString(x + 12 * mm, y, name[:46] + ("  (Standard)" if b else ""))
        newline()
    c.showPage()


def main(sel_path, m3u_dir, out):
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle("tv_all")
    # sat: Live TV numbers, grouped TV / Radio
    sat = []
    for line in open(sel_path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 8 and p[0].isdigit():
            sat.append(("Radio" if p[7] == "1" else "TV", int(p[0]), p[1]))
    sat.sort(key=lambda r: (r[0] != "TV",))
    section(c, "sat.heissa.de", "Satellit Astra 19,2° Ost · Live-TV · Nummer auf der Fernbedienung eintippen",
            sat, bold=("arte HD", "ANTENNE BAYERN"))
    # Kodi numbers follow the order of de/all.m3u (iptvsimple numberByOrder, start 1)
    kodi_no = {url: i + 1 for i, (_, _, url) in enumerate(m3u(f"{m3u_dir}/de/all.m3u"))}
    for cc, host, title in SECTIONS:
        rows = [(g, kodi_no.get(url, "-"), name) for name, g, url in m3u(f"{m3u_dir}/{cc}/list.m3u")]
        if rows:
            section(c, host, title, rows)
    c.save()
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
