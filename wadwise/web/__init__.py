from datetime import date, datetime
from typing import Any

from flask import Flask, request

from wadwise import model as m
from wadwise import state

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_mapping(SECRET_KEY='boo')


def init() -> None:
    m.create_tables()
    m.create_initial_accounts()


@app.context_processor
def setup_context_processor() -> dict[str, Any]:
    today = request.args.get('today')
    if today:
        try:
            today = datetime.strptime(today, '%Y-%m').date()
        except Exception:
            today = None

    today = today or date.today()
    return {'env': state.Env(today), 'today': today, 'today_str': today.strftime('%Y-%m')}


@app.template_global()
def fmt_num(value: float) -> str:
    if value:
        return '{:_.2f}'.format(value).replace('_', '<span class="delim"></span>')
    else:
        return ''


from . import views

_ = views
