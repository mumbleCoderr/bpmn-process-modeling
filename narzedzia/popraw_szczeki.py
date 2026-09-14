# -*- coding: utf-8 -*-
"""Tworzy poprawiona KOPIE modelu Bizagi - oryginal nie jest dotykany.

Plik .bpm to zwykly ZIP, w srodku plik .diag (rowniez ZIP), a w nim Diagram.xml
w formacie XPDL 2.2. Etykiety siedza w atrybutach Name="..." i TextAnnotation="...",
wiec da sie je poprawic bez przerysowywania diagramu.

Skrypt:
  1. czyta oryginal z 02-produkcja-filmu/zrodla-oryginal/
  2. podmienia etykiety wedlug mapy ponizej
  3. wpisuje autora: Mateusz Biernat
  4. zapisuje kopie do 02-produkcja-filmu/poprawione/
  5. generuje raport "bylo -> jest" do dokumentacja/raport-zmian-etykiet.md

Autor: Mateusz Biernat
"""
from __future__ import annotations

import io
import os
import re
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "02-produkcja-filmu", "zrodla-oryginal")
OUT_DIR = os.path.join(ROOT, "02-produkcja-filmu", "poprawione")
DOC_DIR = os.path.join(ROOT, "02-produkcja-filmu", "dokumentacja")

AUTOR = "Mateusz Biernat"

# ---------------------------------------------------------------------------
# Mapa poprawek. Klucz to doslowna wartosc z pliku zrodlowego.
# Powod kazdej grupy stoi w raporcie zmian, nie w nazwie zmiennej.
# ---------------------------------------------------------------------------
MAPA = {
    # --- nazwa modelu i pule ---
    "Diagram 1": "Produkcja filmu fabularnego - stan docelowy (TO-BE)",
    "Proces produkcji": "Wytwórnia filmowa",
    "Produkcja": "Producent wykonawczy",
    "Process 4": "Kierownik planu",
    "Rezyser": "Reżyser",
    "Dzial finansowy": "Dział finansowy",
    "Finanse": "Kontroler finansowy",
    "Dzial castingu": "Dział castingu",
    "Casting": "Reżyser castingu",
    "Zespol lokalizacyjny": "Zespół lokalizacyjny",
    "Montazysta": "Montażysta",
    "Dzial promocji": "Dział promocji",
    "dzial promocji": "Specjalista do spraw promocji",
    "system IT ": "System IT",

    # --- zadania: czasownik w trybie rozkazujacym + obiekt ---
    "Zainicjowanie projektu i wstepne  zalozenia": "Zainicjuj projekt i wstępne założenia",
    "Zatwierdzenie scenariusza": "Zatwierdź scenariusz",
    "Wyslanie do poprawek": "Wyślij scenariusz do poprawek",
    "Odrzuc scenariusz": "Odrzuć scenariusz",
    "Opracowanie budzetu": "Opracuj budżet produkcji",
    "Zrob spotkanie budzetowe": "Przeprowadź spotkanie budżetowe",
    "Stworz raport koncowy": "Sporządź raport końcowy",
    "Wyslij do autora": "Wyślij scenariusz do autora",
    "Wyslij raport do dzialu it": "Wyślij raport do działu IT",
    "Stworz budzet kosztowy": "Sporządź budżet kosztowy",
    "Zbieranie danych o kosztach": "Zbierz dane o kosztach",
    "Planowanie harmongramu zdjec": "Zaplanuj harmonogram zdjęć",
    "Zglos poprawki do montazu": "Zgłoś poprawki do montażu",
    "Realizuj zdjecia": "Realizuj zdjęcia",
    "przekaz zdjecia dalej  ": "Przekaż materiał do montażu",
    "Organizuj casting": "Zorganizuj casting",
    "Zglos problem techniczny": "Zgłoś problem techniczny",
    "Wyslij nagrania aktorow do dzialu it": "Wyślij nagrania aktorów do działu IT",
    "wybierz lokalizacjiee zdjeciowe": "Wybierz lokalizacje zdjęciowe",
    "Montuj wersje robocza filmu": "Zmontuj wersję roboczą filmu",
    "przeslij kopie montazu doIT ": "Prześlij kopię montażu do działu IT",
    "Przygotowanie kampanii promocyjnej": "Przygotuj kampanię promocyjną",
    "zapisz nagrania aktorw do bazy danych ": "Zapisz nagrania aktorów w bazie danych",
    "Wpisz budzet z raportu wsparty przez ERP": "Wprowadź budżet do systemu ERP",
    "zapisz kod bledu technicznego do bazy danych": "Zapisz kod błędu technicznego w bazie danych",
    "sprawdz zapomoca AI solvera sposb rozwiazania problemuo ": "Wyznacz rozwiązanie problemu w module AI",

    # --- bramki: pytanie zamkniete ---
    "Czy scenariusz poprawny?": "Czy scenariusz jest poprawny?",
    "Czy scenariusz poprawiono?": "Czy scenariusz poprawiono?",
    "Czy wystapil problem techniczny?": "Czy wystąpił problem techniczny?",
    "czy jest to e-casting": "Czy casting odbywa się zdalnie?",

    # --- zdarzenia: stan, ktory zaszedl ---
    "gotowy raport": "Raport gotowy",
    "spotkanie odbyte": "Spotkanie budżetowe odbyte",
    "niekompletny scenariusz": "Scenariusz niekompletny",
    "Gdy odbedzie sie spotkanie budzetowe": "Po spotkaniu budżetowym",
    "Zaczyna dzialac w momencie zatwierdzenia scenariusza": "Po zatwierdzeniu scenariusza",
    "Po otrzymaniu harmongramu zdjec ": "Po otrzymaniu harmonogramu zdjęć",
    "Gdy casting sie skonczy": "Po zakończeniu castingu",
    "informacja o problemie": "Informacja o problemie technicznym",
    "po otrzymaniu raportu": "Po otrzymaniu raportu kosztowego",
    "raport z analizy trendow": "Raport z analizy trendów",

    # --- magazyny danych: nazwa zbioru, nie zdanie ---
    "Lokalna baza danych z opracowanymi danymi": "Baza danych kosztów produkcji",
    "Baza danych z zapisanymi demami aktorow": "Baza nagrań castingowych",
    "baza danych z kodami bledu": "Baza kodów błędów technicznych",
    "materialy montazowe": "Repozytorium materiałów montażowych",

    # --- adnotacje ---
    "Pomysł zgłaszany ustnie lub przez e-mail.":
        "Pomysł zgłaszany ustnie lub przez e-mail.",
    "Weryfikacja danych przez dział promocji.":
        "Weryfikacja danych przez dział promocji.",
    "Przeslij materiałów do chmury (Dropbox/Sharepoint).":
        "Prześlij materiały do chmury (Dropbox, SharePoint).",
    "Integracja narzędzia do feedbacku (np. Frame.io)":
        "Integracja narzędzia do zbierania uwag (np. Frame.io).",
    "Automatyczne zapisywanie każdej iteracji (backup, historia wersji).":
        "Automatyczny zapis każdej iteracji montażu (kopia i historia wersji).",
    "Wprowadzenie danych do systemu AI – analiza trendów i planowanie kampanii promocyjnej.":
        "Wprowadzenie danych do systemu AI - analiza trendów i planowanie kampanii.",
    "Nagrania zapisane w bazie danych moga przydac sie w relizacju inych projkeotw "
    "lub gdy cos stalo by sie aktorowi i trzeba byloby dokonac zmiany":
        "Nagrania w bazie służą kolejnym projektom oraz zmianie obsady w trakcie produkcji.",
}

