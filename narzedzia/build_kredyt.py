# -*- coding: utf-8 -*-
"""Buduje diagramy BPMN 2.0 procesu obslugi wniosku kredytowego (AS-IS i TO-BE).

Uruchomienie:
    python narzedzia\\build_kredyt.py

Autor: Mateusz Biernat
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_bpmn import Diagram, Flow, Lane, Node, sanity  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "01-proces-kredytowy", "diagramy")


def _flows(pool, pairs):
    for i, item in enumerate(pairs, start=1):
        src, dst = item[0], item[1]
        name = item[2] if len(item) > 2 else ""
        pool.flows.append(Flow("F_%s_%d" % (pool.process_id, i), src, dst, name))


# ---------------------------------------------------------------- AS-IS
def as_is() -> Diagram:
    d = Diagram("AsIs", "Obsluga wniosku kredytowego - stan obecny (AS-IS)", cols=13)

    klient = d.pool("P_Klient", "Klient")
    bank = d.pool("P_Bank", "Bank - obsluga wniosku kredytowego (AS-IS)", "Proc_AsIs")
    ext = d.pool("P_Bik", "BIK / KRD (portal WWW)")

    bank.lanes = [
        Lane("L_Doradca", "Doradca kredytowy (oddzial)"),
        Lane("L_Analityk", "Analityk ryzyka kredytowego"),
        Lane("L_Komitet", "Komitet kredytowy"),
    ]

    bank.nodes = [
        # tor: doradca
        Node("A_start", "Klient sklada wniosek w oddziale", "start", "L_Doradca", 0,
             event_def="message",
             doc="Wniosek papierowy, przyjmowany wylacznie w godzinach pracy oddzialu."),
        Node("A_przyjmij", "Przyjmij wniosek papierowy", "user", "L_Doradca", 1,
             doc="Doradca sprawdza wzrokowo komplet zalacznikow. Brak listy kontrolnej w systemie."),
        Node("A_excel", "Przepisz dane do arkusza Excel", "manual", "L_Doradca", 2,
             doc="Dane przepisywane recznie z formularza papierowego. Zrodlo najczestszych bledow."),
        Node("A_gkomplet", "Komplet dokumentow?", "xor", "L_Doradca", 3),
        Node("A_telefon", "Zadzwon po brakujace dokumenty", "user", "L_Doradca", 4, row=1,
             doc="Brak sladu kontaktu w systemie - ustalenia zostaja w notatniku doradcy."),
        Node("A_mail", "Wyslij wniosek e-mailem do analityka", "user", "L_Doradca", 5,
             doc="Skan wniosku jako zalacznik. Poza e-mailem nie ma informacji, gdzie jest sprawa."),
        Node("A_info_nie", "Poinformuj klienta telefonicznie", "user", "L_Doradca", 10, row=1,
             doc="Uzasadnienie decyzji przekazywane ustnie, bez zapisu."),
        Node("A_umowa", "Przygotuj umowe w edytorze tekstu", "manual", "L_Doradca", 10,
             doc="Szablon .docx z dysku sieciowego, dane wpisywane recznie po raz drugi."),
        Node("A_podpis", "Umow klienta na podpis umowy", "user", "L_Doradca", 11),
        Node("A_end_ok", "Umowa podpisana", "end", "L_Doradca", 12),
        Node("A_end_nie", "Wniosek odrzucony", "end", "L_Doradca", 11, row=1),

        # tor: analityk
        Node("A_bik", "Pobierz raport BIK recznie", "user", "L_Analityk", 6,
             doc="Logowanie do portalu, pobranie PDF, zapis na dysku sieciowym."),
        Node("A_scoring", "Policz scoring w arkuszu", "manual", "L_Analityk", 7,
             doc="Arkusz lokalny, wersjonowany nazwa pliku. Kazdy analityk ma wlasna kopie."),
        Node("A_opinia", "Sporzadz opinie o ryzyku", "user", "L_Analityk", 8),
        Node("A_glimit", "Kwota powyzej limitu analityka?", "xor", "L_Analityk", 9),
        Node("A_dec_analityk", "Zatwierdz decyzje kredytowa", "user", "L_Analityk", 10, row=1),
        Node("A_gdecyzja", "Decyzja pozytywna?", "xor", "L_Analityk", 11),

        # tor: komitet
        Node("A_komitet", "Rozpatrz wniosek na komitecie", "user", "L_Komitet", 10,
             doc="Komitet zbiera sie raz w tygodniu - wniosek czeka do najblizszego posiedzenia."),
    ]

    _flows(bank, [
        ("A_start", "A_przyjmij"),
        ("A_przyjmij", "A_excel"),
        ("A_excel", "A_gkomplet"),
        ("A_gkomplet", "A_telefon", "nie"),
        ("A_telefon", "A_mail"),
        ("A_gkomplet", "A_mail", "tak"),
        ("A_mail", "A_bik"),
        ("A_bik", "A_scoring"),
        ("A_scoring", "A_opinia"),
        ("A_opinia", "A_glimit"),
        ("A_glimit", "A_komitet", "tak"),
        ("A_glimit", "A_dec_analityk", "nie"),
        ("A_komitet", "A_gdecyzja"),
        ("A_dec_analityk", "A_gdecyzja"),
        ("A_gdecyzja", "A_umowa", "tak"),
        ("A_gdecyzja", "A_info_nie", "nie"),
        ("A_info_nie", "A_end_nie"),
        ("A_umowa", "A_podpis"),
        ("A_podpis", "A_end_ok"),
    ])

    d.msg("M_a1", "P_Klient", "A_start", "wniosek papierowy")
    d.msg("M_a2", "A_telefon", "P_Klient", "telefon o brakach")
    d.msg("M_a3", "A_bik", "P_Bik", "reczne zapytanie przez portal")
    d.msg("M_a4", "A_info_nie", "P_Klient", "decyzja odmowna (ustnie)")
    d.msg("M_a5", "A_podpis", "P_Klient", "umowa do podpisu")
    return d


# ---------------------------------------------------------------- TO-BE
def to_be() -> Diagram:
    d = Diagram("ToBe", "Obsluga wniosku kredytowego - stan docelowy (TO-BE)", cols=16)

    klient = d.pool("P_Klient", "Klient")
    bank = d.pool("P_Bank", "Bank - obsluga wniosku kredytowego (TO-BE)", "Proc_ToBe")
    ext = d.pool("P_Rejestry", "Rejestry zewnetrzne (BIK, KRD, CEIDG)")
    core = d.pool("P_Core", "System centralny banku (core banking)")

    bank.lanes = [
        Lane("T_LDoradca", "Doradca kredytowy"),
        Lane("T_LSystem", "Silnik procesowy (BPM)"),
        Lane("T_LAnalityk", "Analityk ryzyka kredytowego"),
        Lane("T_LKomitet", "Komitet kredytowy"),
    ]

    bank.nodes = [
        # tor: doradca
        Node("T_uzupelnij", "Uzupelnij dane wniosku z klientem", "user", "T_LDoradca", 3,
             doc="Zadanie trafia na liste doradcy z SLA 1 dnia roboczego. Kazdy kontakt zapisuje sie w sprawie."),
        Node("T_podpis", "Przekaz umowe do podpisu", "user", "T_LDoradca", 13,
             doc="Umowa generowana przez system; doradca tylko potwierdza tozsamosc i odbiera podpis."),
        Node("T_termin", "Uplynelo 14 dni", "boundary", "T_LDoradca", 13,
             event_def="timer", attached_to="T_podpis",
             doc="Regula: decyzja kredytowa wazna 14 dni. Po tym terminie wniosek wygasa automatycznie."),
        Node("T_end_wygasl", "Wniosek wygasl", "end", "T_LDoradca", 14, row=1),

        # tor: silnik procesowy
        Node("T_start", "Wniosek zlozony w kanale online", "start", "T_LSystem", 0,
             event_def="message",
             doc="Formularz z bankowosci elektronicznej trafia do procesu przez REST."),
        Node("T_waliduj", "Zwaliduj dane wniosku", "service", "T_LSystem", 1,
             doc="Walidacja skladniowa i slownikowa (PESEL, NIP, kwota, okres). REST do uslugi walidacji."),
        Node("T_gkomplet", "Dane kompletne?", "xor", "T_LSystem", 2),
        Node("T_bik", "Pobierz raporty BIK i KRD", "service", "T_LSystem", 4,
             doc="Zapytanie SOAP do BIK (XML wg schemy XSD), rownolegle REST do KRD. Odpowiedz zapisywana w sprawie."),
        Node("T_scoring", "Wylicz scoring i klase ryzyka", "rule", "T_LSystem", 5,
             doc="Zadanie regul biznesowych: model scoringowy zwraca punktacje 0-100 i klase ryzyka A-E."),
        Node("T_gsciezka", "Klasa ryzyka i kwota wniosku?", "xor", "T_LSystem", 6,
             doc="Rozgalezienie sciezki: odmowa automatyczna, decyzja automatyczna albo analiza reczna."),
        Node("T_auto", "Wydaj decyzje automatyczna", "service", "T_LSystem", 7,
             doc="Klasa A-B i kwota do 50 000 zl: decyzja bez udzialu czlowieka."),
        Node("T_odmowa_auto", "Zarejestruj odmowe automatyczna", "service", "T_LSystem", 7, row=1,
             doc="Klasa E lub negatywna weryfikacja rejestrow: odmowa bez analizy recznej."),
        Node("T_zbierz", "Decyzja zebrana", "xor", "T_LSystem", 10),
        Node("T_gdecyzja", "Decyzja pozytywna?", "xor", "T_LSystem", 11),
        Node("T_umowa", "Wygeneruj umowe kredytowa", "service", "T_LSystem", 12,
             doc="SOAP do systemu dokumentowego; dane umowy jako XML zgodny z XSD. Zero przepisywania recznego."),
        Node("T_powiadom", "Wyslij decyzje odmowna z uzasadnieniem", "service", "T_LSystem", 12, row=1,
             doc="REST do kanalu powiadomien. Uzasadnienie z regul scoringowych, nie z rozmowy telefonicznej."),
        Node("T_end_nie", "Wniosek odrzucony", "end", "T_LSystem", 13, row=1),
        Node("T_uruchom", "Przekaz uruchomienie kredytu do core", "service", "T_LSystem", 14,
             doc="SOAP do systemu centralnego; potwierdzenie zwrotne zamyka sprawe."),
        Node("T_end_ok", "Kredyt uruchomiony", "end", "T_LSystem", 15),

        # tor: analityk
        Node("T_analiza", "Przeprowadz analize ryzyka kredytowego", "user", "T_LAnalityk", 7,
             doc="Formularz analizy w systemie, z raportami BIK/KRD i wynikiem scoringu w kontekscie sprawy. SLA 2 dni robocze."),
        Node("T_glimit", "Kwota powyzej limitu decyzyjnego?", "xor", "T_LAnalityk", 8),
        Node("T_dec_analityk", "Podejmij decyzje kredytowa", "user", "T_LAnalityk", 9),

        # tor: komitet
        Node("T_komitet", "Rozpatrz wniosek na komitecie", "user", "T_LKomitet", 9,
             doc="Wniosek trafia na liste komitetu od razu po analizie, bez czekania na posiedzenie."),
    ]

    _flows(bank, [
        ("T_start", "T_waliduj"),
        ("T_waliduj", "T_gkomplet"),
        ("T_gkomplet", "T_uzupelnij", "nie"),
        ("T_uzupelnij", "T_bik"),
        ("T_gkomplet", "T_bik", "tak"),
        ("T_bik", "T_scoring"),
        ("T_scoring", "T_gsciezka"),
        ("T_gsciezka", "T_auto", "klasa A-B, do 50 tys."),
        ("T_gsciezka", "T_odmowa_auto", "klasa E"),
        ("T_gsciezka", "T_analiza", "klasa C-D"),
        ("T_analiza", "T_glimit"),
        ("T_glimit", "T_komitet", "tak"),
        ("T_glimit", "T_dec_analityk", "nie"),
        ("T_dec_analityk", "T_zbierz"),
        ("T_komitet", "T_zbierz"),
        ("T_auto", "T_zbierz"),
        ("T_zbierz", "T_gdecyzja"),
        ("T_gdecyzja", "T_umowa", "tak"),
        ("T_gdecyzja", "T_powiadom", "nie"),
        ("T_odmowa_auto", "T_powiadom"),
        ("T_powiadom", "T_end_nie"),
        ("T_umowa", "T_podpis"),
        ("T_podpis", "T_uruchom"),
        ("T_termin", "T_end_wygasl"),
        ("T_uruchom", "T_end_ok"),
    ])

    d.msg("M_t1", "P_Klient", "T_start", "wniosek z kanalu online (REST)")
    d.msg("M_t2", "T_uzupelnij", "P_Klient", "prosba o uzupelnienie danych")
    d.msg("M_t3", "T_bik", "P_Rejestry", "zapytanie SOAP/XML")
    d.msg("M_t4", "T_powiadom", "P_Klient", "decyzja odmowna z uzasadnieniem")
    d.msg("M_t5", "T_podpis", "P_Klient", "umowa do podpisu")
    d.msg("M_t6", "T_uruchom", "P_Core", "zlecenie uruchomienia (SOAP)")
    return d


def zapisz(d: Diagram, nazwa: str):
    d.layout()
    bledy = sanity(d)
    if bledy:
        print("BLEDY w modelu %s:" % nazwa)
        for b in bledy:
            print("  -", b)
        raise SystemExit(1)
    sciezka = os.path.join(OUT, nazwa)
    with open(sciezka, "w", encoding="utf-8") as fh:
        fh.write(d.xml())
    liczba = sum(len(p.nodes) for p in d.pools)
    print("zapisano %s (%d elementow, %d komunikatow)" % (sciezka, liczba, len(d.messages)))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    zapisz(as_is(), "wniosek-kredytowy-AS-IS.bpmn")
    zapisz(to_be(), "wniosek-kredytowy-TO-BE.bpmn")
