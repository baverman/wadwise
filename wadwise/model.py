import json
import operator
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Optional, TypedDict, Union, overload

from sqlbind_t import VALUES, WHERE, E, in_range, not_none, sqlf, text

from wadwise.db import (
    QueryList,
    delete,
    execute,
    execute_d,
    execute_raw,
    gen_id,
    get_version,
    insert,
    replace,
    select,
    set_version,
    transaction,
    update,
)


class Operation(TypedDict):
    aid: str
    amount: float
    cur: str


class TransactionRaw(TypedDict):
    tid: str
    date: int
    desc: str
    ops: str


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
    is_hidden: bool | None


class Account(AccountB):
    aid: str


class AccountExt(Account):
    parents: tuple[str, ...]
    is_sheet: bool
    children: list[str]
    full_name: str


@dataclass(frozen=True)
class Amount2:
    credit: float = 0
    debit: float = 0

    @property
    def sum(self) -> float:
        return self.credit + self.debit

    def combine(self, other: Optional['Amount2'] = None) -> 'Amount2':
        if other:
            return Amount2(self.credit + other.credit, self.debit + other.debit)
        return self


TransactionAny = Union[Transaction, Transaction2]
BState = dict[str, float]
BState2 = dict[str, Amount2]
Balance = dict[str, BState2]


class AccountMap(dict[str, AccountExt]):
    top: list[str]


class AccType:
    INCOME = 'i'
    EXPENSE = 'e'
    EQUITY = 'q'
    ASSET = 'a'
    LIABILITY = 'l'


class JointAccount(TypedDict):
    parent: str
    clear: str
    joints: list[str]
    assets: list[str]


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
    is_hidden: bool | None = None,
) -> str:
    aid = aid or gen_id()
    insert(
        'accounts',
        aid=aid,
        parent=parent,
        name=name,
        type=type,
        desc=desc,
        is_placeholder=is_placeholder,
        is_hidden=is_hidden,
    )
    return aid


@transaction()
def update_account(
    aid: str,
    parent: Optional[str],
    name: str,
    type: str,
    desc: Optional[str],
    is_placeholder: bool,
    is_hidden: bool | None,
) -> None:
    update(
        'accounts',
        'aid',
        aid=aid,
        parent=parent,
        name=name,
        type=type,
        desc=desc,
        is_placeholder=is_placeholder,
        is_hidden=is_hidden,
    )


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


def account_transactions(
    *, start_date: datetime | None = None, end_date: datetime | None = None, aids: list[str] | None = None, **eq: object
) -> list[TransactionAny]:
    cond = [in_range(E.t.date, start_date and start_date.timestamp(), end_date and end_date.timestamp())]
    query = f"""@\
        SELECT tid, date, desc,
               json_group_array(json_array(aid, amount/100.0, cur)) as ops
        FROM (SELECT distinct(tid) FROM ops {WHERE(E.aid.IN(not_none / aids), **eq)})
        INNER JOIN transactions t USING(tid)
        INNER JOIN ops USING(tid)
        {WHERE(*cond)}
        GROUP BY tid
        ORDER BY date DESC
    """
    data: QueryList[TransactionRaw] = execute_d(sqlf(query))  # type: ignore[assignment]

    aid: str = eq.pop('aid', None)  # type: ignore[assignment]
    by_amount = operator.itemgetter(1)

    result: list[TransactionAny] = []
    for it in data:
        ops: list[tuple[str, float, str]] = [tuple(op) for op in json.loads(it['ops'])]
        curs = set(o[2] for o in ops)
        tr: TransactionAny = {
            'tid': it['tid'],
            'date': datetime.fromtimestamp(it['date']),
            'ops': sorted(ops, key=by_amount),
            'split': len(ops) != 2 or len(curs) > 1,  # type: ignore[typeddict-item]
            'dest': aid,
            'desc': it['desc'],
        }

        if not tr['split']:
            tr['amount'] = sum(a for op_aid, a, _cur in tr['ops'] if aid == op_aid)
            tr['src'] = next(op_aid for op_aid, _a, _cur in tr['ops'] if op_aid != aid)
            tr['cur'] = list(curs)[0]

        result.append(tr)

    return result


@transaction()
def delete_account(aid: str, new_parent: Optional[str]) -> None:
    assert aid
    update('accounts', 'parent', aid, parent=new_parent)
    update('ops', 'aid', aid, aid=new_parent)
    delete('accounts', aid=aid)


