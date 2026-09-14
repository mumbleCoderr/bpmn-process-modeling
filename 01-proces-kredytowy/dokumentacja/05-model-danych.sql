-- =====================================================================
-- Model danych procesu KRD-001: obsluga wniosku kredytowego (TO-BE)
-- Dialekt: ANSI SQL / MySQL 8
-- Autor: Mateusz Biernat
--
-- Zakres: dane sprawy prowadzonej przez silnik procesowy. Ewidencja
-- ksiegowa kredytu zostaje w systemie centralnym - tu trzymamy droge
-- wniosku do decyzji, a nie sam kredyt.
-- =====================================================================

CREATE TABLE klient (
    id_klienta      BIGINT       NOT NULL AUTO_INCREMENT,
    pesel           CHAR(11)     NOT NULL,
    imie            VARCHAR(60)  NOT NULL,
    nazwisko        VARCHAR(80)  NOT NULL,
    email           VARCHAR(120) NOT NULL,
    telefon         VARCHAR(20)  NOT NULL,
    utworzono       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_klienta),
    UNIQUE KEY uk_klient_pesel (pesel)
);

CREATE TABLE wniosek (
    id_sprawy               VARCHAR(20)    NOT NULL,   -- KRD-2026-000184
    id_klienta              BIGINT         NOT NULL,
    kanal                   VARCHAR(30)    NOT NULL,   -- ODDZIAL / BANKOWOSC_ELEKTRONICZNA
    kwota                   DECIMAL(12,2)  NOT NULL,
    waluta                  CHAR(3)        NOT NULL DEFAULT 'PLN',
    okres_miesiecy          SMALLINT       NOT NULL,
    cel                     VARCHAR(30)    NOT NULL,
    dochod_netto_miesieczny DECIMAL(12,2)  NOT NULL,
    zrodlo_dochodu          VARCHAR(30)    NOT NULL,
    staz_miesiecy           SMALLINT       NOT NULL,
    status                  VARCHAR(30)    NOT NULL,   -- W_WALIDACJI / W_ANALIZIE / DECYZJA / ODRZUCONY / URUCHOMIONY / WYGASL
    zlozono                 DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    zamknieto               DATETIME       NULL,
    PRIMARY KEY (id_sprawy),
    CONSTRAINT fk_wniosek_klient FOREIGN KEY (id_klienta) REFERENCES klient (id_klienta),
    CONSTRAINT ck_wniosek_kwota  CHECK (kwota > 0),
    CONSTRAINT ck_wniosek_okres  CHECK (okres_miesiecy BETWEEN 3 AND 120),
    KEY ix_wniosek_status_data (status, zlozono)         -- raport "co wisi i od kiedy"
);

CREATE TABLE raport_rejestru (
    id_raportu     BIGINT       NOT NULL AUTO_INCREMENT,
    id_sprawy      VARCHAR(20)  NOT NULL,
    rejestr        VARCHAR(10)  NOT NULL,               -- BIK / KRD / CEIDG
    pobrano        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_pobrania VARCHAR(20) NOT NULL,               -- OK / BLAD / BRAK_ZGODY
    tresc          LONGTEXT     NULL,                   -- oryginalny XML/JSON odpowiedzi
    PRIMARY KEY (id_raportu),
    CONSTRAINT fk_raport_wniosek FOREIGN KEY (id_sprawy) REFERENCES wniosek (id_sprawy),
    KEY ix_raport_sprawa (id_sprawy, rejestr)
);
-- Tresc odpowiedzi trzymamy w oryginale, nie tylko przetworzona: przy sporze
-- z klientem albo kontroli liczy sie to, co rejestr realnie odeslal tamtego dnia.

CREATE TABLE scoring (
    id_scoringu    BIGINT       NOT NULL AUTO_INCREMENT,
    id_sprawy      VARCHAR(20)  NOT NULL,
    wersja_modelu  VARCHAR(20)  NOT NULL,               -- np. SC-2026.02
    punktacja      SMALLINT     NOT NULL,
    klasa_ryzyka   CHAR(1)      NOT NULL,               -- A..E
    dti            DECIMAL(5,2) NULL,                   -- rata do dochodu, w procentach
    policzono      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_scoringu),
    CONSTRAINT fk_scoring_wniosek FOREIGN KEY (id_sprawy) REFERENCES wniosek (id_sprawy),
    CONSTRAINT ck_scoring_punktacja CHECK (punktacja BETWEEN 0 AND 100),
    CONSTRAINT ck_scoring_klasa CHECK (klasa_ryzyka IN ('A','B','C','D','E')),
    KEY ix_scoring_sprawa (id_sprawy)
);
-- wersja_modelu nie jest ozdoba: bez niej po zmianie wag nie da sie odtworzyc,
-- dlaczego wniosek sprzed pol roku dostal klase D.

