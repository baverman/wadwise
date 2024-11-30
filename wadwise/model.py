import json
import operator
from datetime import datetime
from typing import Any, Iterable, Literal, Optional, TypedDict, Union, overload

from sqlbind import not_none

from wadwise.db import Q, QueryList, delete, execute, gen_id, insert, replace, select, transaction, update


class Operation(TypedDict):
    aid: str
    amount: float
    cur: str


class Transaction(TypedDict):
    tid: str
    date: datetime
    desc: str
    ops: list[tuple[str, float, str]]
    split: Literal[True]
    dest: str


class Transaction2(Transaction):
    amount: float
    src: str
    cur: str
    split: Literal[False]  # type: ignore[misc]


class AccountB(TypedDict):
    type: str
    name: str
    desc: Optional[str]
    parent: Optional[str]
    is_placeholder: bool


class Account(AccountB):
    aid: str


class AccountExt(Account):
    parents: tuple[str, ...]
    is_sheet: bool
    children: list[str]
    full_name: str


TransactionAny = Union[Transaction, Transaction2]
BState = dict[str, float]
Balance = dict[str, BState]


class AccountMap(dict[str, AccountExt]):
    top: list[str]


class AccType:
    INCOME = 'i'
    EXPENSE = 'e'
    EQUITY = 'q'
    ASSET = 'a'
    LIABILITY = 'l'


acc_types = [(v, k.capitalize()) for k, v in vars(AccType).items() if not k.startswith('_')]
sheet_accounts = {AccType.EQUITY, AccType.ASSET, AccType.LIABILITY}


@transaction()
def create_account(
    parent: Optional[str],
    name: str,
    type: str,
    desc: Optional[str] = None,
    aid: Optional[str] = None,
    is_placeholder: bool = False,
) -> str:
    aid = aid or gen_id()
    insert('accounts', aid=aid, parent=parent, name=name, type=type, desc=desc, is_placeholder=is_placeholder)
    return aid


@transaction()
def update_account(
    aid: str, parent: Optional[str], name: str, type: str, desc: Optional[str], is_placeholder: bool
) -> None:
    update('accounts', 'aid', aid=aid, parent=parent, name=name, type=type, desc=desc, is_placeholder=is_placeholder)


@transaction()
def create_transaction(ops: Iterable[Operation], date: Optional[datetime] = None, desc: Optional[str] = None) -> str:
    tid = gen_id()
    ts = int((date or datetime.now()).timestamp())
    insert('transactions', tid=tid, date=ts, desc=desc)
    for op in ops:
        insert('ops', tid=tid, aid=op['aid'], amount=round(op['amount'] * 100), cur=op['cur'])
    return tid


@transaction()
def update_transaction(tid: str, ops: Iterable[Operation], date: datetime, desc: Optional[str]) -> None:
    update('transactions', 'tid', tid=tid, date=int(date.timestamp()), desc=desc)
    delete('ops', tid=tid)
    for op in ops:
        insert('ops', tid=tid, aid=op['aid'], amount=round(op['amount'] * 100), cur=op['cur'])


@transaction()
def delete_transaction(tid: str) -> None:
    delete('ops', tid=tid)
    delete('transactions', tid=tid)


def account_transactions(**eq: Any) -> QueryList[TransactionAny]:
    q = Q()
    result: QueryList[TransactionAny]

    result = q.execute_d(
        f'''\
        SELECT tid, date, desc, json_array(json_group_array(aid),
                                           json_group_array(amount/100.0),
                                           json_group_array(cur)) ops_raw
        FROM (SELECT distinct(tid) FROM ops {q.WHERE(**eq)})
        INNER JOIN transactions t USING(tid)
        INNER JOIN ops USING(tid)
        GROUP BY tid
        ORDER BY date DESC
    '''
    )  # type: ignore[assignment]

    aid = eq.pop('aid', None)
    by_amount = operator.itemgetter(1)

    for it in result:
        it['date'] = datetime.fromtimestamp(it['date'])  # type: ignore[arg-type]
        accs: list[str]
        amounts: list[float]
        curs: list[str]
        accs, amounts, curs = json.loads(it.pop('ops_raw'))  # type: ignore[typeddict-item]
        it['ops'] = sorted(zip(accs, amounts, curs), key=by_amount)
        it['split'] = len(accs) != 2 or len(set(curs)) > 1  # type: ignore[arg-type]
        it['dest'] = aid
        if not it['split']:
            it['amount'] = sum(a for op_aid, a, cur in it['ops'] if aid == op_aid)
            it['src'] = next(a for a in accs if a != aid)
            it['cur'] = curs[0]

    return result


@transaction()
def delete_account(aid: str, new_parent: Optional[str]) -> None:
    assert aid
    update('accounts', 'parent', aid, parent=new_parent)
    update('ops', 'aid', aid, aid=new_parent)
    delete('accounts', aid=aid)


def account_by_name(parent: str, name: str) -> Optional[Account]:
    return select('accounts', '*', parent=parent, name=name).first()  # type: ignore[return-value]


def account_by_id(aid: str) -> Optional[Account]:
    return select('accounts', '*', aid=aid).first()  # type: ignore[return-value]


def get_sub_accounts(parent: Optional[str]) -> QueryList[Account]:
    return select('accounts', '*', parent=parent)  # type: ignore[return-value]