POWODY = {
    "Diagram 1": "nazwa modelu nie mowila, co model przedstawia",
    "Process 4": "domyslna nazwa z narzedzia zostala w gotowym diagramie",
    "Produkcja": "tor opisuje role, a nie dzial - rola wskazuje wykonawce zadania",
    "Finanse": "j.w.",
    "Casting": "j.w.",
    "dzial promocji": "j.w.",
    "system IT ": "spacja na koncu nazwy i niespojna wielkosc liter",
    "Zainicjowanie projektu i wstepne  zalozenia": "podwojna spacja; forma rzeczownikowa zamiast czasownika",
    "wybierz lokalizacjiee zdjeciowe": "literowka w nazwie zadania",
    "sprawdz zapomoca AI solvera sposb rozwiazania problemuo ": "trzy literowki i zlepek slow w jednej etykiecie",
    "zapisz nagrania aktorw do bazy danych ": "literowka i spacja na koncu",
    "przekaz zdjecia dalej  ": "etykieta nie mowila, dokad material trafia",
    "przeslij kopie montazu doIT ": "brak spacji, literowka",
    "Planowanie harmongramu zdjec": "literowka w slowie harmonogram",
    "Po otrzymaniu harmongramu zdjec ": "literowka w slowie harmonogram",
    "czy jest to e-casting": "bramka bez znaku zapytania i wielkiej litery",
    "Lokalna baza danych z opracowanymi danymi": "magazyn danych opisany zdaniem zamiast nazwa zbioru",
    "Wprowadzenie danych do systemu AI – analiza trendów i planowanie kampanii promocyjnej.":
        "myslnik dlugi zamieniony na zwykly",
}


def patch_xml(xml: str):
    """Podmienia etykiety. Zwraca (nowy_xml, lista_zmian, nieznalezione)."""
    zmiany = []
    nieznalezione = []
    for stare, nowe in MAPA.items():
        trafienia = 0
        for atrybut in ("Name", "TextAnnotation"):
            wzor = '%s="%s"' % (atrybut, stare.replace("&", "&amp;"))
            if wzor in xml:
                trafienia += xml.count(wzor)
                xml = xml.replace(wzor, '%s="%s"' % (atrybut, nowe))
        if trafienia:
            if stare != nowe:
                zmiany.append((stare, nowe, trafienia))
        else:
            nieznalezione.append(stare)
    xml = re.sub(r'UserName="[^"]*"', 'UserName="%s"' % AUTOR, xml)
    return xml, zmiany, nieznalezione


