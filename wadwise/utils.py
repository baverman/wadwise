import logging
from datetime import date as dt_date
from datetime import datetime, timedelta
from datetime import time as dt_time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar

K = TypeVar('K')
V = TypeVar('V')
R = TypeVar('R', covariant=True)

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeVarTuple, Unpack

    P = ParamSpec('P')
    Ts = TypeVarTuple('Ts')
else:
    Unpack, P, Ts, ParamSpec, TypeVarTuple = [list] * 5


def pick_keys(d: Mapping[K, V], *keys: K) -> dict[K, V]:
    return {k: d[k] for k in keys}


def cached(fn: Callable[[Unpack[Ts]], R]) -> Callable[[Unpack[Ts]], R]:
    cache: dict[Any, R] = {}

    @wraps(fn)
    def inner(*args: Unpack[Ts]) -> R:
        try:
            return cache[args]
        except KeyError:
            pass

        result = cache[args] = fn(*args)
        return result

    def invalidate(*args: Unpack[Ts]) -> None:
        cache.pop(args, None)

    inner.invalidate = invalidate  # type: ignore[attr-defined]
    inner.clear = cache.clear  # type: ignore[attr-defined]
    return inner


def month_start(dt: dt_date) -> datetime:
    return datetime.combine(dt.replace(day=1), dt_time())


def next_month_start(dt: dt_date) -> datetime:
    dy, m = divmod(dt.month, 12)
    return datetime.combine(dt.replace(year=dt.year + dy, month=m + 1, day=1), dt_time())


def day_range(dt: dt_date) -> tuple[datetime, datetime]:
    t = dt_time()
    return datetime.combine(dt, t), datetime.combine(dt + timedelta(days=1), t)


def scream(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except:  # noqa: E722
            logging.exception('Scream')
            raise

    return inner


def fmt_date(dt: dt_date) -> str:
    return dt.strftime('%Y-%m-%d')