@overload
def get_param(name: str) -> Optional[str]: ...


@overload
def get_param(name: str, default: str) -> str: ...


def get_param(name: str, default: Optional[str] = None) -> Optional[str]:
    q = Q()
    return q.execute(f'SELECT value FROM params WHERE name = {q/name}').scalar(default)  # type: ignore[no-any-return]


@transaction()
def set_param(name: str, value: str) -> None:
    replace('params', name=name, value=value)


def account_parents(aid: Optional[str], amap: AccountMap, cache: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if aid is None:
        return ()

    if aid in cache:
        return cache[aid]

    cur = amap[aid]
    result = cache[aid] = account_parents(cur['parent'], amap, cache) + (aid,)
    return result


def account_list() -> AccountMap:
    all_accounts: QueryList[AccountExt] = Q().execute_d('SELECT * FROM accounts')  # type: ignore[assignment]
    amap = AccountMap({it['aid']: it for it in all_accounts})
    amap[None] = {}  # type: ignore[typeddict-item,index]

    cache: dict[str, tuple[str, ...]] = {}
    for it in amap.values():
        if not it.get('aid'):
            continue
        it['is_sheet'] = it['type'] in sheet_accounts
        it['parents'] = account_parents(it['parent'], amap, cache)
        it.setdefault('children', [])
        amap[it['parent']].setdefault('children', []).append(it['aid'])  # type: ignore[index]

    amap.top = amap.pop(None)['children']  # type: ignore[call-overload]
    for it in amap.values():
        if not it.get('aid'):
            continue
        it['full_name'] = ':'.join([amap[p]['name'] for p in it['parents']] + [it['name']])
    return amap


def op(aid: str, amount: float, currency: str) -> Operation:
    return {'aid': aid, 'amount': amount, 'cur': currency}


def op2(a1: str, a2: str, amount: float, currency: str) -> tuple[Operation, Operation]:
    return op(a1, -amount, currency), op(a2, amount, currency)


def balance(start: Optional[float] = None, end: Optional[float] = None) -> Balance:
    q = Q()
    data = q.execute_d(
        f'''\
        SELECT aid, cur, sum(amount) / 100.0 AS total
        FROM transactions AS t
        INNER JOIN ops t USING (tid)
        {q.WHERE(q.in_range(q.t.date, not_none/start, not_none/end))}
        GROUP BY aid, cur
    '''
    )

    result: Balance = {}
    for it in data:
        result.setdefault(it['aid'], {})[it['cur']] = it['total']

    return result


def combine_balances(*balances: Balance) -> Balance:  # pragma: no cover
    result: Balance = {}
    for b in balances:
        for acc, state in b.items():
            rstate = result.setdefault(acc, {})
            for cur, amount in state.items():
                rstate[cur] = rstate.get(cur, 0) + amount

    return result


def combine_states(*states: BState) -> BState:  # pragma: no cover
    rstate: BState = {}
    for state in states:
        for cur, amount in state.items():
            rstate[cur] = rstate.get(cur, 0) + amount
    return rstate


@transaction()
def create_tables() -> None:
    # Initial tables
    execute(
        '''\
        CREATE TABLE IF NOT EXISTS accounts (
            aid TEXT NOT NULL PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            desc TEXT,
            parent TEXT,
            is_placeholder INTEGER NOT NULL DEFAULT 0
        )
    '''
    )

    execute(
        '''\
        CREATE TABLE IF NOT EXISTS transactions (
            tid TEXT NOT NULL PRIMARY KEY,
            date INTEGER NOT NULL,
            desc TEXT
        )
    '''
    )

    execute(
        '''\
        CREATE TABLE IF NOT EXISTS ops (
            tid TEXT NOT NULL,
            aid TEXT NOT NULL,
            amount INTEGER NOT NULL,
            cur TEXT NOT NULL
        )
    '''
    )

    execute(
        '''\
        CREATE TABLE IF NOT EXISTS params (
            name TEXT NOT NULL PRIMARY KEY,
            value TEXT
        )
    '''
    )

    # Indexes
    execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_uniq_name ON accounts (parent, name)')
    execute('CREATE INDEX IF NOT EXISTS idx_ops_tid ON ops (tid)')
    execute('CREATE INDEX IF NOT EXISTS idx_ops_aid ON ops (aid)')
    execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date, tid)')


def create_initial_accounts() -> None:
    if Q().execute('SELECT count(1) from accounts').scalar(0) > 0:
        return

    initial_accounts = [
        (AccType.INCOME, 'Income'),
        (AccType.EXPENSE, 'Expenses'),
        (AccType.ASSET, 'Assets'),
        (AccType.LIABILITY, 'Liabilities'),
        (AccType.EQUITY, 'Equity'),
    ]
    for aid, name in initial_accounts:
        q = Q()
        q.execute(f'INSERT OR IGNORE INTO accounts {q.VALUES(aid=aid, type=aid, name=name)}')


@transaction()
def drop_tables() -> None:
    execute('DROP TABLE IF EXISTS accounts')
    execute('DROP TABLE IF EXISTS transactions')
    execute('DROP TABLE IF EXISTS ops')
    execute('DROP TABLE IF EXISTS params')
