import sys
import os.path
import glob

import logging
log = logging.getLogger()
logging.basicConfig(level='INFO', stream=sys.stdout)

if os.environ.get('WADWISE_VENDOR') == '1':
    sys.path.insert(0, os.path.dirname(__file__) + '/vendor')

from wadwise import web, db

db.DB = os.environ.get('WADWISE_DB', 'data.sqlite')

web.init()
# web.app.run(host='127.0.0.1', port=5000)
web.app.run(host='127.0.0.10', port=5000)
# web.app.run(host='0.0.0.0', port=5000)
