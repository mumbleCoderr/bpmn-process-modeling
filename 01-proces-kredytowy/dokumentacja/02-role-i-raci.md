# Role i macierz odpowiedzialności (RACI)

R - wykonuje, A - odpowiada za wynik, C - konsultowany, I - informowany.

## Role w procesie

| Rola | Opis | Uprawnienia w systemie |
|---|---|---|
| Klient | Składa wniosek, uzupełnia dane, podpisuje umowę | dostęp wyłącznie do własnej sprawy przez kanał online |
| Doradca kredytowy | Kontakt z klientem, uzupełnianie danych, odbiór podpisu | podgląd sprawy, edycja danych wniosku do momentu scoringu |
| Analityk ryzyka kredytowego | Analiza wniosków klasy C-D, decyzja do limitu | decyzja do 100 000 zł, podgląd raportów BIK/KRD |
| Komitet kredytowy | Decyzja powyżej limitu analityka | decyzja bez limitu kwotowego |
| Silnik procesowy (BPM) | Walidacja, integracje, scoring, decyzje automatyczne, generowanie umowy | konto techniczne, brak dostępu interaktywnego |
| Administrator procesu | Wersje modelu, reguły, SLA, uprawnienia | wdrożenie nowej wersji procesu |
| Audyt / Compliance | Kontrola śladu decyzji | odczyt historii spraw, bez prawa edycji |

## Macierz RACI (TO-BE)

| Zadanie | Klient | Doradca | Analityk | Komitet | Silnik BPM | Audyt |
|---|---|---|---|---|---|---|
| Złożenie wniosku | R | I | - | - | A | - |
| Walidacja danych wniosku | I | I | - | - | R/A | - |
| Uzupełnienie brakujących danych | C | R/A | - | - | I | - |
| Pobranie raportów BIK i KRD | I | - | C | - | R/A | I |
| Wyliczenie scoringu i klasy ryzyka | - | - | C | - | R/A | I |
| Decyzja automatyczna (klasa A-B do 50 tys. zł) | I | I | I | - | R/A | I |
| Odmowa automatyczna (klasa E) | I | I | I | - | R/A | I |
| Analiza ryzyka kredytowego (klasa C-D) | - | C | R/A | I | I | I |
| Decyzja kredytowa do limitu | I | I | R/A | I | I | I |
| Decyzja kredytowa powyżej limitu | I | I | C | R/A | I | I |
| Wygenerowanie umowy | I | I | - | - | R/A | - |
| Podpisanie umowy | R | R/A | - | - | I | - |
| Uruchomienie kredytu w core banking | I | I | - | - | R/A | I |

Zasada: **jedno A na wiersz**. Tam, gdzie odpowiada silnik procesowy, odpowiedzialność
organizacyjna leży po stronie właściciela procesu - konto techniczne nie odpowiada
przed audytem, odpowiada człowiek, który zatwierdził wersję reguł.

## Limity decyzyjne

| Szczebel | Limit kwotowy | Warunek dodatkowy |
|---|---|---|
| Decyzja automatyczna | do 50 000 zł | klasa ryzyka A lub B, brak negatywnych wpisów w BIK/KRD |
| Analityk ryzyka | do 100 000 zł | klasa ryzyka C lub D |
| Komitet kredytowy | bez limitu | każdy wniosek powyżej 100 000 zł |

Limit jest **parametrem procesu, nie stałą w kodzie** - podniesienie progu decyzji
automatycznej z 50 000 na 80 000 zł nie może wymagać nowej wersji modelu BPMN.

---
Autor: Mateusz Biernat
