# Specyfikacja integracji (TO-BE)

Każde zadanie usługowe z diagramu ma tu swój kontrakt. Dokument odpowiada na pytanie
"co dokładnie leci przez sieć w tym kroku", a nie "z czym się integrujemy".

## Mapa integracji

| Zadanie BPMN | System | Protokół | Operacja | Tryb | Timeout | Zachowanie przy błędzie |
|---|---|---|---|---|---|---|
| `T_start` | Kanał online | REST | `POST /api/v1/wnioski` | synchroniczny | 10 s | odpowiedź 4xx do kanału, sprawa nie powstaje |
| `T_waliduj` | Usługa walidacji | REST | `POST /api/v1/walidacja` | synchroniczny | 5 s | 3 ponowienia co 2 s, potem zadanie dla doradcy |
| `T_bik` | BIK | SOAP 1.1 | `PobierzRaportKredytowy` | synchroniczny | 30 s | 2 ponowienia, potem eskalacja do analityka |
| `T_bik` | KRD | REST | `GET /v2/podmioty/{pesel}/wpisy` | synchroniczny | 15 s | brak raportu KRD nie blokuje procesu, obniża punktację |
| `T_umowa` | System dokumentowy | SOAP 1.1 | `GenerujDokument` | synchroniczny | 20 s | 3 ponowienia, potem zadanie dla administratora |
| `T_powiadom` | Kanał powiadomień | REST | `POST /api/v1/powiadomienia` | asynchroniczny | 5 s | kolejka ponowień, proces idzie dalej |
| `T_uruchom` | Core banking | SOAP 1.1 | `UruchomKredyt` | synchroniczny | 60 s | bez potwierdzenia sprawa nie zamyka się; zadanie dla operatora |

Zasada doboru protokołu nie jest estetyczna: **systemy centralne banku i BIK wystawiają
SOAP** (kontrakt WSDL, XSD, podpis XML), a kanały cyfrowe i usługi wewnętrzne - REST.
Adapter tłumaczy jedno na drugie, żeby model procesu nie zależał od tego, który
system akurat mówi którym protokołem.

## 1. Złożenie wniosku - REST

`POST /api/v1/wnioski`

```json
{
  "kanal": "BANKOWOSC_ELEKTRONICZNA",
  "klient": {
    "pesel": "90010112345",
    "imie": "Anna",
    "nazwisko": "Nowak",
    "email": "anna.nowak@example.com",
    "telefon": "+48500100200"
  },
  "wniosek": {
    "kwota": 45000.00,
    "waluta": "PLN",
    "okresMiesiecy": 48,
    "cel": "KONSOLIDACJA",
    "dochodNettoMiesieczny": 7800.00,
    "zrodloDochodu": "UMOWA_O_PRACE",
    "stazMiesiecy": 26
  },
  "zgody": {
    "bik": true,
    "rodoMarketing": false
  }
}
```

Odpowiedź `201 Created`:

```json
{
  "idSprawy": "KRD-2026-000184",
  "status": "W_WALIDACJI",
  "utworzono": "2026-09-14T10:21:05+02:00"
}
```

`idSprawy` jest jedynym identyfikatorem używanym w dalszej komunikacji - klient
i doradca podają go przy każdym kontakcie, a audyt po nim odtwarza całą historię.

## 2. Raport kredytowy z BIK - SOAP

Żądanie:

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:bik="http://bik.pl/uslugi/raport/v2">
  <soapenv:Header>
    <bik:Uwierzytelnienie>
      <bik:IdInstytucji>PL-BANK-0042</bik:IdInstytucji>
      <bik:Token>eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...</bik:Token>
    </bik:Uwierzytelnienie>
  </soapenv:Header>
  <soapenv:Body>
    <bik:PobierzRaportKredytowyRequest>
      <bik:IdKorelacji>KRD-2026-000184</bik:IdKorelacji>
      <bik:Pesel>90010112345</bik:Pesel>
      <bik:ZakresRaportu>PELNY</bik:ZakresRaportu>
      <bik:PodstawaPrawna>ZGODA_KLIENTA</bik:PodstawaPrawna>
      <bik:DataZgody>2026-09-14</bik:DataZgody>
    </bik:PobierzRaportKredytowyRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

