# -*- coding: utf-8 -*-
"""Renderuje pliki .bpmn do PNG przez bpmn-js w Chromium (Playwright).

Po co: plik BPMN jest zrodlem prawdy, ale do repozytorium, dokumentacji i portfolio
potrzebny jest obrazek. Render idzie z tego samego pliku, wiec podglad nigdy nie
rozjedzie sie z modelem.

    python narzedzia\\render_bpmn.py [sciezka.bpmn ...]

Bez argumentow renderuje wszystkie diagramy w repozytorium.

Autor: Mateusz Biernat
"""
from __future__ import annotations

import glob
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<script src="https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-viewer.development.js"></script>
<style>
  html, body { margin: 0; padding: 0; background: #ffffff; }
  #canvas { width: 4200px; height: 2600px; background: #ffffff; }
  .bjs-powered-by { display: none; }
</style>
</head><body><div id="canvas"></div>
<script>
  window.viewer = null;
  window.renderDiagram = async function (xml) {
    // kazdy plik dostaje czysty kontener - inaczej drugi diagram doklada sie do pierwszego
    document.getElementById('canvas').remove();
    const div = document.createElement('div');
    div.id = 'canvas';
    document.body.appendChild(div);
    window.viewer = new BpmnJS({ container: '#canvas' });
    await window.viewer.importXML(xml);
    const box = window.viewer.get('canvas').viewbox();
    return { w: Math.ceil(box.inner.width), h: Math.ceil(box.inner.height),
             x: Math.floor(box.inner.x), y: Math.floor(box.inner.y) };
  };
  // skala 1:1 i ramka 40 px dookola tresci - inaczej PNG ma pol obrazka pustego tla
  window.refit = function (b) {
    window.viewer.get('canvas').viewbox({
      x: b.x - 40, y: b.y - 40, width: b.w + 80, height: b.h + 80 });
  };
</script></body></html>
"""


def render(pliki):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 2200, "height": 1400},
                                device_scale_factor=2)
        bledy = []
        page.on("pageerror", lambda e: bledy.append(str(e)))
        page.set_content(HTML)
        page.wait_for_function("() => typeof BpmnJS !== 'undefined'", timeout=30000)

        for sciezka in pliki:
            with open(sciezka, encoding="utf-8") as fh:
                xml = fh.read()
            bledy.clear()
            wynik = page.evaluate("xml => window.renderDiagram(xml)", xml)
            if bledy:
                print("BLAD renderu %s: %s" % (sciezka, bledy[0]))
                continue
            page.evaluate(
                "size => { const c = document.getElementById('canvas');"
                " c.style.width = (size.w + 80) + 'px';"
                " c.style.height = (size.h + 80) + 'px'; }", wynik)
            page.evaluate("b => window.refit(b)", wynik)
            png = os.path.splitext(sciezka)[0] + ".png"
            page.locator("#canvas").screenshot(path=png)
            print("render %s -> %dx%d px" % (os.path.basename(png), wynik["w"], wynik["h"]))
        browser.close()


if __name__ == "__main__":
    pliki = sys.argv[1:]
    if not pliki:
        pliki = sorted(glob.glob(os.path.join(ROOT, "**", "*.bpmn"), recursive=True))
    if not pliki:
        raise SystemExit("nie znalazlem zadnego pliku .bpmn")
    render(pliki)
