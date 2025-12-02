import io
import json
import subprocess
from datetime import date as ddate
from datetime import datetime, timedelta
from itertools import groupby
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, TypedDict, Union, cast

from covador import Date, DateTime, enum, opt
from covador.flask import form, query_string
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from wadwise import db, monzo, state, utils
from wadwise import model as m
from wadwise.web import app, get_request_state

datetime_t = DateTime('%Y-%m-%d%H:%M:%S')
datetime_trunc_t = DateTime('%Y-%m-%d')
date_t = Date('%Y-%m-%d')

if TYPE_CHECKING:
    from typing_extensions import Unpack
else:
    Unpack = list


def combine_date(name: str = 'date') -> Callable[[dict[str, Any]], dict[str, Any]]:
    def converter(form: dict[str, Any]) -> dict[str, Any]:
        form[name] = datetime_t(form[name] + form.pop(name + '_time'))
        return form

    return converter


def split_date(name: str = 'date') -> dict[str, Any]:
    return {name: str, name + '_time': str}


@app.route('/account')
@query_string(aid=opt(str))
def account_view(aid: Optional[str]) -> str:
    if aid:
        account = state.account_map()[aid]
    else:
        account = None
    accounts = m.get_sub_accounts(aid)
    data = m.account_transactions(aid=aid)

    now = datetime.now()

    key = lambda x: x['date'].strftime('%a %d %B') if x['date'].year == now.year else x['date'].strftime('%d %B %Y')
    transactions = []
    for k, g in groupby(data, key):
        transactions.append((k, list(g)))

    st = get_request_state()
    env = st['env']

    cur_list = {}
    balance = {}
    if account:
        cur_list['total'] = env.sorted_curs(env.total(account['aid']))
        balance['current_total'] = env.current[account['aid']].total
        balance['month_total'] = env.month[account['aid']].total
        if account['is_sheet']:
            balance['month_debit'] = mdeb = env.month[account['aid']].debit
            balance['month_credit'] = mcred = env.month[account['aid']].credit
            balance['prev_total'] = prev_tot = env.prev[account['aid']].total
            cur_list['full'] = env.sorted_curs({**prev_tot, **mdeb, **mcred})
    else:
        cur_list['total'] = env.top_sorted_curs()

    view_data = {
        'account': account,
        'accounts': accounts,
        'accounts_totals': env.accounts_totals(accounts),
        'joint_accounts': env.joint_accounts,
        'urls': {
            'settings': url_for('settings'),
            'account_view': url_for('account_view'),
            'account_edit': url_for('account_edit'),
            'transaction_edit': url_for('transaction_edit'),
            'import_monzo': url_for('import_monzo'),
        },
        'amap': env.amap,
        'today_str': st['today_str'],
        'today_dsp': st['today'].strftime('%b %Y'),
        'cur_list': cur_list,
        'balance': balance,
        'transactions': transactions,
    }

    return render_template(
        'app.html',
        module='account_view.js',
        data=view_data,
    )


@app.route('/account/edit')
@query_string(aid=opt(str), parent=opt(str))
def account_edit(aid: Optional[str], parent: Optional[str]) -> str:
    form: Union[dict[str, str | None], m.Account]
    if aid:
        account = m.account_by_id(aid)
        if not account:
            return abort(404)
        form = account
    elif parent:
        pacc = m.account_by_id(parent)
        if not pacc:
            return abort(404)
        form = {'type': pacc['type'], 'parent': parent, 'is_hidden': None}
    form['hidden_value'] = '' if form['is_hidden'] is None else str(int(form['is_hidden']))  # type: ignore[typeddict-unknown-key]
    return render_template('account/edit.html', form=form)


@app.route('/account/edit', methods=['POST'])
@query_string(aid=opt(str))
@form(name=str, parent=opt(str), type=str, desc=opt(str), is_placeholder=opt(bool, False), is_hidden=opt(bool))
def account_save(aid: Optional[str], **form: Unpack[m.AccountB]) -> Response:
    if aid:
        m.update_account(aid, **form)
    else:
        aid = m.create_account(**form)

    state.accounts_changed()
    return redirect(url_for('account_view', aid=aid))


