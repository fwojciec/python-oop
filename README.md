# Przykład OOP w Pythonie

## Problem

Umowy licencyjne na wydawanie książek wymagają od wydawców okresowego raportowania sprzedaży licencjodawcy. Honoraria obliczane są od ceny detalicznej lub ceny zbytu książki zgodnie ze stawkami honorariów określonymi w umowie. Większość umów dziś stosuje tzw. **progresywne stawki honorariów**, to znaczy stawki które rosną wraz z całkowitą sprzedażą książki w danym formacie. Za sprzedaż pierwszych 2000 egzemplrzy książki, na przykład, wydawca płaci licencjodawcy honorarium na poziomie 7%, za kolejne 2000 egzemplarzy 8%, a od 4000 egzemplarzy w górę -- 9%. Podobne rozwiązania stosuje się również w przypadku ebooków i audiobooków.

Progresywne stawki honorariów powodują, że wyliczanie należności honoraryjnych jest nieco złożone, bo trzeba przez cały czas pilnować na jakim "pułapie" honorariów znajduje się wydawca raportując sprzedaż kolejnego egzempalrza. W praktyce raporty często zawierają błędne wyliczenia, zwłaszcza gdy mowa o kolejnym z rzędu raporcie za dany tytuł -- kilka lat od oryginalnego wydania.

Ta mała aplikacja to przykładowa implementacja mechanizmu obliczania tantiem z użyciem progresywnych stawek honorariów.

## Implementacja

Sercem tej implementacji jest klasa `RoyaltyStack` - to rodzaj state machine (automatu stanów), który potrafi rejestrować sprzedaż pozytywną i negatywną (zwroty) i przydzielać właściwą stawkę honorarium każdemu sprzedanemu lub zwróconemu egzemplarzowi.

Klasa `Agreement` reprezentuje umowę licencyjną.

Klasa `Right` (oraz subklasy `TradeVolumeRight` i `EbookRight`) reprezentują kategegorie praw przyznawanych w ramach umowy licencyjnej.

Klasa `Statement` (oraz subklasy `TradeVolumeStatement` i `EbookStatement`) reprezentują raport sprzedaży przedstawianiy przez wydawcę licencjodawcy.

Część klas jest napisanych ręcznie, kilka z użycie generatora `dataclass` dostępnego w nowych wersjach Pythona.

## Przykład użycia

```python
>>> from datetime import date
>>> from decimal import Decimal
>>> tvr = TradeVolumeRight.from_string('7-5000,8-10000,9-0')
>>> er = EbookRight.from_string('25-0')
>>> a = Agreement(1500, [tvr, er])
>>> s1 = TradeVolumeStatement(date(2016, 6, 30), 143, Decimal('28.40'))
>>> s2 = EbookStatement(date(2016, 6, 30), 89, Decimal('13.56'))
>>> a.add_statements([s1, s2])
>>> report_items = a.apply_statements()
>>> pprint(list(report_items))
[ReportItem(date=datetime.date(2016, 6, 30), right='trade_volume', copies=143, rate='7%', price=Decimal('28.40'), advance_left=Decimal('1215.716'), due=Decimal('284.284')),
 ReportItem(date=datetime.date(2016, 6, 30), right='ebook', copies=89, rate='25%', price=Decimal('13.56'), advance_left=Decimal('914.006'), due=Decimal('301.71'))]
```

## Testy

Aby uruchomić testy należy zainstalować `pytest` a następnie:

```
> pytest
```
