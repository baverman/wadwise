from datetime import date as dt_date
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Union, cast

from covador import Date, DateTime, enum, item, opt
from covador.flask import form, query_string
from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from wadwise import db
from wadwise import model as m
from wadwise import state, utils
from wadwise.web import app

datetime_t = DateTime('%Y-%m-%d%H:%M')
datetime_trunc_t = DateTime('%Y-%m-%d')
date_t = Date('%Y-%m-%d')

if TYPE_CHECKING:
    from typing_extensions import Unpack
else:
    Unpack = list


def split_date(form: dict[str, Any], dt: datetime, name: str = 'date') -> None:
    form[name] = dt.strftime('%Y-%m-%d')
    form[name + '_time'] = dt.strftime('%H:%M')


def combine_date(name: str = 'date') -> Callable[[dict[str, Any]], dict[str, Any]]:
    def converter(form: dict[str, Any]) -> dict[str, Any]:
        form[name] = datetime_t(form[name] + form.pop(name + '_time'))
        return form

    return converter


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
    form: Union[dict[str, str], m.Account]
    if aid:
        account = m.account_by_id(aid)
        if not account:
            return abort(404)
        form = account
    elif parent:
        pacc = m.account_by_id(parent)
        if not pacc:
            return abort(404)
        form = {'type': pacc['type'], 'parent': parent}
    return render_template('account/edit.html', form=form)


@app.route('/account/edit', methods=['POST'])
@query_string(aid=opt(str))
@form(name=str, parent=opt(str), type=str, desc=opt(str), is_placeholder=opt(bool, False))
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
        split_date(form, trn['date'])
    else:
        cur = 'GBP'
        form = {'cur': cur, 'ops': ((None, 0, cur), (dest, 0, cur))}
        split_date(form, datetime.now())

    if split or form.get('split'):
        return render_template('transaction/split.html', form=form)
    else:
        return render_template('transaction/edit.html', form=form)


transaction_actions_t = opt(str) | enum('delete', 'copy', 'copy-now')


@app.route('/transaction/edit', methods=['POST'])
@query_string(dest=str, tid=opt(str))
@form(src=str, amount=float, desc=opt(str), cur=str, action=transaction_actions_t, _=combine_date())
def transaction_save(
    tid: Optional[str], src: str, dest: str, amount: float, cur: str, action: str, desc: Optional[str], date: datetime
) -> Response:
    ops = m.op2(src, dest, amount, cur)
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
            flash(f'''{amap[aid]['full_name']}: {cbal[aid].total.get(op['cur'], 0)} {op['cur']}''')

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
        'transaction/over.html', aid=aid, next_date=utils.fmt_date(next_date), prev_date=utils.fmt_date(prev_date)
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


@app.route('/account/favs')
def favs_edit() -> str:
    return render_template('favs_edit.html', ids=state.get_favs())


@app.route('/account/favs', methods=['POST'])
@form(ids=opt(str, src='acc', multi=True))
def favs_edit_apply(ids: list[str]) -> Response:
    state.set_favs(ids)
    return redirect(url_for('account_view'))
