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
    print('connecting to', DB)
    conn = sqlite3.connect(DB)
    conn.row_factory = dict_factory
    conn.isolation_level = None
    conn.execute('pragma journal_mode=wal')
    conn.execute('pragma cache_size=-100000')
    conn.execute('pragma busy_timeout=10000')
    return conn


def get_connection():
    return _get_connection(threading.get_ident())


def dict_factory(cursor, row):
    return dict(zip((it[0] for it in cursor.description), row))


def execute(sql, params=None):
    conn = get_connection()
    return conn.execute(sql, params or ())


def insert(table, **params):
    return Q(q := Q.p, f'INSERT INTO {table} {q.VALUES(**params)}').execute()


def replace(table, **params):
    return Q(q := Q.p, f'REPLACE INTO {table} {q.VALUES(**params)}').execute()


def update(table, pk, pk_value=None, **params):
    if pk_value is None:
        pk_value = params.pop(pk)
    return Q(q := Q.p, f'UPDATE {table} {q.SET(**params)} WHERE {pk} = {q/pk_value}').execute()


def delete(table, **eq):
    return Q(q := Q.p, f'DELETE FROM {table} {q.WHERE(**eq)}').execute().rowcount


def select(table, fields, **eq):
    return Q(q := Q.p, f'SELECT {fields} FROM {table} {q.WHERE(**eq)}')


def gen_id():
    value = int(time.time()).to_bytes(4, 'big') + os.urandom(11)
    return base64.urlsafe_b64encode(value).decode()


class QParamDesc:
    def __get__(self, instance, owner):
        return sqlbind.Dialect.sqlite_named()


class Q:
    p = QParamDesc()

    def __init__(self, q, query):
        self.q = q
        self.query = query

    def one(self):
        return self.execute().fetchone()

    def all(self):
        return self.execute().fetchall()

    def scalar(self, default=None):
        result = self.one()
        if result:
            return result[list(result.keys())[0]]
        else:  # pragma: no cover
            return default

    def execute(self):
        return execute(self.query, self.q)

    def __iter__(self):
        return self.execute()
