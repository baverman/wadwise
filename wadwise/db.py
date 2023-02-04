import os
import time
import functools
import contextlib
import sqlite3
import base64
import threading

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
    if hasattr(sql, 'unwrap'):
        sql, params = sql.unwrap()
    # print('@@', sql, params)
    return conn.execute(sql, params or ())


def insert(table, **params):
    params = list(params.items())
    columns, values = zip(*params)
    columns_s = ','.join(columns)
    qmark_s = ','.join('?' * len(columns))
    sql = f'INSERT INTO {table} ({columns_s}) VALUES ({qmark_s})'
    return execute(sql, values)


def replace(table, **params):
    params = list(params.items())
    columns, values = zip(*params)
    columns_s = ','.join(columns)
    qmark_s = ','.join('?' * len(columns))
    sql = f'REPLACE INTO {table} ({columns_s}) VALUES ({qmark_s})'
    return execute(sql, values)


def update(table, pk, **params):
    pk_value = params.pop(pk)
    params = list(params.items())
    columns, values = zip(*params)
    values += (pk_value,)
    col_eq_qmark = ','.join(f'{it} = ?' for it in columns)
    sql = f'UPDATE {table} SET {col_eq_qmark} WHERE {pk} = ?'
    return execute(sql, values)


def delete(table, *filters, **eq):
    q = Q(f'DELETE FROM {table}', WHERE(*filters, **eq))
    return execute(q).rowcount


def gen_id():
    value = int(time.time()).to_bytes(4, 'big') + os.urandom(11)
    return base64.urlsafe_b64encode(value).decode()


def sqlite_escape(val):
    tval = type(val)
    if tval is str:
        return "'{}'".format(val.replace("'", "''"))
    elif tval is int or tval is float:
        return str(val)
    elif val is None:
        return 'NULL'
    raise ValueError(f'Invalid type: {val}')


def sqlite_value_list(values):
    return ','.join(map(sqlite_escape, values))


class F:
    def __new__(self, sql, *params):
        return sql, params

    @staticmethod
    def cond(cond, sql, *params):
        if cond:
            return sql, params

    @staticmethod
    def not_none(sql, param):
        if param is not None:
            return sql, (param,)

    @staticmethod
    def is_true(sql, param):
        if param:
            return sql, (param,)

    @staticmethod
    def eq(field, value):
        if value is None:
            return f'{field} is NULL', ()
        else:
            return f'{field} = {{}}', (value,)


def op_fset(sep, fragments, prefix='(', postfix=')'):
    qlist = []
    params = []
    for q, p in filter(None, fragments):
        qlist.append(q)
        params.extend(p)

    if qlist:
        return prefix + sep.join(qlist) + postfix, params


def AND(*fragments):
    return op_fset(' AND ', fragments)


def OR(*fragments):
    return op_fset(' OR ', fragments)


def IN(field, values, escape=False):
    if not values:
        return None
    if escape or len(values) > 50:
        # Trying to escape and assemble sql manually to avoid too many
        # parameters exception
        return f"{field} IN ({sqlite_value_list(values)})", ()
    else:
        qmarks = ','.join(['{}'] * len(values))
        return f'{field} IN ({qmarks})', values


class FSET:
    def unwrap(self):
        if self.fset:
            q = self.prefix + self.fset[0].format(*('?' * len(self.fset[1])))
            return q, self.fset[1]
        return None, []


class WHERE(FSET):
    prefix = 'WHERE '
    def __init__(self, *parts, **eq):
        parts += tuple(F.eq(k, v) for k, v in eq.items())
        self.fset = AND(*parts)


class SET(FSET):
    prefix = 'SET '
    def __init__(self, *fragments, **eq):
        fragments += tuple((f'{field} = {{}}', (value,)) for field, value in eq.items())
        self.fset = op_fset(', ', fragments, '', '')


class Q:
    def __init__(self, *parts):
        self.parts = parts

    def unwrap(self):
        params = []
        unwraped_parts = []

        for it in self.parts:
            if type(it) is str:
                unwraped_parts.append(it)
            else:
                q, p = it.unwrap()
                params.extend(p)
                q and unwraped_parts.append(q)

        return ' '.join(unwraped_parts), params

    def one(self):
        return execute(self).fetchone()

    def all(self):
        return execute(self).fetchall()

    def scalar(self, default=None):
        result = execute(self).fetchone()
        if result:
            return result[list(result.keys())[0]]
        else:  # pragma: no cover
            return default

    def __iter__(self):
        return execute(self)
