# -*- coding: utf-8 -*-
"""Sklada dokumentacje z plikow Markdown do jednego PDF (Chromium, Playwright).

    python narzedzia\\pdf_dokumentacja.py wynik.pdf plik1.md plik2.md ...

Po co wlasny konwerter zamiast biblioteki: dokumentacja uzywa naglowkow, tabel,
list, obrazkow i kodu - i nic wiecej. Wlasne 90 linii jest tansze niz zaleznosc,
ktora trzeba instalowac na kazdej maszynie, gdzie ma powstac ten plik.

Autor: Mateusz Biernat
"""
from __future__ import annotations

import html
import os
import re
import sys

from playwright.sync_api import sync_playwright

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; color: #111; line-height: 1.5; }
h1 { font-size: 19pt; margin: 0 0 10pt; border-bottom: 2px solid #222; padding-bottom: 5pt; }
h2 { font-size: 14pt; margin: 20pt 0 7pt; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; }
h1 + p, h2 + p { margin-top: 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9pt; }
th, td { border: 1px solid #bbb; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: #eee; font-weight: 600; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f2f2f2; padding: 1pt 3pt; }
pre { background: #f6f6f6; border: 1px solid #ddd; padding: 7pt; font-size: 8.5pt;
      overflow-wrap: break-word; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
img { max-width: 100%; border: 1px solid #ccc; margin: 6pt 0; }
ul, ol { margin: 6pt 0 10pt; padding-left: 18pt; }
li { margin: 2pt 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 16pt 0 8pt; }
.strona { page-break-after: always; }
.strona:last-child { page-break-after: auto; }
h1, h2, h3 { page-break-after: avoid; }
table, pre, img { page-break-inside: avoid; }
"""


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img alt="\1" src="\2">', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    return t


def md_na_html(md: str) -> str:
    out, i = [], 0
    linie = md.split("\n")
    while i < len(linie):
        w = linie[i]

        if w.startswith("```"):                                   # blok kodu
            i += 1
            buf = []
            while i < len(linie) and not linie[i].startswith("```"):
                buf.append(html.escape(linie[i]))
                i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            i += 1
            continue

        if re.match(r'^\|.*\|\s*$', w):                           # tabela
            wiersze = []
            while i < len(linie) and re.match(r'^\|.*\|\s*$', linie[i]):
                wiersze.append([c.strip() for c in linie[i].strip().strip("|").split("|")])
                i += 1
            if len(wiersze) >= 2 and all(set(c) <= set("-: ") for c in wiersze[1]):
                naglowek, tresc = wiersze[0], wiersze[2:]
            else:
                naglowek, tresc = None, wiersze
            t = ["<table>"]
            if naglowek:
                t.append("<tr>" + "".join("<th>%s</th>" % inline(c) for c in naglowek) + "</tr>")
            for r in tresc:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</table>")
            out.append("".join(t))
            continue

        m = re.match(r'^(#{1,4})\s+(.*)$', w)                     # naglowek
        if m:
            poziom = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (poziom, inline(m.group(2)), poziom))
            i += 1
            continue

        if re.match(r'^\s*[-*]\s+', w) or re.match(r'^\s*\d+\.\s+', w):   # lista
            uporzadkowana = bool(re.match(r'^\s*\d+\.\s+', w))
            tag = "ol" if uporzadkowana else "ul"
            elementy = []
            while i < len(linie) and (re.match(r'^\s*[-*]\s+', linie[i]) or re.match(r'^\s*\d+\.\s+', linie[i])):
                elementy.append(re.sub(r'^\s*(?:[-*]|\d+\.)\s+', '', linie[i]))
                i += 1
                # ciag dalszy punktu: wciecie dwoma spacjami wystarczy, bo tak
                # zapisuje sie zawijane punkty listy w Markdownie
                while (i < len(linie) and linie[i].startswith("  ")
                       and linie[i].strip()
                       and not re.match(r'^\s*(?:[-*]|\d+\.)\s+', linie[i])):
                    elementy[-1] += " " + linie[i].strip()
                    i += 1
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(e) for e in elementy), tag))
            continue

        if w.strip() == "---":
            out.append("<hr>")
            i += 1
            continue

        if not w.strip():
            i += 1
            continue

        akapit = [w]                                              # akapit
        i += 1
        while i < len(linie) and linie[i].strip() and not re.match(r'^(#|\||```|\s*[-*]\s|\s*\d+\.\s)', linie[i]):
            akapit.append(linie[i])
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(akapit)))

    return "\n".join(out)


def zbuduj(wynik: str, pliki: list[str]):
    sekcje = []
    for p in pliki:
        with open(p, encoding="utf-8") as fh:
            sekcje.append('<div class="strona">%s</div>' % md_na_html(fh.read()))
    doc = ("<!doctype html><html lang=\"pl\"><head><meta charset=\"utf-8\">"
           "<style>%s</style></head><body>%s</body></html>" % (CSS, "\n".join(sekcje)))

    katalog = os.path.dirname(os.path.abspath(pliki[0]))
    tmp = os.path.join(katalog, "_tmp_dokumentacja.html")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(doc)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto("file:///" + tmp.replace("\\", "/"))
            page.pdf(path=wynik, format="A4", print_background=True)
            browser.close()
    finally:
        os.remove(tmp)
    print("zapisano %s (%d kB)" % (wynik, os.path.getsize(wynik) // 1024))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("uzycie: pdf_dokumentacja.py wynik.pdf plik1.md [plik2.md ...]")
    zbuduj(sys.argv[1], sys.argv[2:])