Odpowiedź (fragment):

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:bik="http://bik.pl/uslugi/raport/v2">
  <soapenv:Body>
    <bik:PobierzRaportKredytowyResponse>
      <bik:IdKorelacji>KRD-2026-000184</bik:IdKorelacji>
      <bik:Scoring>742</bik:Scoring>
      <bik:LiczbaCzynnychZobowiazan>2</bik:LiczbaCzynnychZobowiazan>
      <bik:SumaRatMiesiecznych>1180.00</bik:SumaRatMiesiecznych>
      <bik:Opoznienia>
        <bik:Opoznienie>
          <bik:Dni>17</bik:Dni>
          <bik:Rok>2024</bik:Rok>
          <bik:Status>SPLACONE</bik:Status>
        </bik:Opoznienie>
      </bik:Opoznienia>
      <bik:WpisyNegatywne>0</bik:WpisyNegatywne>
    </bik:PobierzRaportKredytowyResponse>
  </soapenv:Body>
</soapenv:Envelope>
```

Fragment schemy (XSD), na której stoi walidacja odpowiedzi:

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://bik.pl/uslugi/raport/v2"
           elementFormDefault="qualified">
  <xs:element name="PobierzRaportKredytowyResponse">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="IdKorelacji" type="xs:string"/>
        <xs:element name="Scoring" type="xs:integer"/>
        <xs:element name="LiczbaCzynnychZobowiazan" type="xs:integer"/>
        <xs:element name="SumaRatMiesiecznych" type="xs:decimal"/>
        <xs:element name="Opoznienia" minOccurs="0"/>
        <xs:element name="WpisyNegatywne" type="xs:integer"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

**Odpowiedź jest walidowana schemą przed użyciem.** Bez tego błąd po stronie
rejestru wchodzi do scoringu jako dane i wypływa dopiero w decyzji kredytowej,
czyli w miejscu, w którym kosztuje najwięcej.

## 3. Uruchomienie kredytu - SOAP do core banking

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:core="http://bank.pl/core/kredyty/v3">
  <soapenv:Body>
    <core:UruchomKredytRequest>
      <core:IdSprawy>KRD-2026-000184</core:IdSprawy>
      <core:NumerUmowy>UM/2026/09/000184</core:NumerUmowy>
      <core:Pesel>90010112345</core:Pesel>
      <core:Kwota waluta="PLN">45000.00</core:Kwota>
      <core:OkresMiesiecy>48</core:OkresMiesiecy>
      <core:Oprocentowanie>9.99</core:Oprocentowanie>
      <core:RachunekWyplaty>PL61109010140000071219812874</core:RachunekWyplaty>
      <core:DataPodpisania>2026-09-20</core:DataPodpisania>
    </core:UruchomKredytRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

Operacja musi być **idempotentna względem `IdSprawy`**: ponowienie po timeoucie
nie może uruchomić drugiego kredytu. Powtórzone żądanie z tym samym `IdSprawy`
zwraca to samo potwierdzenie zamiast zakładać nową umowę.

## Obsługa błędów - zasada wspólna

| Rodzaj błędu | Przykład | Reakcja procesu |
|---|---|---|
| Przejściowy | timeout, HTTP 503, `SOAP Fault` z kodem technicznym | ponowienie wg tabeli, potem eskalacja do człowieka |
| Trwały | brak zgody klienta, PESEL nieznany w rejestrze | zadanie dla doradcy, bez ponawiania |
| Niepełne dane | brak odpowiedzi KRD | proces idzie dalej z obniżoną punktacją, fakt zapisany w sprawie |

Ponowienie ma sens tylko przy błędzie, który **mija sam**. Ponawianie odmowy
uprawnień to czekanie na wynik, który się nie zmieni - i z punktu widzenia klienta
wygląda identycznie jak awaria.

---
Autor: Mateusz Biernat
