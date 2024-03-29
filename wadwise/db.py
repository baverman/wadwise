import os
import time
import functools
import contextlib
import sqlite3
import base64
import threading
import sqlbind

DB = 'data.sqlite'


@contextlib.contextmanager
def transaction():
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
def _get_connection(tid):
    conn = sqlite3.connect(DB)
    conn.isolation_level = None
    conn.execute('pragma journal_mode=wal')
    conn.execute('pragma cache_size=-100000')
    conn.execute('pragma busy_timeout=10000')
    return conn


def get_connection():
    return _get_connection(threading.get_ident())


def execute(sql, params=None):
    conn = get_connection()
    return conn.execute(sql, params or ())


def insert(table, **params):
    q = Q()
    return q.execute(f'INSERT INTO {table} {q.VALUES(**params)}')


def replace(table, **params):
    q = Q()
    return q.execute(f'REPLACE INTO {table} {q.VALUES(**params)}')


def update(table, pk, pk_value=None, **params):
    if pk_value is None:
        pk_value = params.pop(pk)
    q = Q()
    return q.execute(f'UPDATE {table} {q.SET(**params)} WHERE {pk} = {q/pk_value}')


def delete(table, **eq):
    q = Q()
    return q.execute(f'DELETE FROM {table} {q.WHERE(**eq)}')


def select(table, fields, **eq):
    q = Q()
    return q.execute(f'SELECT {fields} FROM {table} {q.WHERE(**eq)}', as_dict=True)


def gen_id():
    value = int(time.time()).to_bytes(4, 'big') + os.urandom(11)
    return base64.urlsafe_b64encode(value).decode()


class QueryList(list):
    rowcount: int

    def first(self):
        if self:
            return self[0]
        return None

    def scalar(self, default=None):
        v = self.first()
        if v is not None:
            return v[0]
        return default

    def column(self, n: int = 0):
        return [it[n] for it in self]


class Q(sqlbind.NamedQueryParams):
    def __init__(self):
        sqlbind.NamedQueryParams.__init__(self, sqlbind.SQLiteDialect)

    def execute(self, query: str, as_dict: bool = False):
        cur = execute(query, self)
        data = cur.fetchall()
        if as_dict:
            fields = [it[0] for it in cur.description]
            data = (dict(zip(fields, row)) for row in data)

        result = QueryList(data)
        result.rowcount = cur.rowcount
        return result

    def execute_d(self, query: str):
        return self.execute(query, True)