@app.route('/account/delete', methods=['POST'])
@query_string(aid=str)
def account_delete(aid: str) -> Response:
    account = m.account_by_id(aid)
    if not account:
        return abort(404)
    m.delete_account(aid, account['parent'])
    state.accounts_changed()
    return redirect(url_for('account_view', aid=account['parent']))


@app.route('/transaction/edit')
@query_string(dest=str, tid=opt(str), split=opt(bool))
def transaction_edit(dest: str, tid: Optional[str], split: bool) -> str:
    assert tid or dest
    if tid:
        (trn,) = m.account_transactions(aid=dest, tid=tid)
        form = cast(dict[str, Any], trn)
    else:
        cur = state.get_cur_list()[0]
        form = {'cur': cur, 'ops': ((None, 0, cur), (dest, 0, cur)), 'dest': dest, 'date': datetime.now()}

    cur_list = state.get_cur_list()

    env = get_request_state()['env']
    view_data = {
        'form': form,
        'accountTitle': env.account_title(form['dest']),
        'curList': cur_list,
        'dateStr': form['date'].strftime('%Y-%m-%d'),
        'timeStr': form['date'].strftime('%H:%M:%S'),
        'split': split or form.get('split'),
        'defaultAccount': env.account_groups[0][1][0][0],
        'urls': {
            'transaction_edit': url_for('transaction_edit'),
        },
    }
    return render_template('app.html', data=view_data, module='transaction_edit.js')


transaction_actions_t = opt(str) | enum('delete', 'copy', 'copy-now')


class TransactionSave(TypedDict):
    simple: tuple[str, str, float, str]
    ops: list[tuple[str, float, str, bool]]


@app.route('/transaction/edit', methods=['POST'])
@query_string(dest=str, tid=opt(str))
@form(ops=json.loads, desc=opt(str), action=transaction_actions_t, _=combine_date(), **split_date())
def transaction_save(
    tid: Optional[str], dest: str, action: str, desc: Optional[str], date: datetime, ops: TransactionSave
) -> Response:
    oplist: list[m.Operation] = []
    if 'simple' in ops:
        oplist.extend(m.dop2(*ops['simple']))
    if 'ops' in ops:
        oplist.extend(m.op(*it) for it in ops['ops'])
    if not oplist:
        abort(400)
    return transaction_save_helper(action, tid, oplist, m.decode_account_id(dest)[0], date, desc)


def transaction_save_helper(
    action: str, tid: Optional[str], ops: Iterable[m.Operation], dest: str, date: datetime, desc: Optional[str]
) -> Response:
    if action == 'delete':
        assert tid
        m.delete_transaction(tid)
    else:
        if action == 'copy-now':
            date = datetime.now()
        if tid and action not in ('copy', 'copy-now'):
            m.update_transaction(tid, ops, date, desc)
        else:
            tid = m.create_transaction(ops, date, desc)

    state.transactions_changed()

    amap = state.account_map()
    cbal = state.current_balance()
    flashed: set[str] = set()
    for op in ops:
        aid = op['aid']
        if aid != dest and amap[aid]['is_sheet'] and aid not in flashed:
            flash(f"""{amap[aid]['full_name']}: {cbal[aid].total.get(op['cur'], 0):.2f} {op['cur']}""")
            flashed.add(aid)

    return redirect(url_for('account_view', aid=dest, _anchor=tid and f't-{tid}'))


@app.route('/')
def index() -> Response:
    return redirect(url_for('account_view'))


@app.route('/import/')
def import_data() -> str:
    return render_template('import_data.html')


@app.route('/import/', methods=['POST'])
def import_data_apply() -> Response:
    if 'gnucash' in request.files:
        from wadwise import gnucash

        gnucash.import_data(request.files['gnucash'])  # type: ignore[attr-defined]

    state.accounts_changed()
    state.transactions_changed()
    return redirect(url_for('account_view'))


