import csv
import functools
from datetime import datetime
from typing import IO, TypedDict

from .model import Account, Operation, account_by_id, account_by_name, create_transaction, op, op2


@functools.lru_cache(None)
def get_acc(name: str) -> Account:
    acc = account_by_name(name)
    assert acc, name
    return acc


FMT = '%d/%m/%Y:%H:%M:%S'


def action_joint_me(src: str, amount: float, cur: str) -> tuple[list[Operation], str]:
    ira = get_acc('Assets:Ira')['aid']
    joint = get_acc('Expenses:Joint')['aid']
    return (
        [op(src, amount, cur), op(ira, -amount / 2, cur), op(joint, -amount / 2, 'GBP')],
        f'Joint deposit {-amount}',
    )


# def action_joint_partner(src, amount):
#     assert False
#     ira = get_acc('Assets:Ira')['aid']
#     joint = get_acc('Expenses:Joint')['aid']
#     return (
#         [op(src, amount, 'GBP'), op(ira, -amount / 2, 'GBP'), op(joint, -amount / 2, 'GBP')],
#         f'Joint deposit {-amount}',
#     )


class TransactionData(TypedDict):
    date: datetime
    type: str
    cur: str
    key: str
    amount: float
    category: str
    name: str
    ignore: bool


def prepare(data_stream: IO[str]) -> list[TransactionData]:
    data = csv.DictReader(data_stream)
    result: list[TransactionData] = []
    for row in data:
        amount = float(row['Amount'])
        dt = datetime.strptime(row['Date'].strip() + ':' + row['Time'].strip(), FMT)
        key = row['Type'].strip() + ':' + row['Name'].strip()
        result.append(
            {
                'date': dt,
                'type': row['Type'].strip(),
                'cur': 'GBP',
                'key': key,
                'amount': amount,
                'category': row['Category'].strip(),
                'name': row['Name'].strip(),
                'ignore': False,
            }
        )
    return result


class ImportTransaction(TypedDict):
    date: float
    amount: float
    cur: str
    dest: str
    name: str | None
    desc: str | None


def import_data(src: str, data: list[ImportTransaction]) -> None:
    transactions: list[tuple[list[Operation], datetime, str | None]] = []
    for it in data:
        dt = datetime.fromtimestamp(it['date'])
        dest = it['dest']
        amount = it['amount']
        cur = it['cur']
        if dest == 'joint-me':
            ops, desc = action_joint_me(src, amount, cur)
            transactions.append((ops, dt, desc))
        else:
            _account = account_by_id(dest)
            assert _account, f'{dest} not found'
            transactions.append((list(op2(src, dest, -amount, cur)), dt, it.get('desc') or it['name'] or None))

    for tran in transactions:
        create_transaction(*tran)