def przetworz(nazwa_zrodla: str, nazwa_wyniku: str):
    src = os.path.join(SRC_DIR, nazwa_zrodla)
    dst = os.path.join(OUT_DIR, nazwa_wyniku)
    os.makedirs(OUT_DIR, exist_ok=True)

    zmiany_all, nieznalezione_all = [], []

    with zipfile.ZipFile(src) as zin:
        wpisy = [(i, zin.read(i.filename)) for i in zin.infolist()]

    nowe_wpisy = []
    for info, dane in wpisy:
        if info.filename.endswith(".diag"):
            dane, zmiany_all, nieznalezione_all = patch_diag(dane)
        nowe_wpisy.append((info, dane))

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, dane in nowe_wpisy:
            zout.writestr(info.filename, dane)

    return dst, zmiany_all, nieznalezione_all


def patch_diag(dane: bytes):
    """Plik .diag to zagniezdzony ZIP - patchujemy w nim Diagram.xml."""
    buf = io.BytesIO(dane)
    with zipfile.ZipFile(buf) as zin:
        wpisy = [(i, zin.read(i.filename)) for i in zin.infolist()]

    zmiany, nieznalezione = [], []
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, tresc in wpisy:
            if info.filename.endswith("Diagram.xml"):
                xml = tresc.decode("utf-8")
                xml, zmiany, nieznalezione = patch_xml(xml)
                tresc = xml.encode("utf-8")
            zout.writestr(info.filename, tresc)
    return out.getvalue(), zmiany, nieznalezione


def raport(zmiany, nieznalezione, plik_zrodlowy, plik_wynikowy):
    os.makedirs(DOC_DIR, exist_ok=True)
    sciezka = os.path.join(DOC_DIR, "raport-zmian-etykiet.md")
    L = []
    L.append("# Raport zmian etykiet w modelu BPMN")
    L.append("")
    L.append("Zrodlo: `zrodla-oryginal/%s` (plik **nietkniety**)  " % plik_zrodlowy)
    L.append("Wynik: `poprawione/%s`  " % os.path.basename(plik_wynikowy))
    L.append("Autor modelu wpisany w metadanych: **%s**" % AUTOR)
    L.append("")
    L.append("Zmieniono wylacznie **etykiety i metadane**. Uklad diagramu, elementy,")
    L.append("przeplywy i pule zostaly bez zmian - kazda pozycja ponizej da sie")
    L.append("zestawic z oryginalem jeden do jednego.")
    L.append("")
    L.append("## Zmienione etykiety (%d)" % len(zmiany))
    L.append("")
    L.append("| # | Bylo | Jest | Wystapien | Powod |")
    L.append("|---|---|---|---|---|")
    for i, (stare, nowe, ile) in enumerate(sorted(zmiany), start=1):
        powod = POWODY.get(stare, "literowka lub niespojna forma etykiety")
        L.append("| %d | `%s` | `%s` | %d | %s |" % (i, stare, nowe, ile, powod))
    L.append("")
    if nieznalezione:
        L.append("## Pozycje z mapy, ktorych nie bylo w pliku (%d)" % len(nieznalezione))
        L.append("")
        for s in nieznalezione:
            L.append("- `%s`" % s)
        L.append("")
    L.append("## Zasady, ktore stoja za tymi zmianami")
    L.append("")
    L.append("1. **Zadanie to czasownik w trybie rozkazujacym plus obiekt** "
             "(`Zatwierdz scenariusz`), a nie rzeczownik odczasownikowy "
             "(`Zatwierdzenie scenariusza`). Diagram ma mowic, co ktos ma zrobic.")
    L.append("2. **Bramka to pytanie zamkniete** zakonczone znakiem zapytania, "
             "a kazde wyjscie z niej ma etykiete odpowiedzi.")
    L.append("3. **Zdarzenie to stan, ktory zaszedl** (`Spotkanie budzetowe odbyte`), "
             "a nie zdanie warunkowe (`Gdy odbedzie sie spotkanie budzetowe`).")
    L.append("4. **Tor nosi nazwe roli**, bo tor wskazuje wykonawce zadania. "
             "Nazwa dzialu w puli, rola w torze.")
    L.append("5. **Magazyn danych nosi nazwe zbioru**, nie opis w zdaniu.")
    L.append("6. Zadnej domyslnej nazwy z narzedzia (`Process 4`, `Diagram 1`) "
             "w gotowym modelu.")
    L.append("")
    L.append("---")
    L.append("Autor: %s" % AUTOR)
    with open(sciezka, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return sciezka


if __name__ == "__main__":
    zrodlo = "szczeki BPMNostaeczna.bpm"
    wynik = "produkcja-filmu-TO-BE.bpm"
    dst, zmiany, nieznalezione = przetworz(zrodlo, wynik)
    sciezka_raportu = raport(zmiany, nieznalezione, zrodlo, dst)
    print("zapisano kopie: %s" % dst)
    print("zmienionych etykiet: %d" % len(zmiany))
    if nieznalezione:
        print("nie znaleziono w pliku (%d): %s" % (len(nieznalezione), ", ".join(nieznalezione)))
    print("raport: %s" % sciezka_raportu)
