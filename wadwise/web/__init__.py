from datetime import datetime, date
from flask import Flask, request

from wadwise import model as m, state


app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_mapping(SECRET_KEY='boo')


def init():
    m.create_tables()
    m.create_initial_accounts()


@app.context_processor
def setup_context_processor():
    today = request.args.get('today')
    if today:
        try:
            today = datetime.strptime(today, '%Y-%m-%d').date()
        except Exception as e:
            today = None

    today = today or date.today()
    return {
        'env': state.Env(today),
        'today': today,
        'today_str': today.strftime('%Y-%m-%d'),
    }


@app.template_global()
def fmt_num(value):
    if value:
        return '{:_.2f}'.format(value).replace('_', '<span class="delim"></span>')
    else:
        return ''


from . import views as _views
