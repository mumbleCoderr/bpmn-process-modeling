# -*- coding: utf-8 -*-
"""Zrzut ekranu z Camunda Operate - dowod, ze proces realnie sie wykonal.

Diagram w repozytorium pokazuje, jak proces ma dzialac. Ten zrzut pokazuje,
ze zadzialal: instancje, sciezki przejscia i stan koncowy w silniku.

    python narzedzia\\zrzut_operate.py

Autor: Mateusz Biernat
"""
from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WYNIK = os.path.join(ROOT, "01-proces-kredytowy", "diagramy", "uruchomienie")
BAZA = os.environ.get("C8_OPERATE", "http://localhost:8080/operate")
USER = os.environ.get("C8_USER", "demo")
PASS = os.environ.get("C8_PASS", "demo")


def _instancja_decyzji(id_decyzji):
    """Klucz ostatniej ocenionej instancji danej decyzji (REST API v2)."""
    import base64, json, urllib.request
    zadanie = json.dumps({"filter": {"decisionDefinitionId": id_decyzji},
                          "page": {"limit": 1}}).encode()
    token = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
    req = urllib.request.Request(
        BAZA.split("/operate")[0] + "/v2/decision-instances/search",
        data=zadanie, method="POST",
        headers={"Authorization": "Basic " + token,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as odp:
        dane = json.loads(odp.read().decode())
    pozycje = dane.get("items") or []
    return pozycje[0].get("decisionEvaluationInstanceKey") if pozycje else None


def _zamknij_modal(strona):
    """Operate wita powitalnym oknem, ktore zaslania diagram na zrzucie."""
    for etykieta in ["Got it", "Continue", "Close"]:
        przycisk = strona.get_by_role("button", name=etykieta)
        if przycisk.count():
            przycisk.first.click()
            strona.wait_for_timeout(1500)
            return


def zrzut():
    os.makedirs(WYNIK, exist_ok=True)
    with sync_playwright() as pw:
        przegladarka = pw.chromium.launch()
        strona = przegladarka.new_page(viewport={"width": 1600, "height": 950},
                                       device_scale_factor=2)
        strona.goto(BAZA, wait_until="domcontentloaded")
        strona.wait_for_timeout(2500)

        if strona.locator("input[name='username']").count():
            strona.fill("input[name='username']", USER)
            strona.fill("input[name='password']", PASS)
            strona.click("button[type='submit']")
            strona.wait_for_timeout(4000)

        _zamknij_modal(strona)

        # lista instancji procesu
        strona.goto(BAZA + "/processes?active=true&incidents=true&completed=true"
                           "&canceled=true&process=wniosek-kredytowy&version=1",
                    wait_until="domcontentloaded")
        strona.wait_for_timeout(6000)
        p1 = os.path.join(WYNIK, "operate-instancje.png")
        strona.screenshot(path=p1)
        print("zapisano", p1)

        # widok pojedynczej instancji - podswietlona sciezka przejscia
        wiersze = strona.locator("a[href*='/processes/']")
        for i in range(wiersze.count()):
            href = wiersze.nth(i).get_attribute("href") or ""
            if "/processes/" in href and href.rstrip("/").split("/")[-1].isdigit():
                # href bywa juz z przedrostkiem /operate - sklejanie z BAZA dawalo 404
                korzen = BAZA.split("/operate")[0]
                cel = href if href.startswith("http") else korzen + href
                strona.goto(cel, wait_until="domcontentloaded")
                strona.wait_for_timeout(6000)
                _zamknij_modal(strona)
                p2 = os.path.join(WYNIK, "operate-instancja.png")
                strona.screenshot(path=p2)
                print("zapisano", p2)
                break

        # widok decyzji: tabela decyzyjna z podswietlona regula.
        # Instancje wskazujemy z API, nie klikaniem w liste - lista pokazuje
        # najpierw wyrazenie DTI, a ogladania warta jest tabela punktacji.
        klucz = _instancja_decyzji("punktacja-kredytowa")
        if klucz:
            strona.goto(BAZA + "/decisions/" + klucz, wait_until="domcontentloaded")
            strona.wait_for_timeout(6000)
            _zamknij_modal(strona)
            p3 = os.path.join(WYNIK, "operate-decyzja-dmn.png")
            strona.screenshot(path=p3)
            print("zapisano", p3)
        przegladarka.close()


if __name__ == "__main__":
    try:
        zrzut()
    except Exception as blad:            # zrzut jest dodatkiem, nie warunkiem pracy
        print("nie udalo sie zrobic zrzutu: %s" % blad)
        sys.exit(1)
