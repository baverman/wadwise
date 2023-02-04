import json
from datetime import date
from collections import namedtuple
from cached_property import cached_property

from wadwise import model as m, utils

Option = namedtuple('Option', 'value title hidden')
Option2 = namedtuple('Option2', 'value title')


class Env:
    acc_types = [Option2(*it) for it in m.acc_types]
    cur_sort_key = lambda r, d={'RUB': 'zzzzz'}: d.get(r[0], r[0])
    cur_sort_key1 = lambda r, d={'RUB': 'zzzzz'}: d.get(r, r)

    @cached_property
    def account_list_all(self):
        return [Option(it['aid'], it['full_name'], False) for it in self.amap.values()]

    @cached_property
    def account_groups(self):
        amap = self.amap
        groups = {}
        fids = get_favs()
        favs = [amap[it] for it in fids if it in amap]

        result = []
        if favs:
            result.append(('Favorites', [Option(it['aid'], it['full_name'], False) for it in favs]))

        for it in amap.values():
            if it['parent'] and it['aid'] not in fids:
                atitle = ':'.join([amap[p]['name'] for p in it['parents'][1:]] + [it['name']])
                groups.setdefault(it['parents'][0], []).append(Option(it['aid'], atitle, it['is_placeholder']))

        result.extend((amap[gaid]['name'], children) for gaid, children in groups.items())
        return result

    def account_list(self, exclude=None, root=False):
        result = []
        if root:
            result.append(('', 'ROOT'))

        result.extend(it for it in self.account_list_all if it.value != exclude)
        return result

    @cached_property
    def amap(self):
        return account_map()

    @cached_property
    def current(self):
        return current_balance()

    @cached_property
    def month(self):
        dt = utils.month_start(date.today())
        return month_balance(dt)

    def total(self, aid, mode='month'):
        acc = self.amap[aid]
        if acc['is_sheet']:
            return self.current[aid].total
        else:
            if mode == 'month':
                return self.month[aid].total
            else:
                return self.day[aid].total

    @cached_property
    def day(self):
        return day_balance(date.today())

    def sorted_total(self, total):
        return sorted(total.items(), key=Env.cur_sort_key)

    def sorted_curs(self, total):
        return sorted(total.keys(), key=Env.cur_sort_key1)

    def top_sorted_curs(self):
        keys = {}.keys()
        for it in self.amap.top:
            keys |= self.total(it).keys()
        return sorted(keys, key=Env.cur_sort_key1)


class AccState:
    def __init__(self, account, bmap):
        self.account = account
        self.self_total = bmap.balances.get(account['aid'], {})
        self.bmap = bmap

    @cached_property
    def total(self):
        if self.account['children']:
            return m.combine_states(self.self_total, *(self.bmap[it].total for it in self.account['children']))
        return self.self_total


class BalanceMap:
    def __init__(self, balances, amap):
        self.amap = amap
        self.balances = balances
        self.cache = {}

    def __getitem__(self, key):
        try:
            return self.cache[key]
        except KeyError:
            pass
        result = self.cache[key] = AccState(self.amap[key], self)
        return result


@utils.cached
def account_map():
    return m.account_list()


def get_favs():
    return json.loads(m.get_param('accounts.favs') or '[]') or []


def set_favs(ids):
    m.set_param('accounts.favs', json.dumps(ids))


@utils.cached
def month_balance(dt):
    balances = m.balance(start=dt.timestamp(), end=utils.next_month_start(dt).timestamp())
    return BalanceMap(balances, account_map())


@utils.cached
def day_balance(dt):
    start, end = utils.day_range(dt)
    balances = m.balance(start=start.timestamp(), end=end.timestamp())
    return BalanceMap(balances, account_map())


@utils.cached
def current_balance():
    return BalanceMap(m.balance(), account_map())


def accounts_changed():
    account_map.clear()
    transactions_changed()


def transactions_changed():
    month_balance.clear()
    day_balance.clear()
    current_balance.clear()
