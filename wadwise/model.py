import time
import json
import operator
from datetime import datetime
from sqlbind import not_none

from wadwise.db import (gen_id, insert, transaction, execute, update,
                        delete, replace, Q, select)


class AccType:
    INCOME = 'i'
    EXPENSE = 'e'
    EQUITY = 'q'
    ASSET = 'a'
    LIABILITY = 'l'

acc_types = [(v, k.capitalize()) for k, v in vars(AccType).items() if not k.startswith('_')]
sheet_accounts = {AccType.EQUITY, AccType.ASSET, AccType.LIABILITY}


@transaction()
def create_account(parent, name, type, desc=None, aid=None, is_placeholder=False):
    aid = aid or gen_id()
    insert('accounts', aid=aid, parent=parent, name=name, type=type, desc=desc,
           is_placeholder=is_placeholder)
    return aid


@transaction()
def update_account(aid, parent, name, type, desc, is_placeholder):
    update('accounts', 'aid', aid=aid, parent=parent, name=name, type=type,
           desc=desc, is_placeholder=is_placeholder)


@transaction()
def create_transaction(ops, date=None, desc=None):
    tid = gen_id()
    insert('transactions', tid=tid, date=date or int(time.time()), desc=desc)
    for op in ops:
        insert('ops', tid=tid, aid=op['aid'], amount=round(op['amount'] * 100), cur=op['cur'])
    return tid


@transaction()
def update_transaction(tid, ops, date, desc):
    update('transactions', 'tid', tid=tid, date=date, desc=desc)
    delete('ops', tid=tid)
    for op in ops:
        insert('ops', tid=tid, aid=op['aid'], amount=round(op['amount'] * 100), cur=op['cur'])


@transaction()
def delete_transaction(tid):
    delete('ops', tid=tid)
    delete('transactions', tid=tid)


def account_transactions(**eq):
    result = Q(q := Q.p, f'''\
        SELECT tid, date, desc, json_array(json_group_array(aid),
                                           json_group_array(amount/100.0),
                                           json_group_array(cur)) ops_raw
        FROM (SELECT distinct(tid) FROM ops {q.WHERE(**eq)})
        INNER JOIN transactions t USING(tid)
        INNER JOIN ops USING(tid)
        GROUP BY tid
        ORDER BY date DESC
    ''').all()

    aid = eq.pop('aid', None)
    by_amount = operator.itemgetter(1)

    for it in result:
        it['date'] = datetime.fromtimestamp(it['date'])
        accs, amounts, curs = json.loads(it.pop('ops_raw'))
        it['ops'] = sorted(zip(accs, amounts, curs), key=by_amount)
        it['split'] = len(accs) != 2 or len(set(curs)) > 1
        it['dest'] = aid
        if not it['split']:
            it['amount'] = sum(a for op_aid, a, cur in it['ops'] if aid == op_aid)
            it['src'] = next(a for a in accs if a != aid)
            it['cur'] = curs[0]

    return result


@transaction()
def delete_account(aid, new_parent):
    assert aid
    update('accounts', 'parent', aid, parent=new_parent)
    update('ops', 'aid', aid, aid=new_parent)
    delete('accounts', aid=aid)


def account_by_name(parent, name):
    return select('accounts', '*', parent=parent, name=name).one()


def account_by_id(aid):
    return select('accounts', '*', aid=aid).one()


def get_sub_accounts(parent):
    return select('accounts', '*', parent=parent).all()


def get_param(name, default=None):
    return select('params', 'value', name=name).scalar(default)


@transaction()
def set_param(name, value):
    replace('params', name=name, value=value)


def account_parents(aid, amap, cache):
    if aid is None:
        return ()

    if aid in cache:
        return cache[aid]

    cur = amap[aid]
    result = cache[aid] = account_parents(cur['parent'], amap, cache) + (aid,)
    return result


class AccountMap(dict):
    pass


