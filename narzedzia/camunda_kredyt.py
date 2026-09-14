# -*- coding: utf-8 -*-
"""Obsluga procesu kredytowego w Camunda 8: wdrozenie, start i workery.

Wszystko idzie przez **REST API v2** silnika (http://localhost:8080/v2), bez
gRPC i bez dodatkowych bibliotek - ten sam protokol, ktorym proces rozmawia
z uslugami wewnetrznymi w specyfikacji integracji.

    python narzedzia\\camunda_kredyt.py deploy     # wdraza model
    python narzedzia\\camunda_kredyt.py start      # publikuje komunikat = nowa sprawa
    python narzedzia\\camunda_kredyt.py worker     # obsluguje zadania uslugowe
    python narzedzia\\camunda_kredyt.py zadania    # pokazuje zadania uzytkownika

Dane logowania: zmienne C8_USER i C8_PASS (domyslnie demo/demo).

Autor: Mateusz Biernat
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

BAZA = os.environ.get("C8_URL", "http://localhost:8080/v2")
USER = os.environ.get("C8_USER", "demo")
PASS = os.environ.get("C8_PASS", "demo")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "01-proces-kredytowy", "diagramy",
                     "wniosek-kredytowy-TO-BE-camunda.bpmn")

ID_PROCESU = "wniosek-kredytowy"
KOMUNIKAT_STARTOWY = "wniosek-kredytowy-zlozony"


def _naglowki(extra=None):
    token = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
    h = {"Authorization": "Basic " + token}
    h.update(extra or {})
    return h


def zapytanie(sciezka, dane=None, metoda=None, surowe=None, content_type=None):
    url = BAZA + sciezka
    body = surowe if surowe is not None else (
        json.dumps(dane).encode("utf-8") if dane is not None else None)
    naglowki = _naglowki({"Content-Type": content_type or "application/json"} if body else None)
    req = urllib.request.Request(url, data=body, headers=naglowki,
                                 method=metoda or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as odp:
            tresc = odp.read().decode("utf-8")
            return json.loads(tresc) if tresc.strip() else {}
    except urllib.error.HTTPError as blad:
        tresc = blad.read().decode("utf-8", "replace")
        raise SystemExit("HTTP %s dla %s\n%s" % (blad.code, sciezka, tresc[:600]))
    except urllib.error.URLError as blad:
        raise SystemExit("brak polaczenia z silnikiem (%s): %s\n"
                         "Uruchom Camunda 8 Run i sprobuj ponownie." % (BAZA, blad.reason))


# --------------------------------------------------------------- wdrozenie
def deploy():
    granica = "----camunda" + str(int(time.time()))
    with open(MODEL, "rb") as fh:
        plik = fh.read()
    czesci = (
        ("--%s\r\n" % granica).encode()
        + b'Content-Disposition: form-data; name="resources"; filename="'
        + os.path.basename(MODEL).encode() + b'"\r\n'
        + b"Content-Type: application/xml\r\n\r\n" + plik + b"\r\n"
        + ("--%s--\r\n" % granica).encode()
    )
    wynik = zapytanie("/deployments", surowe=czesci,
                      content_type="multipart/form-data; boundary=" + granica)
    for el in wynik.get("deployments", []):
        proc = el.get("processDefinition") or {}
        if proc:
            print("wdrozono %s, wersja %s (klucz %s)" % (
                proc.get("processDefinitionId"), proc.get("version"),
                proc.get("processDefinitionKey")))
    return wynik


# --------------------------------------------------------------- start sprawy
PRZYKLAD = {
    "pesel": "90010112345",
    "imie": "Anna",
    "nazwisko": "Nowak",
    "kwota": 45000,
    "okresMiesiecy": 48,
    "cel": "KONSOLIDACJA",
    "dochodNetto": 7800,
    "zrodloDochodu": "UMOWA_O_PRACE",
    "stazMiesiecy": 26,
    "zgodaBik": True,
}


def start(nadpisania=None):
    zmienne = dict(PRZYKLAD)
    zmienne.update(nadpisania or {})
    wynik = zapytanie("/messages/publication", {
        "name": KOMUNIKAT_STARTOWY,
        "correlationKey": zmienne["pesel"],
        "timeToLive": 0,
        "variables": zmienne,
    })
    print("nowa sprawa: kwota %s zl, dochod %s zl (klucz komunikatu %s)" % (
        zmienne["kwota"], zmienne["dochodNetto"], wynik.get("messageKey")))
    return wynik


# --------------------------------------------------------------- workery
def _walidacja(v):
    wymagane = ["pesel", "kwota", "okresMiesiecy", "dochodNetto", "zrodloDochodu"]
    braki = [p for p in wymagane if not v.get(p)]
    return {"daneKompletne": not braki and bool(v.get("zgodaBik")), "brakujacePola": braki}


def _rejestry(v):
    # Zaslepka rejestru: wynik zalezy od PESEL, wiec ta sama sprawa daje ten sam
    # raport przy kazdym przebiegu. Losowanie utrudnialoby porownanie przebiegow.
    cyfra = int(str(v.get("pesel", "0"))[-1])
    return {
        "scoringBik": 600 + cyfra * 20,
        "sumaRatMiesiecznych": 400 + cyfra * 90,
        "wpisyNegatywne": 1 if cyfra >= 8 else 0,
    }


def _scoring(v):
    rata = v["kwota"] / max(v["okresMiesiecy"], 1)
    dti = 100.0 * (rata + v.get("sumaRatMiesiecznych", 0)) / max(v["dochodNetto"], 1)
    punkty = 0
    punkty += 35 if v.get("scoringBik", 0) >= 700 else 20 if v.get("scoringBik", 0) >= 620 else 5
    punkty += 25 if dti <= 30 else 15 if dti <= 45 else 3
    punkty += 20 if v.get("stazMiesiecy", 0) >= 24 else 10
    punkty += 15 if not v.get("wpisyNegatywne") else 0
    punkty += 5
    klasa = ("A" if punkty >= 85 else "B" if punkty >= 70 else
             "C" if punkty >= 55 else "D" if punkty >= 40 else "E")
    return {"punktacja": punkty, "klasaRyzyka": klasa, "dti": round(dti, 2),
            "wersjaModelu": "SC-2026.02"}


def _decyzja_auto(v):
    return {"decyzja": "POZYTYWNA", "typDecyzji": "AUTOMATYCZNA",
            "kwotaPrzyznana": v["kwota"], "uzasadnienie":
            "Klasa ryzyka %s, kwota w progu decyzji automatycznej." % v.get("klasaRyzyka")}


def _odmowa_auto(v):
    return {"decyzja": "NEGATYWNA", "typDecyzji": "AUTOMATYCZNA", "uzasadnienie":
            "Punktacja %s, klasa ryzyka %s - ponizej progu polityki kredytowej."
            % (v.get("punktacja"), v.get("klasaRyzyka"))}


def _umowa(v):
    return {"numerUmowy": "UM/2026/09/%s" % str(v.get("pesel", "0"))[-6:],
            "oprocentowanie": 9.99}


def _powiadomienie(v):
    return {"powiadomienieWyslane": True}


def _uruchomienie(v):
    return {"uruchomiono": True, "rachunekWyplaty": "PL61109010140000071219812874"}


OBSLUGA = {
    "walidacja-wniosku": _walidacja,
    "pobranie-raportow": _rejestry,
    "scoring-kredytowy": _scoring,
    "decyzja-automatyczna": _decyzja_auto,
    "odmowa-automatyczna": _odmowa_auto,
    "generowanie-umowy": _umowa,
    "powiadomienie-klienta": _powiadomienie,
    "uruchomienie-kredytu": _uruchomienie,
}


def worker(rundy=0):
    print("worker startuje, obsluguje %d typow zadan. Ctrl+C konczy." % len(OBSLUGA))
    runda = 0
    while True:
        runda += 1
        zrobione = 0
        for typ, funkcja in OBSLUGA.items():
            odp = zapytanie("/jobs/activation", {
                "type": typ,
                "maxJobsToActivate": 10,
                "timeout": 30000,
                "worker": "worker-kredytowy",
                "requestTimeout": 1000,
            })
            for zadanie in odp.get("jobs", []):
                zmienne = zadanie.get("variables", {})
                wynik = funkcja(zmienne)
                zapytanie("/jobs/%s/completion" % zadanie["jobKey"], {"variables": wynik})
                print("  %-22s -> %s" % (typ, json.dumps(wynik, ensure_ascii=False)[:110]))
                zrobione += 1
        if not zrobione:
            time.sleep(1)
        if rundy and runda >= rundy:
            return


# --------------------------------------------------------------- zadania ludzi
def zadania():
    odp = zapytanie("/user-tasks/search", {"filter": {"state": "CREATED"},
                                           "page": {"limit": 30}})
    pozycje = odp.get("items", [])
    if not pozycje:
        print("brak otwartych zadan uzytkownika")
        return
    print("%-28s %-22s %s" % ("ZADANIE", "GRUPA", "KLUCZ"))
    for z in pozycje:
        print("%-28s %-22s %s" % (
            z.get("name") or z.get("elementId"),
            ",".join(z.get("candidateGroups") or []),
            z.get("userTaskKey")))


def zakoncz_zadanie(klucz, zmienne=None):
    zapytanie("/user-tasks/%s/completion" % klucz, {"variables": zmienne or {}})
    print("zadanie %s zakonczone" % klucz)


if __name__ == "__main__":
    polecenie = sys.argv[1] if len(sys.argv) > 1 else "status"
    if polecenie == "deploy":
        deploy()
    elif polecenie == "start":
        nadpis = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
        start(nadpis)
    elif polecenie == "worker":
        worker(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    elif polecenie == "zadania":
        zadania()
    elif polecenie == "zakoncz":
        zakoncz_zadanie(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
