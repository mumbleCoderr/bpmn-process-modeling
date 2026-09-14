# Katalog zadań i reguł biznesowych (TO-BE)

Identyfikatory zgadzają się z `id` elementów w pliku `wniosek-kredytowy-TO-BE.bpmn`,
więc dokument i model da się zestawić bez zgadywania.

## Zadania

| ID | Nazwa | Typ BPMN | Wykonawca | Wejście | Wyjście | SLA |
|---|---|---|---|---|---|---|
| `T_waliduj` | Zwaliduj dane wniosku | Service Task | Silnik BPM | formularz wniosku (JSON) | status walidacji, lista braków | 5 s |
| `T_uzupelnij` | Uzupełnij dane wniosku z klientem | User Task | Doradca | lista braków | komplet danych | 1 dzień roboczy |
| `T_bik` | Pobierz raporty BIK i KRD | Service Task | Silnik BPM | PESEL, zgoda klienta | raport BIK (XML), raport KRD (JSON) | 30 s |
| `T_scoring` | Wylicz scoring i klasę ryzyka | Business Rule Task | Silnik BPM | dane wniosku, raporty | punktacja 0-100, klasa A-E | 5 s |
| `T_auto` | Wydaj decyzję automatyczną | Service Task | Silnik BPM | klasa ryzyka, kwota | decyzja pozytywna | 5 s |
| `T_odmowa_auto` | Zarejestruj odmowę automatyczną | Service Task | Silnik BPM | klasa ryzyka E | decyzja odmowna | 5 s |
| `T_analiza` | Przeprowadź analizę ryzyka kredytowego | User Task | Analityk | komplet danych i raportów | opinia o ryzyku | 2 dni robocze |
| `T_dec_analityk` | Podejmij decyzję kredytową | User Task | Analityk | opinia o ryzyku | decyzja | 1 dzień roboczy |
| `T_komitet` | Rozpatrz wniosek na komitecie | User Task | Komitet | opinia o ryzyku | decyzja | 3 dni robocze |
| `T_umowa` | Wygeneruj umowę kredytową | Service Task | Silnik BPM | decyzja pozytywna, dane sprawy | umowa PDF + XML | 20 s |
| `T_powiadom` | Wyślij decyzję odmowną z uzasadnieniem | Service Task | Silnik BPM | decyzja odmowna, powody z reguł | powiadomienie do klienta | 1 min |
| `T_podpis` | Przekaż umowę do podpisu | User Task | Doradca | umowa | umowa podpisana | 14 dni (termin ważności decyzji) |
| `T_uruchom` | Przekaż uruchomienie kredytu do core | Service Task | Silnik BPM | umowa podpisana | potwierdzenie uruchomienia | 1 min |

## Bramki i reguły

### `T_gkomplet` - Dane kompletne?

| Warunek | Ścieżka |
|---|---|
| wszystkie pola wymagane wypełnione **i** walidacja słownikowa przeszła | `tak` - dalej do pobrania raportów |
| brak choćby jednego pola wymaganego albo błąd formatu | `nie` - zadanie dla doradcy |

Pola wymagane: PESEL, imię i nazwisko, adres, dochód miesięczny netto, źródło
dochodu, kwota wniosku, okres kredytowania, cel kredytu, zgody RODO i BIK.

### `T_gsciezka` - Klasa ryzyka i kwota wniosku?

| Warunek | Ścieżka | Uzasadnienie |
|---|---|---|
| klasa A lub B **i** kwota <= 50 000 zł **i** brak wpisów negatywnych | decyzja automatyczna | reguła jednoznaczna, udział człowieka nic nie wnosi |
| klasa E | odmowa automatyczna | próg odcięcia z polityki kredytowej |
| klasa C lub D **albo** kwota > 50 000 zł | analiza ręczna | ocena wymaga osądu, nie tylko punktacji |

**Bramka jest wyłączna (XOR) i warunki muszą się wykluczać.** Kolejność sprawdzania:
najpierw klasa E, potem próg automatyczny, na końcu ścieżka domyślna (analiza).
Bez ustalonej kolejności wniosek klasy E na kwotę 20 000 zł spełniałby dwa warunki naraz.

### `T_glimit` - Kwota powyżej limitu decyzyjnego?

| Warunek | Ścieżka |
|---|---|
| kwota > 100 000 zł | komitet kredytowy |
| kwota <= 100 000 zł | decyzja analityka |

### `T_gdecyzja` - Decyzja pozytywna?

| Warunek | Ścieżka |
|---|---|
| decyzja = POZYTYWNA | generowanie umowy |
| decyzja = NEGATYWNA | powiadomienie z uzasadnieniem |

### `T_termin` - zdarzenie brzegowe (timer, 14 dni)

Decyzja kredytowa traci ważność po 14 dniach od wydania. Po upływie terminu sprawa
kończy się stanem `Wniosek wygasł`, a klient musi złożyć nowy wniosek - dane
o dochodach i wpisy w rejestrach po dwóch tygodniach nie są już świeże.

Zdarzenie jest **przerywające** (`cancelActivity="true"`): zadanie podpisu znika
z listy doradcy. Wersja nieprzerywająca zostawiłaby zadanie, którego wykonanie
nie miałoby już skutku.

## Reguły scoringowe (wejście do `T_scoring`)

| Czynnik | Waga | Źródło |
|---|---|---|
| Historia spłat w BIK | 35 | raport BIK |
| Wskaźnik DTI (rata do dochodu) | 25 | dane wniosku + zobowiązania z BIK |
| Staż i źródło dochodu | 20 | dane wniosku |
| Wpisy w KRD | 15 | raport KRD |
| Relacja z bankiem (staż rachunku) | 5 | core banking |

| Punktacja | Klasa | Domyślne działanie |
|---|---|---|
| 85-100 | A | decyzja automatyczna (do progu kwotowego) |
| 70-84 | B | decyzja automatyczna (do progu kwotowego) |
| 55-69 | C | analiza ręczna |
| 40-54 | D | analiza ręczna, wymagane zabezpieczenie |
| 0-39 | E | odmowa automatyczna |

Model scoringowy jest **wersjonowany osobno od procesu**: zmiana wag nie jest zmianą
przebiegu procesu i nie może wymuszać wdrożenia nowej wersji diagramu BPMN.
Każda decyzja zapisuje identyfikator wersji modelu, inaczej po roku nie da się
odtworzyć, na jakiej podstawie zapadła.

---
Autor: Mateusz Biernat