def account_by_name(name: str) -> Optional[Account]:
    parent: Optional[Account] = None
    parts = name.split(':')
    for p in parts:
        parent = select('accounts', '*', parent=parent and parent['aid'], name=p).first()  # type: ignore[assignment]
        if not parent:
            return None
    return parent


def account_by_id(aid: str) -> Optional[Account]:
    return select('accounts', '*', aid=aid).first()  # type: ignore[return-value]


def get_sub_accounts(parent: Optional[str]) -> QueryList[Account]:
    return select('accounts', '*', parent=parent)  # type: ignore[return-value]


@overload
def get_param(name: str) -> Optional[str]: ...


@overload
def get_param(name: str, default: str) -> str: ...


def get_param(name: str, default: Optional[str] = None) -> Optional[str]:
    return execute(sqlf(f'@SELECT value FROM params WHERE name = {name}')).scalar(default)  # type: ignore[no-any-return]


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
    all_accounts: QueryList[AccountExt] = execute_d(text('SELECT * FROM accounts'))  # type: ignore[assignment]
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


def dop2(a1: str, a2: str, amount: float, currency: str) -> Collection[Operation]:
    ops = Joint.try_ops(a1, a2, amount, currency)
    if ops is not None:
        return ops
    return op2(a1, a2, amount, currency)


def balance(start: Optional[float] = None, end: Optional[float] = None) -> Balance:
    query = f"""@\
        SELECT aid, cur,
            total(amount) FILTER (WHERE amount < 0) / 100.0 AS credit,
            total(amount) FILTER (WHERE amount >= 0) / 100.0 AS debit
        FROM transactions AS t
        INNER JOIN ops t USING (tid)
        {WHERE(in_range(E.t.date, start, end))}
        GROUP BY aid, cur
    """
    data = execute_d(sqlf(query))

    result: Balance = {}
    for it in data:
        result.setdefault(it['aid'], {})[it['cur']] = Amount2(it['credit'], it['debit'])

    return result


def combine_balances(*balances: Balance) -> Balance:  # pragma: no cover
    result: Balance = {}
    for b in balances:
        for acc, state in b.items():
            rstate = result.setdefault(acc, {})
            for cur, amount in state.items():
                rstate[cur] = amount.combine(rstate.get(cur))

    return result


def combine_states(*states: BState2) -> BState2:  # pragma: no cover
    rstate: BState2 = {}
    for state in states:
        for cur, amount in state.items():
            rstate[cur] = amount.combine(rstate.get(cur))
    return rstate


class Joint:
    type = 'joint'

    def __init__(self, account: JointAccount):
        self.parent_joint = account['parent']
        self.my_joint = account['joints'][0]
        self.partner_joint = account['joints'][1]
        self.partner_acc = account['assets'][0]
        self.clear = account['clear']

    @staticmethod
    def try_ops(src: str, dest: str, amount: float, cur: str) -> list[Operation] | None:
        suffix = f'.{Joint.type}'
        applicable = False
        main = ''
        if src.endswith(suffix):
            main = src = src[: -len(suffix)]
            applicable = True
        elif dest.endswith(suffix):
            main = dest = dest[: -len(suffix)]
            applicable = True

        if applicable:
            joints = get_joint_accounts()
            return Joint(joints[main]).ops(src, dest, amount, cur)
        return None

    def ops(self, src: str, dest: str, amount: float, cur: str) -> list[Operation]:
        if amount < 0:
            amount = -amount
            src, dest = dest, src

        if dest == self.parent_joint:
            if src == self.partner_acc:
                return [
                    op(self.partner_joint, amount, cur),
                    op(src, -amount / 2, cur),
                    op(self.clear, -amount / 2, cur),
                ]
            else:
                return [
                    *op2(src, self.my_joint, amount, cur),
                    *op2(self.clear, self.partner_acc, amount / 2, cur),
                ]
        elif src == self.parent_joint:
            return [
                op(self.my_joint, -amount / 2, cur),
                op(self.partner_joint, -amount / 2, cur),
                op(dest, amount / 2, cur),
                op(self.clear, amount / 2, cur),
            ]

        raise RuntimeError(f'Invalid src/dest account: {src}/{dest}')

    def transaction(
        self, src: str, dest: str, amount: float, cur: str, date: datetime | None = None, desc: str | None = None
    ) -> str:
        ops = self.ops(src, dest, amount, cur)
        return create_transaction(ops, date, desc)


