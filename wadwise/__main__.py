# type: ignore
import json

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


if __name__ == '__main__':
    cli()
