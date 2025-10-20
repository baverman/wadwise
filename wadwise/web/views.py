import io
import json
import subprocess
from datetime import date as dt_date
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Union, cast

from covador import Date, DateTime, enum, item, opt
from covador.flask import form, query_string
from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from wadwise import db, monzo, state, utils
from wadwise import model as m
from wadwise.web import app

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
        account = {}  # type: ignore[typeddict-item]
    accounts = m.get_sub_accounts(aid)
    transactions = m.account_transactions(aid=aid)
    return render_template(
        'account/view.html',
        accounts=accounts,
        account=account,
        transactions=transactions,
        total_mode=request.cookies.get('total_mode', 'month'),
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
@query_string(dest=str, tid=opt(str), split=opt(bool), type=opt(str, ''))
def transaction_edit(dest: str, tid: Optional[str], split: bool, type: str) -> str:
    assert tid or dest
    if tid:
        (trn,) = m.account_transactions(aid=dest, tid=tid)
        form = cast(dict[str, Any], trn)
    else:
        cur = state.get_cur_list()[0]
        form = {'cur': cur, 'ops': ((None, 0, cur), (dest, 0, cur)), 'dest': dest, 'date': datetime.now()}

    cur_list = state.get_cur_list()
    if split or form.get('split'):
        return render_template('transaction/split.html', form=form, cur_list=cur_list)
    else:
        return render_template('transaction/edit.html', form=form, cur_list=cur_list, type=type)


transaction_actions_t = opt(str) | enum('delete', 'copy', 'copy-now')


@app.route('/transaction/edit', methods=['POST'])
@query_string(dest=str, tid=opt(str), type=opt(str, ''))
@form(src=str, amount=float, desc=opt(str), cur=str, action=transaction_actions_t, _=combine_date(), **split_date())
def transaction_save(
    tid: Optional[str],
    src: str,
    dest: str,
    amount: float,
    cur: str,
    action: str,
    desc: Optional[str],
    date: datetime,
    type: str,
) -> Response:
    ops = m.dop2(type, src, dest, amount, cur)
    return transaction_save_helper(action, tid, ops, dest, date, desc)


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
    for op in ops:
        aid = op['aid']
        if aid != dest and amap[aid]['is_sheet']:
            flash(f"""{amap[aid]['full_name']}: {cbal[aid].total.get(op['cur'], 0)} {op['cur']}""")

    return redirect(url_for('account_view', aid=dest, _anchor=tid and f't-{tid}'))


@app.route('/transaction/split-edit', methods=['POST'])
@query_string(dest=str, tid=opt(str))
@form(
    desc=opt(str),
    acc=item(str, multi=True),
    amount=item(float, multi=True),
    cur=item(str, multi=True),
    action=transaction_actions_t,
    _=combine_date(),
    **split_date(),
)
def transaction_split_save(
    tid: Optional[str],
    dest: str,
    acc: list[str],
    amount: list[float],
    cur: list[str],
    action: str,
    date: datetime,
    desc: Optional[str],
) -> Response:
    ops = [m.op(*it) for it in zip(acc, amount, cur)]
    return transaction_save_helper(action, tid, ops, dest, date, desc)


@app.route('/transaction/over')
@query_string(aid=str, today=str | date_t)
def transaction_transfer_over(aid: str, today: dt_date) -> str:
    next_date = today.replace(day=1)
    prev_date = next_date - timedelta(days=1)
    return render_template(
        'transaction/over.html',
        aid=aid,
        next_date=utils.fmt_date(next_date),
        prev_date=utils.fmt_date(prev_date),
        cur_list=state.get_cur_list(),
    )


@app.route('/transaction/over', methods=['POST'])
@query_string(aid=str)
@form(over=str, cur=str, amount=float, next_date=str | datetime_trunc_t, prev_date=str | datetime_trunc_t)
def transaction_transfer_over_save(
    aid: str, over: str, cur: str, amount: float, next_date: datetime, prev_date: datetime
) -> Response:
    with db.transaction():
        m.create_transaction(m.op2(aid, over, amount, cur), prev_date, 'Transfer over')
        tid = m.create_transaction(m.op2(over, aid, amount, cur), next_date, 'Transfer over')
    state.transactions_changed()
    return redirect(url_for('account_view', aid=aid, _anchor=f't-{tid}'))


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

    data.sort(reverse=True, key=lambda x: x['date'])
    max_dt = data[0]['date']
    min_dt = data[-1]['date']

    def get_amount(tr: m.TransactionAny) -> tuple[float, str]:
        for aid, amount, cur in tr['ops']:
            if aid == src:
                return (amount, cur)
        raise RuntimeError('Never')

    existing = m.account_transactions(aid=src, start_date=min_dt, end_date=max_dt + timedelta(seconds=1))
    existing_keys = set((it['date'], get_amount(it)) for it in existing)

    for it in data:
        dt = it['date']
        if (dt, (it['amount'], it['cur'])) in existing_keys:
            it['ignore'] = True
        it['date'] = dt.timestamp()  # type: ignore[typeddict-item]
        it['date_str'] = dt.strftime('%Y-%m-%d')  # type: ignore[typeddict-unknown-key]

    bend = state.current_balance(utils.next_month_start(max_dt))[src].total
    return render_template('import_transactions.html', src=src, balance=bend, transactions=data, bdate=max_dt)


@app.route('/import/transactions', methods=['POST'])
@form(src=str, transactions=json.loads)
def import_transactions_apply(src: str, transactions: list[monzo.ImportTransaction]) -> Response:
    monzo.import_data(src, transactions)
    state.transactions_changed()
    return redirect(url_for('account_view', aid=src))


@app.route('/settings/')
def settings() -> str:
    return render_template(
        'settings.html', fav_ids=state.get_favs(), cur_list=state.get_cur_list(), joints=m.get_joint_accounts()
    )


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
