import base64
import contextlib
import functools
import os
import sqlite3
import threading
import time
from typing import Any, Iterator, Literal, Optional, TypeVar, Union, cast, overload

import sqlbind

T = TypeVar('T')
TupleResult = tuple[Any, ...]
DictResult = dict[str, Any]

DB = 'data.sqlite'


@contextlib.contextmanager
def transaction() -> Iterator[None]:
    conn = get_connection()
    if conn.in_transaction:  # pragma: no cover
        yield
        return

    conn.execute('BEGIN IMMEDIATE')
    try:
        yield
        conn.commit()
    except Exception:  # pragma: no cover
        conn.rollback()
        raise


@functools.lru_cache(None)
def _get_connection(tid: int, db: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db or DB)
    conn.isolation_level = None
    conn.execute('pragma journal_mode=wal')
    conn.execute('pragma cache_size=-100000')
    conn.execute('pragma busy_timeout=10000')
    return conn


def get_connection(db: Optional[str] = None) -> sqlite3.Connection:
    return _get_connection(threading.get_ident(), db)


def execute(sql: str, params: Optional[dict[str, Any]] = None) -> sqlite3.Cursor:
    conn = get_connection()
    return conn.execute(sql, params or ())


def insert(table: str, **params: Any) -> 'QueryList[TupleResult]':
    q = Q()
    return q.execute(f'INSERT INTO {table} {q.VALUES(**params)}')


def replace(table: str, **params: Any) -> 'QueryList[TupleResult]':
    q = Q()
    return q.execute(f'REPLACE INTO {table} {q.VALUES(**params)}')


def update(table: str, pk: str, pk_value: Optional[Any] = None, **params: Any) -> 'QueryList[TupleResult]':
    if pk_value is None:
        pk_value = params.pop(pk)
    q = Q()
    return q.execute(f'UPDATE {table} {q.SET(**params)} WHERE {pk} = {q/pk_value}')


def delete(table: str, **eq: Any) -> 'QueryList[TupleResult]':
    q = Q()
    return q.execute(f'DELETE FROM {table} {q.WHERE(**eq)}')


def select(table: str, fields: str, **eq: Any) -> 'QueryList[DictResult]':
    q = Q()
    return q.execute_d(f'SELECT {fields} FROM {table} {q.WHERE(**eq)}')


def gen_id() -> str:
    value = int(time.time()).to_bytes(4, 'big') + os.urandom(11)
    return base64.urlsafe_b64encode(value).decode()


class QueryList(list[T]):
    rowcount: int

    def first(self) -> Optional[T]:
        if self:
            return self[0]
        return None

    def scalar(self, default: Optional[Any] = None) -> Any:
        v: TupleResult = self.first()  # type: ignore[assignment]
        if v is not None:
            return v[0]
        return default

    def column(self, n: int = 0) -> list[Any]:
        return [it[n] for it in cast(TupleResult, self)]


class Q(sqlbind.NamedQueryParams):
    def __init__(self) -> None:
        sqlbind.NamedQueryParams.__init__(self, sqlbind.SQLiteDialect)

    @overload
    def execute(self, query: str) -> QueryList[TupleResult]: ...

    @overload
    def execute(self, query: str, as_dict: Literal[True]) -> QueryList[DictResult]: ...

    def execute(self, query: str, as_dict: bool = False) -> Union[QueryList[TupleResult], QueryList[DictResult]]:
        cur = execute(query, self)
        data = cur.fetchall()
        if as_dict:
            fields = [it[0] for it in cur.description]
            data = (dict(zip(fields, row)) for row in data)  # type: ignore[assignment]

        result = QueryList(data)
        result.rowcount = cur.rowcount
        return result

    def execute_d(self, query: str) -> QueryList[DictResult]:
        r = self.execute(query, True)
        return r


def backup() -> str:
    src = get_connection()
    fname = os.path.join(os.path.dirname(DB), 'wadwise-backup.sqlite')
    dst = _get_connection.__wrapped__(None, fname)
    with dst:
        src.backup(dst)
    dst.close()
    return fname
