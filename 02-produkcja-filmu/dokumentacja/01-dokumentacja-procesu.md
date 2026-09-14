# Produkcja filmu fabularnego - analiza i modelowanie procesu

**Autor: Mateusz Biernat**
Projekt zaliczeniowy z przedmiotu dotyczącego inżynierii procesów biznesowych,
Polsko-Japońska Akademia Technik Komputerowych.
Przykład procesu: produkcja filmu fabularnego "Szczęki" w Hollywood.

## Co zawiera ten katalog

| Plik | Co to jest |
|---|---|
| `../zrodla-oryginal/` | pliki źródłowe w stanie oryginalnym, bez żadnych zmian (kopia lokalna, poza repozytorium) |
| `../poprawione/produkcja-filmu-TO-BE.bpm` | model Bizagi po korekcie etykiet i metadanych |
| `raport-zmian-etykiet.md` | tabela "było - jest" na każdą zmienioną etykietę (62 pozycje) |
| `obrazy/` | diagramy wyeksportowane z dokumentacji projektu |

## Karta procesu

| Pole | Wartość |
|---|---|
| Nazwa | Produkcja filmu fabularnego |
| Właściciel procesu | Producent wykonawczy |
| Wyzwalacz | Zgłoszenie pomysłu na film (ustnie lub e-mailem) |
| Wynik pozytywny | Premiera filmu i raport końcowy z kosztorysu |
| Wynik negatywny | Odrzucenie scenariusza |
| Uczestnicy | Producent wykonawczy, kontroler finansowy, reżyser, kierownik planu, dział castingu, zespół lokalizacyjny, montażysta, dział promocji, system IT |
| Notacje | BPMN 2.0 (przebieg), UML - diagram przypadków użycia i diagram analityczny (zakres funkcjonalny) |
| Narzędzia | Bizagi Modeler, draw.io, Lucidchart |

## Metoda pracy

1. **Opis stanu obecnego prozą** - na podstawie opisu procesu produkcyjnego,
   z wypunktowaniem miejsc nieefektywnych.
2. **Biznesowy diagram przypadków użycia** - kto z kim i po co
   (`obrazy/2-use-case-biznesowy.png`).
3. **Diagram analityczny** - zależności między obszarami
   (`obrazy/3-diagram-analityczny.png`).
4. **BPMN stanu obecnego (AS-IS)** - przebieg taki, jaki jest
   (`obrazy/4-bpmn-as-is.png`).
5. **BPMN stanu docelowego (TO-BE)** - przebieg po wprowadzeniu wsparcia IT
   (`obrazy/5-bpmn-to-be.png`).
6. **Finalny diagram przypadków użycia** - z rozszerzeniami `<<extend>>`
   opisującymi nowe funkcje systemu (`obrazy/6-use-case-finalny.png`).

Kolejność nie jest przypadkowa: **najpierw ustalam, co się dzieje i kto za to
odpowiada, a dopiero potem, co z tego zautomatyzować.** Odwrotna kolejność kończy
się automatyzacją kroku, który przy okazji zmiany procesu w ogóle znika.

## Stan obecny (AS-IS) - zidentyfikowane problemy

| # | Miejsce w procesie | Problem | Skutek |
|---|---|---|---|
| 1 | Zgłoszenie pomysłu | wpływa ustnie lub e-mailem | brak jednego miejsca, w którym stoi lista pomysłów |
| 2 | Planowanie produkcji | budżet, harmonogram i lista zasobów ustalane ręcznie | pracochłonność, brak spójności między dokumentami |
| 3 | Casting | wyłącznie castingi stacjonarne | wysoki koszt i długi czas obsady |
| 4 | Wybór lokalizacji | ręcznie, po wizytacjach | czas zespołu lokalizacyjnego |
| 5 | Realizacja zdjęć | brak bieżącego monitoringu kosztów | przekroczenia budżetu widoczne dopiero po fakcie |
| 6 | Komunikacja zespołów | e-mail i spotkania | rozproszona informacja, ustalenia giną |
| 7 | Montaż | wersje robocze na nośnikach fizycznych, uwagi spisywane ręcznie | każda iteracja kosztuje obieg materiału |
| 8 | Promocja | plan bez danych analitycznych | kampania oparta na przeczuciu |
| 9 | Rozliczenie | raport końcowy składany ręcznie | błędy w kosztorysie |

