from flask import Flask

from wadwise import model as m, state


app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_mapping(SECRET_KEY='boo')


def init():
    m.create_tables()
    m.create_initial_accounts()


@app.context_processor
def setup_context_processor():
    return {'env': state.Env()}


@app.template_global()
def fmt_num(value):
    if value:
        return '{:_.2f}'.format(value).replace('_', '<span class="delim"></span>')
    else:
        return ''


from . import views
