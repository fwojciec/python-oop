import operator
from datetime import date
from decimal import Decimal
from typing import Union, List, Tuple, NamedTuple, Optional, Dict, Iterator
from dataclasses import dataclass
from itertools import chain, groupby
from pprint import pprint


class Step(NamedTuple):
    'Step to krok w progresji honorariów.'

    rate: int
    limit: int


@dataclass(frozen=True)
class Statement:
    '''Statement to raport sprzedaży wysyłany właścicielowi praw przez
    wydawcę. Określa cenę i ilość egzemplarzy książki sprzedanych w danym
    okresie rozliczeniowym na potrzeby wyliczenia tantiem.
    '''
    date: date
    copies: int
    price: Decimal

    @property
    def name(self):
        raise NotImplementedError('Use one of the subclasses')


class TradeVolumeStatement(Statement):
    'TradeVolumeStatement to raport sprzedaży wydania papierowego książki.'

    @property
    def name(self):
        return "trade volume"


class EbookStatement(Statement):
    'EbookStatement to raport sprzedaży wydania ebook książki.'

    @property
    def name(self):
        return "ebook"


class RoyaltyStack:
    '''Royalties are calculated according to a progressive royalty scale.
    The higher the sales, the higher the royalty rate. RoyaltyStack keeps
    history of copies reported so far and makes it possible to apply sales
    and returns at the rates resulting from the total number of copies reported
    to date and the defined progression scale.

    push method is used to add positive sales to the overall tally.
    pop method is used to add negative sales (returns) to the overall tally.

    The return value of both methods is a generator yielding copies/rate tuples
    corresponding to the state adjustment caused by the operation.
    '''

    def __init__(self, progression: List[Step]):
        self._progression = progression
        self._rates = [step.rate for step in self._progression]
        self._rate_index = 0
        self._init_cursor()
        self._limits: Dict[int, int] = {}
        for i, step in enumerate(self._progression):
            if i == 0 or step.limit == 0:
                self._limits[step.rate] = step.limit
            else:
                prev_limit = self._progression[i-1].limit
                self._limits[step.rate] = step.limit - prev_limit

    def __repr__(self):
        return f'{self.__class__.__name__}({self._progression})'

    def push(self, copies: int) -> Iterator[Tuple[int, int]]:
        '''Push adds copies to stack. It returns a generator of (rate, copies)
        tuples corresponding to the performed state adjustment.
        '''
        while copies > 0:
            cr = self._rates[self._rate_index]
            has_no_upper_limit = self._limits[cr] == 0
            cursor_after_apply = self._cursor[cr] + copies
            can_process_at_current_rate = cursor_after_apply <= self._limits[cr]
            if has_no_upper_limit or can_process_at_current_rate:
                yield (copies, cr)
                self._cursor[cr] += copies
                copies = 0
            else:
                to_apply = self._limits[cr] - self._cursor[cr]
                yield (to_apply, cr)
                self._cursor[cr] += to_apply
                self._rate_index += 1
                copies -= to_apply

    def pop(self, copies: int) -> Iterator[Tuple[int, int]]:
        '''Pop removes copies from stack. It returns a generator of (rate,
        copies) tuples corresponding to the performed state adjustment.
        '''
        while copies > 0:
            cr = self._rates[self._rate_index]
            has_no_lower_limit = self._rate_index == 0
            can_process_at_current_rate = self._cursor[cr] - copies >= 0
            if has_no_lower_limit or can_process_at_current_rate:
                yield (copies * -1, cr)
                self._cursor[cr] -= copies
                copies = 0
            else:
                to_apply = self._cursor[cr]
                yield (to_apply * -1, cr)
                self._cursor[cr] = 0
                self._rate_index -= 1
                copies -= to_apply

    def reset(self):
        '''Resets re-initializes the RoyaltyStack removing all artefacts of
        prior operations.
        '''
        self._rate_index = 0
        self._init_cursor()

    def _init_cursor(self):
        self._cursor = {step.rate: 0 for step in self._progression}


@dataclass
class ReportItem:
    'ReportItem to wpis w podsumowaniu należności honoraryjnych.'

    date: date
    right: str
    copies: int
    rate: str
    price: Decimal
    advance_left: Optional[Decimal]
    due: Decimal