## Stan docelowy (TO-BE) - wprowadzone usprawnienia

| Usprawnienie | Element na diagramie | Co zmienia |
|---|---|---|
| Integracja z systemem ERP | `Wprowadź budżet do systemu ERP` | budżet i harmonogram w jednym systemie zamiast w arkuszach |
| Baza nagrań castingowych | `Zapisz nagrania aktorów w bazie danych` + magazyn `Baza nagrań castingowych` | nagrania służą kolejnym projektom i zmianie obsady w trakcie produkcji |
| E-casting | bramka `Czy casting odbywa się zdalnie?` | część castingów bez kosztu spotkania na miejscu |
| Rejestr błędów technicznych | `Zapisz kod błędu technicznego w bazie danych` | powtarzalne awarie planu przestają być rozwiązywane od zera |
| Moduł AI do diagnozy | `Wyznacz rozwiązanie problemu w module AI` | skrócenie przestoju na planie |
| Materiały w chmurze | adnotacja przy torze montażu | koniec obiegu nośników fizycznych |
| Automatyczny zapis iteracji montażu | adnotacja przy torze montażu | pełna historia wersji bez pracy montażysty |
| Integracja narzędzia do uwag | adnotacja przy torze montażu | uwagi producenta przypięte do konkretnej sceny |
| Analiza trendów | `Raport z analizy trendów` | kampania promocyjna planowana na danych |
| Zbieranie danych o kosztach | `Zbierz dane o kosztach` | raport końcowy powstaje z danych, nie z rekonstrukcji |

## Korekta modelu (wrzesień 2026)

Model źródłowy powstał w toku zajęć i miał wady warsztatowe, które w dokumencie
oddawanym na zewnątrz przeszkadzają bardziej niż w projekcie studenckim. Poprawiona
kopia (`../poprawione/produkcja-filmu-TO-BE.bpm`) usuwa je **bez zmiany przebiegu**:

- literówki w etykietach (`wybierz lokalizacjiee zdjeciowe`, `harmongram`)
- brak polskich znaków w części etykiet, przy pełnych diakrytykach w pozostałych
- domyślne nazwy z narzędzia w gotowym modelu (`Process 4`, `Diagram 1`)
- tory nazwane działem zamiast rolą wykonawcy
- zadania nazwane rzeczownikiem odczasownikowym zamiast czasownikiem
- magazyny danych opisane zdaniem zamiast nazwą zbioru

Pełna lista w `raport-zmian-etykiet.md`. Oryginał leży obok poprawionej kopii
(lokalnie, poza repozytorium), więc każdą z tych zmian da się zweryfikować
jeden do jednego.

## Czego ten model nie zawiera

Świadome ograniczenia zakresu, warte powiedzenia wprost:

1. **Brak czasów i kosztów zadań** - model pokazuje przebieg, nie symulację.
   Bizagi umożliwia analizę czasową, ale bez danych z produkcji byłyby to liczby
   wymyślone.
2. **Brak specyfikacji integracji** - systemy zewnętrzne (ERP, chmura, moduł AI)
   występują jako uczestnicy procesu, bez kontraktów technicznych. Przykład takiej
   specyfikacji jest w drugim projekcie w tym repozytorium
   (`01-proces-kredytowy/dokumentacja/04-integracje.md`).
3. **Brak obsługi wyjątków w torze produkcji** - model opisuje przebieg podstawowy
   plus wybrane odchylenia (odrzucenie scenariusza, problem techniczny).

---
Autor: Mateusz Biernat
