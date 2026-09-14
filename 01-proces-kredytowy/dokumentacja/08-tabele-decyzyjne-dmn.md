# Model scoringowy jako tabele decyzyjne (DMN 1.3)

Scoring nie jest kodem w workerze ani logiką wpisaną w proces. Jest osobnym
modelem decyzyjnym w DMN, który silnik wywołuje z zadania reguł biznesowych.

![Tabela decyzyjna w Operate](../diagramy/uruchomienie/operate-decyzja-dmn.png)

Zrzut z Camunda Operate: realnie oceniona sprawa. Podświetlone wiersze to reguły,
które zadziałały (1, 4, 7, 9, 11), po prawej ich wkład punktowy: 35 + 25 + 20 + 15 + 5 = 100.

## Dlaczego osobno od procesu

Progi ryzyka zmieniają się kilka razy w roku, przebieg procesu - raz na kilka lat.
Gdyby punktacja siedziała w procesie, **podniesienie wagi za staż pracy wymagałoby
wdrożenia nowej wersji całego procesu**, a wszystkie sprawy w toku dalej chodziłyby
po starej wersji modelu. Osobna decyzja pozwala wersjonować jedno bez drugiego:

| Zmiana | Co się wdraża |
|---|---|
| inna waga czynnika, inna granica klasy | nowa wersja decyzji DMN |
| nowy krok w procesie, inna ścieżka, inne SLA | nowa wersja procesu BPMN |

To ta sama zasada, którą [katalog reguł](03-katalog-zadan-i-regul.md) zapowiadał
przy uwadze o wersjonowaniu modelu scoringowego. Tutaj jest zrealizowana.

## Struktura modelu decyzyjnego

Trzy decyzje w jednym pliku `diagramy/scoring-kredytowy.dmn`, powiązane wymaganiami
informacyjnymi (DRD):

```
  ocena-ryzyka           klasa A-E + ścieżka decyzji     (tabela, hit policy FIRST)
        ^
        |
  punktacja-kredytowa    0-100 punktów                   (tabela, COLLECT SUM)
        ^
        |
  wskaznik-dti           rata do dochodu w procentach    (wyrażenie literalne FEEL)
```

| Decyzja | Wejście | Wyjście | Rodzaj |
|---|---|---|---|
| `wskaznik-dti` | kwota, okres, dochód, raty z BIK | `dti` (liczba) | wyrażenie FEEL |
| `punktacja-kredytowa` | scoring BIK, DTI, staż, wpisy negatywne | `punktacja` (0-100) | tabela decyzyjna |
| `ocena-ryzyka` | punktacja, DTI | kontekst: klasa, punktacja, DTI, ścieżka | tabela decyzyjna |

## Dwie decyzje projektowe w samych tabelach

**1. Punktacja ma politykę trafień COLLECT z agregacją SUM, nie UNIQUE.**
Czynniki ryzyka **dodają się**, a nie wykluczają: dobra historia w BIK i niski DTI
to dwie osobne zalety wniosku. Przy polityce UNIQUE trzeba by wypisać wszystkie
kombinacje czynników - przy czterech wejściach to kilkadziesiąt wierszy zamiast
jedenastu, i każda zmiana wagi wymagałaby przepisania całej tabeli.

**2. Ocena klasy ma politykę FIRST, mimo że przedziały są rozłączne.**
Rozłączność to założenie, a nie gwarancja - literówka w granicy przedziału
(`[70..85)` kontra `[70..85]`) sprawia, że 85 punktów pasuje do dwóch reguł.
Przy FIRST wniosek dostaje wtedy lepszą klasę i sprawa idzie dalej; przy UNIQUE
silnik zgłasza incydent i sprawa staje. Tutaj wybieram zachowanie przewidywalne.

**DTI zaokrąglany w górę** (`round up`), nie do najbliższej wartości. Przy progach
30% i 45% druga cyfra po przecinku decyduje o 10 punktach, a zaokrąglenie w dół
zaniżałoby obciążenie klienta. Błąd na niekorzyść wniosku jest tańszy niż błąd
na niekorzyść banku.

## Połączenie z procesem

Zadanie `Wylicz scoring i klasę ryzyka` (Business Rule Task) woła decyzję
i rozpakowuje wynik na zmienne sprawy:

```xml
<bpmn:businessRuleTask id="T_scoring" name="Wylicz scoring i klase ryzyka">
  <bpmn:extensionElements>
    <zeebe:calledDecision decisionId="ocena-ryzyka" resultVariable="ocenaRyzyka" />
    <zeebe:ioMapping>
      <zeebe:output source="=ocenaRyzyka.klasa"     target="klasaRyzyka" />
      <zeebe:output source="=ocenaRyzyka.punktacja" target="punktacja" />
      <zeebe:output source="=ocenaRyzyka.dti"       target="dti" />
      <zeebe:output source="=ocenaRyzyka.sciezka"   target="sciezkaDecyzji" />
    </zeebe:ioMapping>
  </bpmn:extensionElements>
</bpmn:businessRuleTask>
```

Mapowanie wyjścia nie jest ozdobą: decyzja zwraca **jeden kontekst**, a warunki
na bramkach w modelu biznesowym mówią o `klasaRyzyka` i `kwota`. Rozpakowanie
kontekstu na zmienne sprawy pozwala zostawić te warunki dokładnie takie, jakie
uzgodniono z biznesem - bez przepisywania ich na `ocenaRyzyka.klasa`.

Proces i decyzje idą w **jednym wdrożeniu** (`camunda_kredyt.py deploy`). Przy
osobnych wdrożeniach nowa wersja procesu potrafi przez chwilę wołać starą wersję
decyzji, a to najgorszy rodzaj błędu: nic się nie psuje, tylko wyniki są inne.

## Sprawdzenie zgodności

Przed przeniesieniem scoringu do DMN liczył go worker. Po przeniesieniu te same
sprawy dają te same wyniki:

| Sprawa | Worker (przed) | DMN (po) |
|---|---|---|
| 45 000 zł, dochód 7 800 zł | 100 pkt, klasa A, DTI 22,92 | 100 pkt, klasa A, DTI 22,91 |
| 200 000 zł, dochód 3 200 zł | 53 pkt, klasa D, DTI 211,42 | 53 pkt, klasa D, DTI 211,42 |

Różnica 0,01 punktu procentowego w pierwszej sprawie to **świadoma zmiana**, nie
błąd: worker zaokrąglał do najbliższej wartości, DMN zaokrągla w górę. Klasa
ryzyka i punktacja są identyczne, więc zmiana nie rusza decyzji kredytowej.

## Czego ta wersja nie obejmuje

1. **Tabela nie zna produktu.** Progi są wspólne dla wszystkich kredytów
   gotówkowych. Model dla kilku produktów potrzebuje wejścia `typProduktu`
   albo osobnych decyzji per produkt.
2. **Brak reguł odcinających poza punktacją.** Polityka kredytowa zwykle ma
   twarde wykluczenia (wiek, brak zdolności prawnej, kraj rezydencji), które
   działają niezależnie od punktów. To osobna decyzja przed scoringiem.
3. **Brak testów tabeli.** Camunda pozwala oceniać decyzję samodzielnie
   (`POST /v2/decision-definitions/{key}/evaluation`), więc zestaw przypadków
   brzegowych - 84, 85, 69, 70 punktów - daje się uruchomić bez procesu.

---
Autor: Mateusz Biernat
