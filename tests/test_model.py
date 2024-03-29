import datetime
from unittest.mock import ANY

import pytest
from wadwise import db, model as m


def get_acc(name):
    parent = None
    parts = name.split(':')
    for p in parts:
        parent = m.account_by_name(parent and parent['aid'], p)
        if not parent:
            return None
    return parent


def make_acc(name, type=None):
    head, _, acc = name.rpartition(':')
    parent = get_acc(head)
    assert parent
    return m.create_account(parent['aid'], acc, type or parent['type'])


@pytest.fixture
def dbconn(mocker):
    mocker.patch('wadwise.db.DB', '/tmp/wadwise-test.sqlite')
    db._get_connection.cache_clear()
    m.drop_tables()
    m.create_tables()
    with m.transaction():
        m.create_account(None, 'a', m.AccType.ASSET)
        m.create_account(None, 'e', m.AccType.EXPENSE)
        m.create_account(None, 'i', m.AccType.INCOME)
        m.create_account(None, 'l', m.AccType.LIABILITY)
        m.create_account(None, 'q', m.AccType.EQUITY)


def test_simple(dbconn):
    a = make_acc('a:cash')
    e = make_acc('e:food')
    m.create_transaction(m.op2(a, e, 100, 'USD'))
    result = m.balance()
    assert result == {a: {'USD': -100}, e: {'USD': 100}}


def test_account_flow(dbconn):
    aid = make_acc('a:cash', type='assets')
    a = m.account_by_id(aid)
    a['name'] = 'foo'
    m.update_account(**a)
    a = m.account_by_id(aid)
    assert a['name'] == 'foo'

    accs = sorted(it['name'] for it in m.get_sub_accounts(None))
    assert accs == ['a', 'e', 'i', 'l', 'q']

    accs = sorted(it['name'] for it in m.get_sub_accounts(get_acc('a')['aid']))
    assert accs == ['foo']

    make_acc('a:bank')
    assert m.account_list()


def test_delete_account(dbconn):
    a1 = make_acc('a:bank')
    a2 = make_acc('a:bank:main')
    m.delete_account(a1, get_acc('e')['aid'])
    a = m.account_by_id(a2)
    assert a['parent'] == get_acc('e')['aid']


def test_transaction_flow(dbconn):
    a = make_acc('a:cash')
    e = make_acc('e:food')
    tid = m.create_transaction(m.op2(a, e, 100, 'USD'), 10)

    m.update_transaction(tid, m.op2(a, e, 200, 'USD'), 10, 'foo')
    result = m.balance()
    assert result == {a: {'USD': -200}, e: {'USD': 200}}

    data, = m.account_transactions(tid=tid)
    assert data == {
        'tid': tid,
        'date': datetime.datetime(1970, 1, 1, 1, 0, 10),
        'desc': 'foo',
        'ops': [(a, -200.0, 'USD'),
                (e, 200.0, 'USD')],
        'split': False,
        'dest': None,
        'amount': 0,
        'src': a,
        'cur': 'USD'
    }

    m.delete_transaction(tid)
    result = m.balance()
    assert result == {}

    # make shure transaction cleans up ops
    ops = db.select('ops', '*', tid=tid)
    assert not ops


def test_balance_for_date_range(dbconn):
    a = make_acc('a:cash')
    e = make_acc('e:food')
    i = make_acc('i:salary')
    m.create_transaction(m.op2(a, e, 100, 'USD'), 10)
    m.create_transaction(m.op2(a, e, 20, 'USD'), 50)
    m.create_transaction(m.op2(i, a, 200.4, 'USD'), 100)
    m.create_transaction(m.op2(a, e, 30, 'USD'), 150)

    result = m.balance(end=50)
    assert result == {a: {'USD': -100}, e: {'USD': 100}}

    result = m.balance(start=50, end=150)
    assert result == {a: {'USD': 180.4}, e: {'USD': 20}, i: {'USD': -200.4}}

    result = m.balance(start=100)
    assert result == {a: {'USD': 170.4}, e: {'USD': 30}, i: {'USD': -200.4}}

    result = m.balance()
    assert result == {a: {'USD': 50.4}, e: {'USD': 150}, i:{'USD': -200.4}}


def test_params(dbconn):
    assert m.get_param('boo', 'foo') == 'foo'
    m.set_param('boo', 'bar')
    assert m.get_param('boo') == 'bar'


def test_create_initial(dbconn):
    m.create_initial_accounts()
    db.execute('DELETE FROM accounts')
    m.create_initial_accounts()