def progression_is_valid(progression: List[Step]):
    '''Progresja honorariów jest poprawna kiedy w kolejnych krokach progresji
    tak stawka, jak i limit rosną. Limit w ostatnim stopniu progresji musi
    wynosić zero.
    '''
    for i, step in enumerate(progression):
        # first step
        if i == 0:
            if step.rate < 0 or step.limit < 0:
                return False
        # last step
        elif i == len(progression) - 1:
            if step.rate <= progression[i-1].rate or step.limit != 0:
                return False
        # middle steps
        else:
            prev_rate = progression[i-1].rate
            prev_limit = progression[i-1].limit
            if step.rate <= prev_rate or step.limit <= prev_limit:
                return False
    return True


class Right:
    'Right to prawo przyznane w ramach umowy licencyjnej.'

    def __init__(self, progression: List[Step]):
        if not progression_is_valid(progression):
            raise ValueError
        self.progression = progression
        self._royalty_stack = RoyaltyStack(progression)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.progression})'

    @classmethod
    def from_string(cls, string: str):
        'Umożliwia łatwiejszą inicjalizację klasy.'
        progression = []
        for step in string.split(','):
            rate, limit = step.split('-')
            progression.append(Step(rate=int(rate), limit=int(limit)))
        return cls(progression)

    def reset(self):
        'Przywraca stan początkowy.'
        self._royalty_stack.reset()

    def apply_statement(self, stmt: Statement) -> Iterator[ReportItem]:
        '''Dodaje raport sprzedaży za pomocą jednej z pomocniczych funkcji
        w zależności od tego czy raport dotyczy sprzedaży czy zwrotów.
        '''
        for copies, rate in self._get_iterator(stmt.copies):
            yield ReportItem(
                date=stmt.date,
                right=self.name,
                copies=copies,
                rate=f'{rate}%',
                price=stmt.price,
                advance_left=None,
                due=copies * rate * stmt.price / 100
            )

    @property
    def name(self):
        raise NotImplementedError('Use a subclass')

    def _get_iterator(self, copies: int):
        if copies < 0:
            return self._royalty_stack.pop(copies * -1)
        return self._royalty_stack.push(copies)


class TradeVolumeRight(Right):
    '''TradeVolumeRight to prawo do sprzedaży książek papierowych w
    tradycyjnych kanałach sprzedaży (księgarniach).
    '''

    @property
    def name(self):
        return "trade volume"


class EbookRight(Right):
    'EbookRight to prawo do sprzedaży książek w fromie ebooka.'

    @property
    def name(self):
        return "ebook"


class Agreement:
    ''' Agreement to umowa licencyjna. Posiada advance (zaliczkę) oraz listę
    praw (rights) przyznanych w licencji. Zaliczka jest przedpłatą za tantiemy
    od przyszłej sprzedaży. Prawa umożliwiają sprzedawanie wydań ksiąki w
    różnych formatach/kanałach dystrybucyjnych.
    '''

    def __init__(self, advance: Union[int, float, str], rights: Optional[List[Right]] = None):
        self.advance = Decimal(advance)
        self.rights: Dict[str, Right] = dict()
        self.statements: List[Statement] = []
        if rights is not None:
            for right in rights:
                self.rights[right.name] = right

    def __repr__(self):
        return f'{self.__class__.__name__}({self.advance}, {tuple(self.rights.values())})'

    def add_right(self, right: Right):
        'Dodaje prawo do umowy.'
        self.rights[right.name] = right

    def add_statements(self, statements: List[Statement]):
        'Dodaje raporty sprzedaży do umowy.'
        self.statements.extend(statements)

    def apply_statements(self) -> Iterator[ReportItem]:
        'Podlicza należności wynikające z dodanych raportów sprzedaży.'
        self._sort_statements()
        self._reset_rights()
        adv_left = self.advance
        raw_items = [self.rights[s.name].apply_statement(s)
                     for s in self.statements]
        for item in chain.from_iterable(raw_items):
            adv_left -= item.due
            item.advance_left = adv_left
            yield item

    def print_report(self):
        'Drukuje podsumowanie należności honoraryjnych.'
        for k, v in groupby(self.apply_statements(), operator.attrgetter('date')):
            print(k)
            pprint(list(v))

    def _reset_rights(self):
        for right in self.rights.values():
            right.reset()

    def _sort_statements(self):
        self.statements.sort(key=operator.attrgetter('date'))

