import logging
from functools import wraps
from datetime import datetime, time as dt_time, timedelta


def pick_keys(d, *keys):
    return {k: d[k] for k in keys}


def cached(fn):
    cache = {}

    @wraps(fn)
    def inner(*args):
        try:
            return cache[args]
        except KeyError:
            pass

        result = cache[args] = fn(*args)
        return result

    def invalidate(*args):
        cache.pop(args, None)

    inner.invalidate = invalidate
    inner.clear = cache.clear
    return inner


def month_start(dt):
    return datetime.combine(dt.replace(day=1), dt_time())


def next_month_start(dt):
    dy, m = divmod(dt.month, 12)
    return datetime.combine(dt.replace(year=dt.year+dy, month=m+1, day=1), dt_time())


def day_range(dt):
    t = dt_time()
    return datetime.combine(dt, t), datetime.combine(dt + timedelta(days=1), t)


def scream(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except:
            logging.exception('Scream')
            raise

    return inner
