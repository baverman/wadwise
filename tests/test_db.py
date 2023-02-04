import pytest

from wadwise.db import Q, WHERE, SET, IN, F, OR


def test_sql():
    q = Q('UPDATE boo', SET(foo=10, bar=None), WHERE(baz=20))
    sql, values = q.unwrap()
    assert sql == 'UPDATE boo SET foo = ?, bar = ? WHERE (baz = ?)'
    assert values == [10, None, 20]


def test_inline():
    q = Q('UPDATE boo', SET(foo=10, bar=None), WHERE(baz=20))
    sql, values = q.unwrap()
    assert sql == 'UPDATE boo SET foo = ?, bar = ? WHERE (baz = ?)'
    assert values == [10, None, 20]


def test_q():
    q = Q(
        'SELECT * FROM boo',
        WHERE(foo=10)
    )
    sql, values = q.unwrap()
    assert sql == 'SELECT * FROM boo WHERE (foo = ?)'
    assert values == [10]


def test_in():
    assert IN('f', []) is None

    sql, p = IN('f', [10, 10.5, 'boo', "b'b", 'b"b'], escape=True)
    assert p == ()
    assert sql == '''f IN (10,10.5,'boo','b''b','b"b')'''

    sql, p = IN('f', [10, 10.5, 'boo', "b'b", 'b"b'])
    assert sql == 'f IN ({},{},{},{},{})'
    assert p == [10, 10.5, 'boo', "b'b", 'b"b']

    sql, _ = IN('f', [None], escape=True)
    assert sql == 'f IN (NULL)';

    with pytest.raises(ValueError):
        IN('f', [[]], escape=True)


def test_f():
    assert F('boo', 'foo') == ('boo', ('foo',))

    assert F.cond(False, 'boo', 'foo') is None
    assert F.cond(True, 'boo', 'foo') == ('boo', ('foo',))

    assert F.is_true('boo', False) is None
    assert F.is_true('boo', None) is None
    assert F.is_true('boo', 'foo') == ('boo', ('foo',))


def test_or():
    assert OR(F.eq('a', 'b'), F.eq('c', 'd')) == ('(a = {} OR c = {})', ['b', 'd'])