@app.route('/import/monzo', methods=['POST'])
@form(src=str)
def import_monzo(src: str) -> str:
    if 'monzo' in request.files:
        data = monzo.prepare(io.StringIO(request.files['monzo'].read().decode()))

    src_aid = m.decode_account_id(src)[0]
    data.sort(reverse=True, key=lambda x: x['date'])
    max_dt = data[0]['date']
    min_dt = data[-1]['date']

    def get_amount(tr: m.TransactionAny) -> tuple[float, str]:
        for aid, amount, cur, _ in tr['ops']:
            if aid in src_aids:
                return (amount, cur)
        raise RuntimeError('Never')

    joints = m.get_joint_accounts()
    src_joint = joints.get(src_aid)
    if src_joint:
        src_aids = set(src_joint['joints'])
        data = [it for it in data if it['amount'] > 0]
        existing = m.account_transactions(
            aids=src_joint['joints'], start_date=min_dt, end_date=max_dt + timedelta(seconds=1)
        )
    else:
        src_aids = {src_aid}
        existing = m.account_transactions(aid=src_aid, start_date=min_dt, end_date=max_dt + timedelta(seconds=1))

    existing_keys = set(m.seen_tx_key(it['date'], *get_amount(it)) for it in existing)
    seen_keys = m.seen_transactions(src_aid)

    for it in data:
        dt = it['date']
        key = m.seen_tx_key(dt, it['amount'], it['cur'])
        it['txkey'] = key  # type: ignore[typeddict-unknown-key]
        if key in existing_keys:
            it['state'] = 'imported'
        elif key in seen_keys:
            it['state'] = 'seen'
        it['date'] = dt.timestamp()  # type: ignore[typeddict-item]
        it['date_str'] = dt.strftime('%Y-%m-%d')  # type: ignore[typeddict-unknown-key]

    bend = state.current_balance(utils.next_month_start(max_dt))[src_aid].total

    env = get_request_state()['env']
    view_data = {
        'transactions': data,
        'balance': bend,
        'src': src,
        'name': env.account_title(src),
        'urls': {'import_transactions_apply': url_for('import_transactions_apply')},
    }

    return render_template('app.html', data=view_data, module='import_transactions.js')


@app.route('/import/transactions', methods=['POST'])
@form(src=str, transactions=json.loads)
def import_transactions_apply(src: str, transactions: list[monzo.ImportTransaction]) -> Response:
    aid = m.decode_account_id(src)[0]
    seen_keys = [it['txkey'] for it in transactions if it['state'] == 'seen']
    if seen_keys:
        m.update_seen_transactions(aid, datetime.fromtimestamp(transactions[0]['date']), seen_keys)
    transactions_to_import = [it for it in transactions if not it['state']]
    monzo.import_data(src, transactions_to_import)
    state.transactions_changed()
    return redirect(url_for('account_view', aid=aid))


@app.route('/settings/')
def settings() -> str:
    view_data = {
        'favAccs': state.get_favs(),
        'joints': list(m.get_joint_accounts().values()),
        'curList': state.get_cur_list(),
        'favIds': state.get_favs(),
    }
    return render_template('app.html', data=view_data, module='settings.js')


@app.route('/settings/favs', methods=['POST'])
@form(ids=opt(str, src='acc', multi=True))
def favs_edit_apply(ids: list[str]) -> Response:
    state.set_favs(ids)
    return redirect(url_for('settings'))


@app.route('/settings/joint-accounts', methods=['POST'])
@form(data=json.loads)
def join_accounts_edit_apply(data: list[object]) -> Response:
    m.set_joint_accounts(data)
    return redirect(url_for('settings'))


@app.route('/settings/cur-list', methods=['POST'])
@form(cur_list=str)
def cur_list_edit_apply(cur_list: str) -> Response:
    clist = list(filter(None, (it.strip().upper() for it in cur_list.splitlines())))
    state.set_cur_list(clist)
    return redirect(url_for('settings'))


@app.route('/settings/backup', methods=['POST'])
def backup_db() -> Response:
    fname = db.backup()
    subprocess.run(['termux-open', '--send', fname], check=True)
    return redirect(url_for('settings'))


@app.route('/api/balance')
@query_string(aid=str, date=str | date_t)
def api_account_balance(aid: str, date: ddate) -> Response:
    aid = m.decode_account_id(aid)[0]
    return jsonify({'result': state.current_balance(utils.next_month_start(date))[aid].total})
