import pytest
from datetime import date
from decimal import Decimal
from royalties import (Agreement, TradeVolumeRight, Right, EbookRight, Step, Statement,
                       TradeVolumeStatement, EbookStatement, RoyaltyStack, ReportItem)
from pprint import pprint


@pytest.fixture(scope='function')
def rs():
    p = [Step(7, 5000), Step(8, 10000), Step(9, 0)]
    return RoyaltyStack(p)


@pytest.fixture(scope='function')
def tvr():
    return TradeVolumeRight.from_string('7-5000,8-10000,9-0')


@pytest.fixture(scope='function')
def er():
    return EbookRight.from_string('25-1000,40-0')


@pytest.fixture(scope='module')
def tvs1():
    return TradeVolumeStatement(date(2016, 6, 30), 143, Decimal('28.40'))


@pytest.fixture(scope='module')
def tvs2():
    return TradeVolumeStatement(date(2016, 12, 31), 512, Decimal('34.90'))


@pytest.fixture(scope='module')
def tvs3():
    return TradeVolumeStatement(date(2017, 6, 30), -45, Decimal('33.20'))


@pytest.fixture(scope='module')
def es1():
    return EbookStatement(date(2016, 6, 30), 89, Decimal('13.56'))


@pytest.fixture(scope='module')
def es2():
    return EbookStatement(date(2016, 12, 31), 124, Decimal('14.23'))



def test_new_trade_volume_right_from_string(tvr):
    assert tvr.name == 'trade volume'
    assert tvr.progression == [Step(7, 5000), Step(8, 10000), Step(9, 0)]


def test_raises_value_error_for_invalid_progressions():
    ends_with_non_0_limit = (Step(7, 5000), Step(8, 10000))
    rate_decreases = (Step(7, 5000), Step(6, 10000), Step(9, 0))
    limit_decreases = (Step(7, 5000), Step(8, 2000), Step(9, 0))
    has_negative_rate = (Step(-4, 1000), Step(7, 0))
    has_negative_limit = (Step(7, -1000), Step(8, 0))
    for p in [
        ends_with_non_0_limit,
        rate_decreases,
        limit_decreases,
        has_negative_rate,
        has_negative_limit
    ]:
        with pytest.raises(ValueError):
            TradeVolumeRight(p)


def test_trade_volume_right_repr(tvr):
    exp = 'TradeVolumeRight([Step(rate=7, limit=5000), Step(rate=8, limit=10000), Step(rate=9, limit=0)])'
    assert repr(tvr) == exp


def test_new_ebook_right_from_string(er):
    assert er.name == 'ebook'
    assert er.progression == [Step(25, 1000), Step(40, 0)]


def test_ebook_right_repr(er):
    exp = 'EbookRight([Step(rate=25, limit=1000), Step(rate=40, limit=0)])'
    assert repr(er) == exp


def test_create_agreement_with_just_advance():
    a = Agreement(advance=1500)
    assert a.advance == Decimal('1500')


def test_create_agreement_with_advance_and_rights(tvr, er):
    exp_rights = {'trade volume': tvr, 'ebook': er}
    a = Agreement(1500, [tvr, er])
    assert a.advance == Decimal('1500')
    assert a.rights == exp_rights


def test_add_trade_volume_right_to_agreement(tvr):
    a = Agreement(1500)
    a.add_right(tvr)
    assert a.rights == {'trade volume': tvr}


def test_add_ebook_right_to_agreement(er):
    a = Agreement(1500)
    a.add_right(er)
    assert a.rights == {'ebook': er}


def test_agreement_repr(tvr, er):
    a = Agreement(1500, [tvr, er])
    exp = 'Agreement(1500, (TradeVolumeRight([Step(rate=7, limit=5000), Step(rate=8, limit=10000), Step(rate=9, limit=0)]), EbookRight([Step(rate=25, limit=1000), Step(rate=40, limit=0)])))'
    assert repr(a) == exp


def test_create_trade_volume_statement(tvs1):
    assert tvs1.date == date(2016, 6, 30)
    assert tvs1.copies == 143
    assert tvs1.price == Decimal('28.40')
    assert tvs1.name == 'trade volume'


def test_create_ebook_statement(es1):
    assert es1.date == date(2016, 6, 30)
    assert es1.copies == 89
    assert es1.price == Decimal('13.56')
    assert es1.name == 'ebook'


def test_add_statements_to_agreement(tvr, er, tvs1, es1):
    a = Agreement(1500, [tvr, er])
    a.add_statements([tvs1, es1])
    assert a.statements == [tvs1, es1]


def test_agreement_sort_statements(tvr, er, tvs1, es1, tvs2, es2):
    a = Agreement(1500, [tvr, er])
    a.add_statements([es2, tvs2, tvs1, es1])
    a._sort_statements()
    assert a.statements == [tvs1, es1, es2, tvs2]


def test_royalty_stack_push(rs):
    assert list(rs.push(4999)) == [(4999, 7)]
    assert list(rs.push(5002)) == [(1, 7), (5000, 8), (1, 9)]
    assert list(rs.push(7000)) == [(7000, 9)]


def test_royalty_stack_pop(rs):
    list(rs.push(12500))
    assert list(rs.pop(6000)) == [(-2500, 9), (-3500, 8)]


def test_royalty_stack_can_deal_with_negative_cursor(rs):
    assert list(rs.pop(500)) == [(-500, 7)]
    assert list(rs.push(5500)) == [(5500, 7)]


def test_royalty_stack_repr(rs):
    exp = 'RoyaltyStack([Step(rate=7, limit=5000), Step(rate=8, limit=10000), Step(rate=9, limit=0)])'
    assert repr(rs) == exp


def test_royalty_stack_resets(rs):
    list(rs.push(500))
    rs.reset()
    assert list(rs.push(5000)) == [(5000, 7)]


def test_apply_statements(tvr, er, tvs1, es1, tvs2, es2, tvs3):
    a = Agreement(1500, [tvr, er])
    a.add_statements([tvs1, es1, tvs2, es2, tvs3])
    res = a.apply_statements()
    exp = [
        ReportItem(date=date(2016, 6, 30), right='trade volume', copies=143, rate='7%',
                   price=Decimal('28.40'), advance_left=Decimal('1215.716'), due=Decimal('284.284')),
        ReportItem(date=date(2016, 6, 30), right='ebook', copies=89, rate='25%',
                   price=Decimal('13.56'), advance_left=Decimal('914.006'), due=Decimal('301.71')),
        ReportItem(date=date(2016, 12, 31), right='trade volume', copies=512, rate='7%',
                   price=Decimal('34.90'), advance_left=Decimal('-336.810'), due=Decimal('1250.816')),
        ReportItem(date=date(2016, 12, 31), right='ebook', copies=124, rate='25%',
                   price=Decimal('14.23'), advance_left=Decimal('-777.940'), due=Decimal('441.13')),
        ReportItem(date=date(2017, 6, 30), right='trade volume', copies=-45, rate='7%',
                   price=Decimal('33.20'), advance_left=Decimal('-673.360'), due=Decimal('-104.58'))
    ]
    assert list(res) == exp
