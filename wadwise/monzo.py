import csv
from collections.abc import Collection
from datetime import datetime
from typing import IO, Literal, TypedDict

from .model import Operation, account_by_id, create_transaction, decode_account_id, dop2

FMT = '%d/%m/%Y:%H:%M:%S'

State = Literal['imported'] | Literal['seen']


class TransactionData(TypedDict):
    date: datetime
    type: str
    cur: str
    key: str
    amount: float
    category: str
    name: str
    state: State | None


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
                'state': None,
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
    state: State | None
    txkey: str


def import_data(src: str, data: list[ImportTransaction]) -> None:
    transactions: list[tuple[Collection[Operation], datetime, str | None]] = []
    for it in data:
        dt = datetime.fromtimestamp(it['date'])
        dest = it['dest']
        amount = it['amount']
        cur = it['cur']
        ops = dop2(src, dest, -amount, cur)
        ddest = decode_account_id(dest)[0]
        _account = account_by_id(ddest)
        assert _account, f'{ddest} not found'
        transactions.append((ops, dt, it.get('desc') or it['name'] or None))

    for tran in transactions:
        create_transaction(*tran)