def get_joint_accounts() -> dict[str, JointAccount]:
    accs: list[JointAccount] = json.loads(get_param('accounts.joint') or '[]') or []
    return {it['parent']: it for it in accs}


def set_joint_accounts(joint_accounts: list[object]) -> None:
    set_param('accounts.joint', json.dumps(joint_accounts))


def decode_account_id(aid: str) -> tuple[str, str]:
    aid, _, typ = aid.partition('.')
    return aid, typ


def seen_transactions(aid: str, start: datetime | None = None, end: datetime | None = None) -> set[str]:
    q = f"""@\
        SELECT key
        FROM seen_transactions
        {WHERE(in_range(E.date, start and start.timestamp(), end and end.timestamp()), aid=aid)}
    """
    return set(execute(sqlf(q)).column())


def seen_tx_key(dt: datetime, amount: float, currency: str) -> str:
    return f'{int(dt.timestamp())}-{amount:.2f}-{currency}'


@transaction()
def update_seen_transactions(aid: str, date: datetime, keys: Iterable[str]) -> None:
    existing = seen_transactions(aid)
    new = set(keys) - existing
    for key in new:
        insert('seen_transactions', aid=aid, date=date.timestamp(), key=key)


@transaction()
def create_tables() -> None:
    # Initial tables
    if get_version() < 1:
        execute_raw(
            """\
                CREATE TABLE IF NOT EXISTS accounts (
                    aid TEXT NOT NULL PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    desc TEXT,
                    parent TEXT,
                    is_placeholder INTEGER NOT NULL DEFAULT 0
                )
            """
        )

        execute_raw(
            """\
                CREATE TABLE IF NOT EXISTS transactions (
                    tid TEXT NOT NULL PRIMARY KEY,
                    date INTEGER NOT NULL,
                    desc TEXT
                )
            """
        )

        execute_raw(
            """\
                CREATE TABLE IF NOT EXISTS ops (
                    tid TEXT NOT NULL,
                    aid TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    cur TEXT NOT NULL
                )
            """
        )

        execute_raw(
            """\
                CREATE TABLE IF NOT EXISTS params (
                    name TEXT NOT NULL PRIMARY KEY,
                    value TEXT
                )
            """
        )

        # Indexes
        execute_raw('CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_uniq_name ON accounts (parent, name)')
        execute_raw('CREATE INDEX IF NOT EXISTS idx_ops_tid ON ops (tid)')
        execute_raw('CREATE INDEX IF NOT EXISTS idx_ops_aid ON ops (aid)')
        execute_raw('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date, tid)')
        set_version(1)

    if get_version() < 2:
        execute_raw('ALTER TABLE accounts ADD COLUMN is_hidden INTEGER')
        set_version(2)

    if get_version() < 3:
        stmts = """\
            CREATE TABLE seen_transactions (
                aid TEXT NOT NULL,
                key TEXT NOT NULL,
                date INTEGER NOT NULL
            );

            CREATE UNIQUE INDEX idx_seen_transactions_uniq ON seen_transactions (aid, key);
        """
        for q in stmts.split(';\n'):
            execute_raw(q)
        set_version(3)


def create_initial_accounts() -> None:
    if execute(text('SELECT count(1) from accounts')).scalar(0) > 0:
        return

    initial_accounts = [
        (AccType.INCOME, 'Income'),
        (AccType.EXPENSE, 'Expenses'),
        (AccType.ASSET, 'Assets'),
        (AccType.LIABILITY, 'Liabilities'),
        (AccType.EQUITY, 'Equity'),
    ]
    for aid, name in initial_accounts:
        execute(sqlf(f'@INSERT OR IGNORE INTO accounts {VALUES(aid=aid, type=aid, name=name)}'))


@transaction()
def drop_tables() -> None:
    execute_raw('DROP TABLE IF EXISTS accounts')
    execute_raw('DROP TABLE IF EXISTS transactions')
    execute_raw('DROP TABLE IF EXISTS ops')
    execute_raw('DROP TABLE IF EXISTS params')
    execute_raw('DROP TABLE IF EXISTS seen_transactions')
    set_version(0)
