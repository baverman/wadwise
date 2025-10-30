import logging
import os.path
import sys
import click

log = logging.getLogger()
logging.basicConfig(level='INFO', stream=sys.stdout)

if os.environ.get('WADWISE_VENDOR') == '1':
    sys.path.insert(0, os.path.dirname(__file__) + '/vendor')

from wadwise import db, web

db.DB = os.environ.get('WADWISE_DB', 'data.sqlite')

@click.command()
@click.option('-b', '--bind', default='127.0.0.10:5000')
def main(bind):
    host, sep, port = bind.rpartition(':')
    if not sep:
        host, port = port, ''
    host = host or '127.0.0.10'
    port = port or '5000'

    web.init()
    web.app.run(host=host, port=int(port))

if __name__ == '__main__':
    main()
