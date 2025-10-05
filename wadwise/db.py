import base64
import contextlib
import functools
import os
import sqlite3
import threading
import time
from typing import Any, Iterator, Literal, Optional, TypeVar, Union, cast, overload

from sqlbind_t import SET, VALUES, WHERE, AnySQL, sqlf, text
from sqlbind_t.dialect import unwrap
from sqlbind_t.sqlite import Dialect

_used = SET, VALUES, WHERE, text

T = TypeVar('T')
TupleResult = tuple[Any, ...]
DictResult = dict[str, Any]

DB = 'data.sqlite'
dialect = Dialect()


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


def execute_raw(sql: str, params: Optional[Union[dict[str, Any], list[Any]]] = None) -> sqlite3.Cursor:
    conn = get_connection()
    return conn.execute(sql, params or ())


def insert(table: str, **params: Any) -> 'QueryList[TupleResult]':
    return execute(sqlf(f'@INSERT INTO {text(table)} {VALUES(**params)}'))


def replace(table: str, **params: Any) -> 'QueryList[TupleResult]':
    return execute(sqlf(f'@REPLACE INTO {text(table)} {VALUES(**params)}'))


def update(table: str, pk: str, pk_value: Optional[Any] = None, **params: Any) -> 'QueryList[TupleResult]':
    if pk_value is None:
        pk_value = params.pop(pk)
    return execute(sqlf(f'@UPDATE {text(table)} {SET(**params)} WHERE {text(pk)} = {pk_value}'))


def delete(table: str, **eq: Any) -> 'QueryList[TupleResult]':
    return execute(sqlf(f'@DELETE FROM {text(table)} {WHERE(**eq)}'))


def select(table: str, fields: str, **eq: Any) -> 'QueryList[DictResult]':
    return execute_d(sqlf(f'@SELECT {text(fields)} FROM {text(table)} {WHERE(**eq)}'))


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


@overload
def execute(query: AnySQL) -> QueryList[TupleResult]: ...


@overload
def execute(query: AnySQL, as_dict: Literal[True]) -> QueryList[DictResult]: ...


def execute(query: AnySQL, as_dict: bool = False) -> Union[QueryList[TupleResult], QueryList[DictResult]]:
    qstr, params = unwrap(query, dialect=dialect)
    cur = execute_raw(qstr, params)
    data = cur.fetchall()
    if as_dict:
        fields = [it[0] for it in cur.description]
        data = (dict(zip(fields, row)) for row in data)  # type: ignore[assignment]

    result = QueryList(data)
    result.rowcount = cur.rowcount
    return result


def execute_d(query: AnySQL) -> QueryList[DictResult]:
    r = execute(query, True)
    return r


def backup() -> str:
    src = get_connection()
    fname = os.path.join(os.path.dirname(DB), 'wadwise-backup.sqlite')
    dst = _get_connection.__wrapped__(None, fname)
    with dst:
        src.backup(dst)
    dst.close()
    return fname