CREATE TABLE decyzja (
    id_decyzji     BIGINT       NOT NULL AUTO_INCREMENT,
    id_sprawy      VARCHAR(20)  NOT NULL,
    typ            VARCHAR(20)  NOT NULL,               -- AUTOMATYCZNA / ANALITYK / KOMITET
    wynik          VARCHAR(20)  NOT NULL,               -- POZYTYWNA / NEGATYWNA
    uzasadnienie   VARCHAR(500) NULL,
    id_decydenta   VARCHAR(40)  NULL,                   -- NULL dla decyzji automatycznej
    kwota_przyznana DECIMAL(12,2) NULL,
    wazna_do       DATE         NOT NULL,               -- data wydania + 14 dni
    wydano         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_decyzji),
    CONSTRAINT fk_decyzja_wniosek FOREIGN KEY (id_sprawy) REFERENCES wniosek (id_sprawy),
    CONSTRAINT ck_decyzja_wynik CHECK (wynik IN ('POZYTYWNA','NEGATYWNA')),
    KEY ix_decyzja_sprawa (id_sprawy)
);

CREATE TABLE zadanie (
    id_zadania     BIGINT       NOT NULL AUTO_INCREMENT,
    id_sprawy      VARCHAR(20)  NOT NULL,
    kod_zadania    VARCHAR(30)  NOT NULL,               -- T_analiza, T_podpis, ... - zgodne z BPMN
    rola           VARCHAR(40)  NOT NULL,
    wykonawca      VARCHAR(40)  NULL,
    przydzielono   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    termin_sla     DATETIME     NOT NULL,
    zakonczono     DATETIME     NULL,
    wynik          VARCHAR(30)  NULL,
    PRIMARY KEY (id_zadania),
    CONSTRAINT fk_zadanie_wniosek FOREIGN KEY (id_sprawy) REFERENCES wniosek (id_sprawy),
    KEY ix_zadanie_otwarte (wykonawca, zakonczono),      -- lista zadan uzytkownika
    KEY ix_zadanie_sla (termin_sla, zakonczono)          -- co przekracza SLA
);
-- kod_zadania trzyma identyfikator z modelu BPMN, a nie nazwe wyswietlana.
-- Nazwa zadania bywa poprawiana redakcyjnie; raport historyczny nie moze sie
-- wtedy rozjechac.

CREATE TABLE historia_sprawy (
    id_wpisu       BIGINT       NOT NULL AUTO_INCREMENT,
    id_sprawy      VARCHAR(20)  NOT NULL,
    zdarzenie      VARCHAR(40)  NOT NULL,
    status_przed   VARCHAR(30)  NULL,
    status_po      VARCHAR(30)  NULL,
    autor          VARCHAR(40)  NOT NULL,               -- login albo SYSTEM
    szczegoly      VARCHAR(500) NULL,
    kiedy          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_wpisu),
    CONSTRAINT fk_historia_wniosek FOREIGN KEY (id_sprawy) REFERENCES wniosek (id_sprawy),
    KEY ix_historia_sprawa (id_sprawy, kiedy)
);

-- =====================================================================
-- Zapytania raportowe - te same liczby, ktore stoja w dokumencie o miernikach
-- =====================================================================

-- 1. Sredni czas obslugi wniosku w dniach, w podziale na sciezke decyzji
SELECT d.typ,
       COUNT(*)                                                   AS liczba_spraw,
       ROUND(AVG(TIMESTAMPDIFF(HOUR, w.zlozono, d.wydano) / 24), 2) AS sredni_czas_dni
FROM decyzja d
JOIN wniosek w ON w.id_sprawy = d.id_sprawy
GROUP BY d.typ
ORDER BY liczba_spraw DESC;

-- 2. Udzial decyzji automatycznych (cel: 35% wnioskow bez udzialu czlowieka)
SELECT
    ROUND(100.0 * SUM(CASE WHEN typ = 'AUTOMATYCZNA' THEN 1 ELSE 0 END) / COUNT(*), 1)
        AS procent_automatycznych
FROM decyzja
WHERE wydano >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY);

-- 3. Zadania po terminie SLA, wedlug roli
SELECT rola,
       COUNT(*) AS po_terminie
FROM zadanie
WHERE zakonczono IS NULL
  AND termin_sla < NOW()
GROUP BY rola
ORDER BY po_terminie DESC;

-- 4. Lejek: ile wnioskow dochodzi do kolejnych etapow
SELECT status, COUNT(*) AS liczba
FROM wniosek
WHERE zlozono >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
GROUP BY status
ORDER BY liczba DESC;

-- 5. Wnioski wygasle z winy terminu podpisu (14 dni)
SELECT w.id_sprawy, w.kwota, d.wydano, d.wazna_do
FROM wniosek w
JOIN decyzja d ON d.id_sprawy = w.id_sprawy AND d.wynik = 'POZYTYWNA'
WHERE w.status = 'WYGASL'
ORDER BY d.wazna_do DESC;
