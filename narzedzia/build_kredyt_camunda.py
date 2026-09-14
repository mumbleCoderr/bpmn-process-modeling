# -*- coding: utf-8 -*-
"""Wariant wykonywalny procesu kredytowego dla Camunda 8 (Zeebe).

Model biznesowy i wykonywalny to **ten sam przebieg**, a nie dwa rownolegle
diagramy: skrypt bierze specyfikacje z `build_kredyt.to_be()` i doklada do niej
warstwe techniczna - typy zadan dla workerow, wyrazenia FEEL na bramkach,
grupy odbiorcow zadan i czas trwania timera. Dzieki temu poprawka w procesie
robi sie raz, a nie w dwoch plikach, ktore po tygodniu i tak sie rozjezdzaja.

    python narzedzia\\build_kredyt_camunda.py

Autor: Mateusz Biernat
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_kredyt import OUT, to_be, zapisz  # noqa: E402

# --- warstwa techniczna: id wezla -> typ zadania dla workera ---
TYPY_ZADAN = {
    "T_waliduj": "walidacja-wniosku",
    "T_bik": "pobranie-raportow",
    "T_scoring": "scoring-kredytowy",
    "T_auto": "decyzja-automatyczna",
    "T_odmowa_auto": "odmowa-automatyczna",
    "T_umowa": "generowanie-umowy",
    "T_powiadom": "powiadomienie-klienta",
    "T_uruchom": "uruchomienie-kredytu",
}

# --- zadania uzytkownika: kto je widzi na liscie w Tasklist ---
GRUPY = {
    "T_uzupelnij": "doradcy",
    "T_podpis": "doradcy",
    "T_analiza": "analitycy-ryzyka",
    "T_dec_analityk": "analitycy-ryzyka",
    "T_komitet": "komitet-kredytowy",
}

# --- warunki na bramkach (FEEL). Klucz: (bramka, cel) ---
WARUNKI = {
    ("T_gkomplet", "T_bik"): "=daneKompletne = true",
    ("T_gsciezka", "T_auto"): '=klasaRyzyka in ("A","B") and kwota <= 50000',
    ("T_gsciezka", "T_odmowa_auto"): '=klasaRyzyka = "E"',
    ("T_glimit", "T_komitet"): "=kwota > 100000",
    ("T_gdecyzja", "T_umowa"): '=decyzja = "POZYTYWNA"',
}

# --- przeplywy domyslne: bramka -> cel. Kazda bramka rozgalezialaca musi go miec,
#     inaczej instancja staje w miejscu, gdy zaden warunek nie jest spelniony ---
DOMYSLNE = {
    "T_gkomplet": "T_uzupelnij",
    "T_gsciezka": "T_analiza",
    "T_glimit": "T_dec_analityk",
    "T_gdecyzja": "T_powiadom",
}


def camunda():
    d = to_be()
    d.zeebe = True
    d.id = "ToBeCamunda"

    bank = [p for p in d.pools if p.process_id][0]
    bank.process_id = "wniosek-kredytowy"

    for n in bank.nodes:
        if n.id in TYPY_ZADAN:
            n.job_type = TYPY_ZADAN[n.id]
        if n.id in GRUPY:
            n.candidate_groups = GRUPY[n.id]
        if n.id == "T_termin":
            n.timer = "P14D"
        if n.id == "T_start":
            n.message_name = "wniosek-kredytowy-zlozony"

    for f in bank.flows:
        klucz = (f.src, f.dst)
        if klucz in WARUNKI:
            f.condition = WARUNKI[klucz]
        if DOMYSLNE.get(f.src) == f.dst:
            f.default = True

    braki = [g for g in DOMYSLNE if not any(
        f.src == g and f.default for f in bank.flows)]
    if braki:
        raise SystemExit("bramki bez przeplywu domyslnego: %s" % ", ".join(braki))

    return d


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    zapisz(camunda(), "wniosek-kredytowy-TO-BE-camunda.bpmn")
