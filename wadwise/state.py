import json
from collections import namedtuple
from datetime import date, datetime
from functools import cached_property
from typing import Optional
from operator import itemgetter

from wadwise import model as m
from wadwise import utils

Option = namedtuple('Option', 'value title hidden')
Option2 = namedtuple('Option2', 'value title')


class Env:
    acc_types = [Option2(*it) for it in m.acc_types]
    cur_sort_key = lambda r, d={'RUB': 'zzzzz'}: d.get(r[0], r[0])
    cur_sort_key1 = lambda r, d={'RUB': 'zzzzz'}: d.get(r, r)

    def __init__(self, today: Optional[date] = None) -> None:
        self.today = today or date.today()

    @cached_property
    def account_list_all(self) -> list[Option]:
        return [Option(it['aid'], it['full_name'], False) for it in self.amap.values()]

    @cached_property
    def account_groups(self) -> list[tuple[str, list[Option]]]:
        amap = self.amap
        groups: dict[str, list[Option]] = {}
        fids = get_favs()
        favs = [amap[it] for it in fids if it in amap]

        result = []
        if favs:
            result.append(('Favorites', [Option(it['aid'], it['full_name'], False) for it in favs]))

        for it in amap.values():
            if it['parent'] and it['aid'] not in fids:
                atitle = ':'.join([amap[p]['name'] for p in it['parents'][1:]] + [it['name']])
                groups.setdefault(it['parents'][0], []).append(Option(it['aid'], atitle, it['is_placeholder']))

        key = itemgetter(1)
        for v in groups.values():
            v.sort(key=key)

        result.extend((amap[gaid]['name'], children) for gaid, children in groups.items())
        return result

    def account_list(self, exclude: Optional[str] = None, root: bool = False) -> list[Option]:
        result = []
        if root:
            result.append(Option('', 'ROOT', False))

        result.extend(it for it in self.account_list_all if it.value != exclude)
        return result

    @cached_property
    def amap(self) -> m.AccountMap:
        return account_map()

    @cached_property
    def current(self) -> 'BalanceMap':
        return current_balance()

    @cached_property
    def month(self) -> 'BalanceMap':
        dt = utils.month_start(self.today)
        return month_balance(dt)

    def total(self, aid: str, mode: str = 'month') -> m.BState:
        acc = self.amap[aid]
        if acc['is_sheet']:
            return self.current[aid].total
        else:
            if mode == 'month':
                return self.month[aid].total
            else:
                return self.day[aid].total

    @cached_property
    def day(self) -> 'BalanceMap':
        return day_balance(self.today)

    def sorted_total(self, total: m.BState) -> list[tuple[str, float]]:
        return sorted(total.items(), key=Env.cur_sort_key)

    def sorted_curs(self, total: m.BState) -> list[str]:
        return sorted(total.keys(), key=Env.cur_sort_key1)

    def top_sorted_curs(self) -> list[str]:
        keys = set[str]()
        for it in self.amap.top:
            keys |= self.total(it).keys()
        return sorted(keys, key=Env.cur_sort_key1)


class AccState:
    def __init__(self, account: m.AccountExt, bmap: 'BalanceMap'):
        self.account = account
        self.self_total = bmap.balances.get(account['aid'], {})
        self.bmap = bmap

    @cached_property
    def total(self) -> m.BState:
        if self.account['children']:
            return m.combine_states(self.self_total, *(self.bmap[it].total for it in self.account['children']))
        return self.self_total


class BalanceMap:
    def __init__(self, balances: m.Balance, amap: m.AccountMap):
        self.amap = amap
        self.balances = balances
        self.cache: dict[str, AccState] = {}

    def __getitem__(self, key: str) -> AccState:
        try:
            return self.cache[key]
        except KeyError:
            pass
        result = self.cache[key] = AccState(self.amap[key], self)
        return result


@utils.cached
def account_map() -> m.AccountMap:
    return m.account_list()


def get_favs() -> list[str]:
    return json.loads(m.get_param('accounts.favs') or '[]') or []


def set_favs(ids: list[str]) -> None:
    m.set_param('accounts.favs', json.dumps(ids))


@utils.cached
def month_balance(dt: datetime) -> BalanceMap:
    balances = m.balance(start=dt.timestamp(), end=utils.next_month_start(dt).timestamp())
    return BalanceMap(balances, account_map())


@utils.cached
def day_balance(dt: date) -> BalanceMap:
    start, end = utils.day_range(dt)
    balances = m.balance(start=start.timestamp(), end=end.timestamp())
    return BalanceMap(balances, account_map())


@utils.cached
def current_balance() -> BalanceMap:
    return BalanceMap(m.balance(), account_map())


def accounts_changed() -> None:
    account_map.clear()  # type: ignore[attr-defined]
    transactions_changed()


def transactions_changed() -> None:
    month_balance.clear()  # type: ignore[attr-defined]
    day_balance.clear()  # type: ignore[attr-defined]
    current_balance.clear()  # type: ignore[attr-defined]
