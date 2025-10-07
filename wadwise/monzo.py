import csv
import sys
import functools
from datetime import datetime
from pprint import pprint

import click

from .model import account_by_name, op, Account, op2, create_transaction

@functools.lru_cache(None)
def get_acc(name: str) -> Account:
    acc = account_by_name(name)
    assert acc, name
    return acc


FMT = '%d/%m/%Y:%H:%M:%S'
IFMT = '"%Y-%m-%d %H:%M'


def action_joint_me(acc, amount):
    ira = get_acc('Assets:Ira')['aid']
    joint = get_acc('Expenses:Joint')['aid']
    return (
        [op(acc['aid'], amount, 'GBP'), op(ira, -amount/2, 'GBP'), op(joint, -amount/2, 'GBP')],
        f'Joint deposit {-amount}'
    )

def action_joint_ira(acc, amount):
    assert False
    ira = get_acc('Assets:Ira')['aid']
    joint = get_acc('Expenses:Joint')['aid']
    return (
        [op(acc['aid'], amount, 'GBP'), op(ira, -amount/2, 'GBP'), op(joint, -amount/2, 'GBP')],
        f'Joint deposit {-amount}'
    )


@click.group()
def cli():
    pass


@cli.command('prepare')
@click.argument('data_fname')
def prepare(data_fname):
    data = csv.DictReader(open(data_fname))

    fields = ['Date', 'Action', 'Desc', 'Type', 'Category', 'Name', 'Amount']
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()

    for row in data:
        amount = float(row['Amount'])
        dt = datetime.strptime(row['Date'].strip() + ':' + row['Time'].strip(), FMT)
        out = {'Date': '"' + dt.strftime('%Y-%m-%d %H:%M'), 'Type': row['Type'].strip(),
               'Amount': amount, 'Category': row['Category'].strip(), 'Name': row['Name'].strip()}
        writer.writerow(out)


@cli.command('import')
@click.argument('account')
@click.argument('data_fname')
@click.option('-n', '--dry', is_flag=True)
def import_data(account, data_fname, dry):
    acc = get_acc(account)
    data = csv.DictReader(open(data_fname))
    transactions = []
    for it in  data:
        if not it['Date']:
            continue

        assert it['Action']
        action, _, param = it['Action'].partition(':')
        amount = float(it['Amount'])
        dt = datetime.strptime(it['Date'], IFMT)
        if action == 'dest':
            dest = get_acc(param)
            transactions.append((
                op2(acc['aid'], dest['aid'], -amount, 'GBP'),
                dt,
                it['Desc'] or None
            ))
        elif action == 'joint-me':
            ops, desc = action_joint_me(acc, amount)
            transactions.append((ops, dt, desc))
        else:
            raise Exception(f'Unknown action: {action}')

    if dry:
        for it in transactions:
            print(it)
    else:
        for it in transactions:
            create_transaction(*it)


if __name__ == '__main__':
    cli()
