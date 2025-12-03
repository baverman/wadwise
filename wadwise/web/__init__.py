import functools
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from flask import Flask, request

from wadwise import model as m
from wadwise import state

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_mapping(
    SECRET_KEY='boo',
    SEND_FILE_MAX_AGE_DEFAULT=86400,
)

DEV = os.environ.get('DEV') == '1'


def init() -> None:
    m.create_tables()
    m.create_initial_accounts()


class RequestState(TypedDict):
    env: state.Env
    today: date
    today_str: str
    DEV: bool


def get_request_state() -> RequestState:
    if hasattr(request, '_wadwise_context'):
        return request._wadwise_context  # type: ignore[no-any-return]

    today = request.args.get('today')
    if today:
        try:
            today = datetime.strptime(today, '%Y-%m').date()
        except Exception:
            today = None

    today = today or date.today()
    result: RequestState = {
        'env': state.Env(today),
        'today': today,
        'today_str': today.strftime('%Y-%m'),
        'DEV': DEV,
    }
    request._wadwise_context = result  # type: ignore[attr-defined]
    return result


@app.context_processor
def setup_context_processor() -> dict[str, Any]:
    return cast(dict[str, Any], get_request_state())  # TODO: remove after migration


@app.template_global()
def fmt_num(value: float) -> str:
    if value:
        return '{:_.2f}'.format(value).replace('_', '<span class="delim"></span>')
    else:
        return ''


@app.template_global()
def merge(*values: dict[object, object]) -> dict[object, object]:
    result = {}
    for v in values:
        result.update(v)
    return result


@functools.cache
def get_manifest() -> dict[str, dict[str, str]]:
    assets = Path(__file__).parent / 'static/assets'
    return json.loads(open(assets / '.vite/manifest.json').read())  # type: ignore[no-any-return]


@app.template_global()
def hash_url(name: str) -> str:
    if DEV:
        return f'http://localhost:5173/{name}'
    else:
        return f'/static/assets/{get_manifest()[name]["file"]}'


from . import views

_ = views
