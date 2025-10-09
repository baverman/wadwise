# type: ignore
import json
from datetime import datetime

import click


@click.group()
def cli():
    pass


@cli.command('import-gnucash')
@click.argument('fname')
def import_gnucash(fname):
    from wadwise import gnucash

    gnucash.import_data(fname)


@cli.command('report')
def report():
    from wadwise import model as m

    result = m.balance()
    print(json.dumps(result, indent=2, ensure_ascii=False))


@cli.command('list-accounts')
def list_accounts():
    from wadwise import model as m

    amap = m.account_list()
    for it in sorted(amap.values(), key=lambda x: x['full_name']):
        print(it['full_name'])


@cli.command('transactions')
@click.argument('account')
@click.option('--month')
def transactions(account, month):
    from wadwise import model as m
    from wadwise import state, utils

    dt = datetime.strptime(month, '%Y-%m')
    acc = m.account_by_name(account)
    assert acc

    amap = m.account_list()

    def get_amount(ops):
        for it in ops:
            if it[0] == acc['aid']:
                return it[1]

    def get_dest(ops):
        return ' / '.join(amap[it[0]]['full_name'] for it in ops if it[0] != acc['aid'])

    result = m.account_transactions(
        aid=acc['aid'], start_date=utils.month_start(dt), end_date=utils.next_month_start(dt)
    )
    for r in reversed(result):
        print(r['date'].strftime('%Y-%m-%d %H:%M'), get_amount(r['ops']), get_dest(r['ops']), sep='\t')

    b = state.month_balance(dt)
    bend = state.current_balance(utils.next_month_start(dt))
    print(b[acc['aid']].total, bend[acc['aid']].total)


if __name__ == '__main__':
    cli()