def account_list():
    amap = AccountMap({it['aid']: it for it in Q(None, 'SELECT * FROM accounts')})
    amap[None] = {}

    cache = {}
    for it in amap.values():
        if not it.get('aid'): continue
        it['is_sheet'] = it['type'] in sheet_accounts
        it['parents'] = account_parents(it['parent'], amap, cache)
        it.setdefault('children', [])
        amap[it['parent']].setdefault('children', []).append(it['aid'])

    amap.top = amap.pop(None)['children']
    for it in amap.values():
        if not it.get('aid'): continue
        it['full_name'] = ':'.join([amap[p]['name'] for p in it['parents']] + [it['name']])
    return amap


def op(aid, amount, currency):
    return {'aid': aid, 'amount': amount, 'cur': currency}


def op2(a1, a2, amount, currency):
    return op(a1, -amount, currency), op(a2, amount, currency)


def balance(start=None, end=None):
    data = Q(q := Q.p, f'''\
        SELECT aid, cur, sum(amount) / 100.0 AS total
        FROM transactions AS t
        INNER JOIN ops t USING (tid)
        {q.WHERE(q.in_range(q.t.date, not_none/start, not_none/end))}
        GROUP BY aid, cur
    ''')

    result = {}
    for it in data:
        result.setdefault(it['aid'], {})[it['cur']] = it['total']

    return result


def combine_balances(*balances):  # pragma: no cover
    result = {}
    for b in balances:
        for acc, state in b.items():
            rstate = result.setdefault(acc, {})
            for cur, amount in state.items():
                rstate[cur] = rstate.get(cur, 0) + amount

    return result


def combine_states(*states):  # pragma: no cover
    rstate = {}
    for state in states:
        for cur, amount in state.items():
            rstate[cur] = rstate.get(cur, 0) + amount
    return rstate


@transaction()
def create_tables():
    # Initial tables
    execute('''\
        CREATE TABLE IF NOT EXISTS accounts (
            aid TEXT NOT NULL PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            desc TEXT,
            parent TEXT,
            is_placeholder INTEGER NOT NULL DEFAULT 0
        )
    ''')

    execute('''\
        CREATE TABLE IF NOT EXISTS transactions (
            tid TEXT NOT NULL PRIMARY KEY,
            date INTEGER NOT NULL,
            desc TEXT
        )
    ''')

    execute('''\
        CREATE TABLE IF NOT EXISTS ops (
            tid TEXT NOT NULL,
            aid TEXT NOT NULL,
            amount INTEGER NOT NULL,
            cur TEXT NOT NULL
        )
    ''')

    execute('''\
        CREATE TABLE IF NOT EXISTS params (
            name TEXT NOT NULL PRIMARY KEY,
            value TEXT
        )
    ''')

    # Indexes
    execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_uniq_name ON accounts (parent, name)')
    execute('CREATE INDEX IF NOT EXISTS idx_ops_tid ON ops (tid)')
    execute('CREATE INDEX IF NOT EXISTS idx_ops_aid ON ops (aid)')
    execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date, tid)')


def create_initial_accounts():
    if Q(None, 'SELECT count(1) from accounts').scalar(0) > 0:
        return

    initial_accounts = [
        (AccType.INCOME, 'Income'),
        (AccType.EXPENSE, 'Expenses'),
        (AccType.ASSET, 'Assets'),
        (AccType.LIABILITY, 'Liabilities'),
        (AccType.EQUITY, 'Equity'),
    ]
    for aid, name in initial_accounts:
        Q(q := Q.p, f'INSERT OR IGNORE INTO accounts {q.VALUES(aid=aid, type=aid, name=name)}').execute()


@transaction()
def drop_tables():
    execute('DROP TABLE IF EXISTS accounts')
    execute('DROP TABLE IF EXISTS transactions')
    execute('DROP TABLE IF EXISTS ops')
    execute('DROP TABLE IF EXISTS params')
