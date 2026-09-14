# Karta procesu: obsługa wniosku kredytowego

| Pole | Wartość |
|---|---|
| Identyfikator | `KRD-001` |
| Nazwa | Obsługa wniosku o kredyt gotówkowy dla klienta indywidualnego |
| Właściciel procesu | Dyrektor Departamentu Ryzyka Kredytowego |
| Właściciel systemu | Zespół platformy workflow (BPM) |
| Wyzwalacz | Klient składa wniosek kredytowy (oddział - AS-IS, kanał online - TO-BE) |
| Wynik pozytywny | Umowa podpisana, kredyt uruchomiony w systemie centralnym |
| Wynik negatywny | Wniosek odrzucony z uzasadnieniem albo wygasły po 14 dniach |
| Klienci procesu | Klient indywidualny, Departament Ryzyka, Sprzedaż, Audyt |
| Częstotliwość | Ok. 1 200 wniosków miesięcznie (założenie modelowe) |
| Systemy | Silnik BPM, BIK, KRD, system dokumentowy, core banking, kanał powiadomień |
| Regulacje | Rekomendacja T i S KNF, RODO, ustawa o kredycie konsumenckim |

## Zakres

Proces obejmuje drogę od złożenia wniosku do uruchomienia kredytu albo odrzucenia
wniosku. **Poza zakresem** są: obsługa posprzedażowa, windykacja, monitoring
portfela i zmiany warunków umowy.

## Granice procesu

- **Wejście**: komplet danych wniosku (dane osobowe, kwota, okres, cel, dochód)
- **Wyjście pozytywne**: zlecenie uruchomienia w systemie centralnym plus podpisana umowa
- **Wyjście negatywne**: decyzja odmowna z uzasadnieniem przekazana klientowi

## Dwa modele w tym katalogu

| Model | Plik | Czym jest |
|---|---|---|
| AS-IS | `diagramy/wniosek-kredytowy-AS-IS.bpmn` | Stan obecny: papier, Excel, poczta e-mail, decyzje poza systemem |
| TO-BE | `diagramy/wniosek-kredytowy-TO-BE.bpmn` | Stan docelowy: proces prowadzony przez silnik BPM, integracje, decyzja automatyczna dla części wniosków |

Oba diagramy powstają z jednej specyfikacji (`narzedzia/build_kredyt.py`), więc
zmiana w modelu nie wymaga przesuwania figur na rysunku.

## Problemy stanu obecnego (AS-IS)

| # | Problem | Skutek | Gdzie widać na diagramie |
|---|---|---|---|
| 1 | Dane przepisywane ręcznie z papieru do arkusza | Błędy danych, podwójna praca (drugi raz przy umowie) | `Przepisz dane do arkusza Excel` |
| 2 | Wniosek wędruje e-mailem | Brak informacji, na jakim etapie jest sprawa; brak SLA | `Wyślij wniosek e-mailem do analityka` |
| 3 | Raport BIK pobierany ręcznie przez portal | Czas analityka zużyty na czynność mechaniczną | `Pobierz raport BIK ręcznie` |
| 4 | Scoring liczony w lokalnym arkuszu | Brak jednej wersji modelu, wynik nieodtwarzalny przy audycie | `Policz scoring w arkuszu` |
| 5 | Każdy wniosek idzie przez człowieka | Wnioski o niskim ryzyku i małej kwocie zajmują ten sam czas co trudne | cały tor analityka |
| 6 | Komitet obraduje raz w tygodniu | Wniosek czeka do posiedzenia niezależnie od gotowości | `Rozpatrz wniosek na komitecie` |
| 7 | Odmowa przekazywana ustnie | Brak śladu uzasadnienia, ryzyko regulacyjne i reklamacyjne | `Poinformuj klienta telefonicznie` |
| 8 | Umowa składana ręcznie w edytorze tekstu | Ryzyko rozbieżności z decyzją, trzecie przepisanie danych | `Przygotuj umowę w edytorze tekstu` |

## Odpowiedzi w stanie docelowym (TO-BE)

| Problem | Rozwiązanie w TO-BE |
|---|---|
| 1, 8 | Dane wpisywane raz, w formularzu wniosku; umowa generowana z danych sprawy |
| 2 | Sprawa prowadzona przez silnik procesowy: status, historia i SLA w jednym miejscu |
| 3 | Zadanie usługowe `Pobierz raporty BIK i KRD` (SOAP/REST) |
| 4 | Zadanie reguł biznesowych `Wylicz scoring i klasę ryzyka` - jeden model, wersjonowany |
| 5 | Bramka `Klasa ryzyka i kwota wniosku?` kieruje część spraw na decyzję automatyczną |
| 6 | Wniosek trafia na listę komitetu od razu po analizie |
| 7 | Zadanie usługowe wysyła decyzję z uzasadnieniem zbudowanym z reguł scoringowych |

Świadomie **nie usunięto** analizy ręcznej: wnioski klasy C-D nadal ocenia analityk.
Automatyzacja obejmuje wyłącznie skrajne klasy ryzyka, gdzie reguła jest jednoznaczna.

---
Autor: Mateusz Biernat
