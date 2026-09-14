# Mierniki procesu i spodziewane efekty zmiany

Liczby w tym dokumencie są **wielkościami modelowymi**, przyjętymi do policzenia
efektu zmiany - nie pochodzą z pomiaru na produkcji. Tam, gdzie dana wielkość jest
założeniem, jest to napisane wprost. Miernik bez źródła jest życzeniem, nie miernikiem.

## Mierniki

| # | Miernik | Definicja | Źródło danych | Cel |
|---|---|---|---|---|
| M1 | Czas do decyzji | od `zlozono` do `decyzja.wydano` | tabela `wniosek`, `decyzja` | mediana < 1 dzień roboczy |
| M2 | Udział decyzji automatycznych | decyzje typu `AUTOMATYCZNA` / wszystkie | tabela `decyzja` | >= 35% |
| M3 | Dotrzymanie SLA zadań | zadania zamknięte przed `termin_sla` / wszystkie | tabela `zadanie` | >= 90% |
| M4 | Udział wniosków z brakami | sprawy, które przeszły przez `T_uzupelnij` | historia sprawy | < 15% |
| M5 | Wnioski wygasłe po decyzji pozytywnej | status `WYGASL` / decyzje pozytywne | `wniosek`, `decyzja` | < 5% |
| M6 | Nieudane wywołania integracji | wywołania zakończone błędem / wszystkie | logi integracji | < 1% |
| M7 | Kompletność śladu decyzji | decyzje z zapisanym uzasadnieniem i wersją modelu | `decyzja`, `scoring` | 100% |

M7 ma cel 100% i to nie jest ambicja, tylko wymóg: decyzja kredytowa bez zapisanego
uzasadnienia jest problemem regulacyjnym niezależnie od tego, czy była trafna.

## Porównanie AS-IS i TO-BE

| Etap | AS-IS (założenie modelowe) | TO-BE (oczekiwane) | Skąd różnica |
|---|---|---|---|
| Rejestracja wniosku | 25 min pracy doradcy | 0 min (formularz klienta) | dane wpisuje klient, raz |
| Kompletowanie dokumentów | 1-3 dni, kontakt telefoniczny | do 1 dnia, zadanie z SLA | brak zależy od pamięci doradcy |
| Pobranie raportów | 15 min pracy analityka | 30 sekund, bez człowieka | zadanie usługowe |
| Scoring | 20 min w arkuszu | 5 sekund, jedna wersja modelu | zadanie reguł biznesowych |
| Decyzja - wnioski proste | ta sama ścieżka co trudne | automatyczna | bramka klasy ryzyka |
| Decyzja - komitet | do 7 dni (czeka na posiedzenie) | do 3 dni | wniosek trafia na listę od razu |
| Umowa | 30 min, ręczne przepisanie | 20 sekund, generowana z danych sprawy | jedno źródło danych |
| Ślad decyzji | e-mail plus notatki | historia sprawy | proces prowadzony przez silnik |

## Gdzie zmiana **nie** daje oszczędności

Trzy rzeczy, których automatyzacja nie skraca, i lepiej powiedzieć to od razu niż
tłumaczyć się po wdrożeniu:

1. **Analiza wniosków klasy C-D.** Czas analityka zostaje ten sam - zmienia się to,
   że dostaje komplet danych w jednym miejscu, a nie że ocenia szybciej.
2. **Decyzja komitetu.** Skrócenie oczekiwania bierze się z kolejkowania, nie
   z samego posiedzenia. Posiedzenie trwa tyle, ile trwało.
3. **Podpisanie umowy przez klienta.** Zależy od klienta, nie od procesu. Dlatego
   stoi tu timer 14 dni, a nie obietnica skrócenia.

## Ryzyka wdrożenia

| Ryzyko | Skutek | Reakcja |
|---|---|---|
| Model scoringowy przepuszcza złe wnioski w trybie automatycznym | strata kredytowa | start z wąskim progiem (klasa A-B, do 50 tys. zł), przegląd po 3 miesiącach |
| Niedostępność BIK | proces staje na etapie raportów | eskalacja do analityka po 2 ponowieniach, ręczne pobranie jako droga awaryjna |
| Opór doradców przed nowym narzędziem | powrót do pracy poza systemem | lista zadań zastępuje skrzynkę e-mail, nie dokłada się do niej |
| Zmiana progów bez śladu | brak odtwarzalności decyzji | wersjonowanie parametrów, `wersja_modelu` przy każdej decyzji |

---
Autor: Mateusz Biernat
