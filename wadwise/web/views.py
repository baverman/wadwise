import time
from datetime import datetime

from covador import opt, DateTime, item, enum
from covador.flask import query_string, form

from flask import render_template, redirect, url_for, request, flash

from wadwise import model as m, state
from wadwise.web import app

datetime_t = DateTime('%Y-%m-%dT%H:%M')


@app.route('/account')
@query_string(aid=opt(str))
def account_view(aid):
    account = aid and state.account_map()[aid] or {}
    accounts = m.get_sub_accounts(aid)
    transactions = m.account_transactions(aid=aid)
    return render_template('account/view.html', accounts=accounts,
                           account=account, transactions=transactions,
                           total_mode=request.cookies.get('total_mode', 'month'))


@app.route('/account/edit')
@query_string(aid=opt(str), parent=opt(str))
def account_edit(**form):
    if form['aid']:
        account = m.account_by_id(form['aid'])
        form.update(account)
    elif form['parent']:
        pacc = m.account_by_id(form['parent'])
        form['type'] = pacc['type']
    return render_template('account/edit.html', form=form)


@app.route('/account/edit', methods=['POST'])
@query_string(aid=opt(str))
@form(name=str, parent=opt(str), type=str, desc=opt(str), is_placeholder=opt(bool, False))
def account_save(aid, **form):
    if aid:
        m.update_account(aid, **form)
    else:
        aid = m.create_account(**form)

    state.accounts_changed()
    return redirect(url_for('account_view', aid=aid))


@app.route('/account/delete', methods=['POST'])
@query_string(aid=str)
def account_delete(aid):
    account = m.account_by_id(aid)
    m.delete_account(aid, account['parent'])
    state.accounts_changed()
    return redirect(url_for('account_view', aid=account['parent']))


@app.route('/transaction/edit')
@query_string(dest=str, tid=opt(str), split=opt(bool))
def transaction_edit(split, **form):
    assert form['tid'] or form['dest']
    if form['tid']:
        form, = m.account_transactions(aid=form['dest'], tid=form['tid'])
        form['date'] = form['date'].strftime(datetime_t.fmt)
    else:
        form['cur'] = 'GBP'
        form['date'] = datetime.now().strftime(datetime_t.fmt)
        form['ops'] = (None, 0, 'GBP'), (form['dest'], 0, 'GBP')

    if split or form.get('split'):
        return render_template('transaction/split.html', form=form)
    else:
        return render_template('transaction/edit.html', form=form)


transaction_actions_t = opt(str) | enum('delete', 'copy', 'copy-now')


@app.route('/transaction/edit', methods=['POST'])
@query_string(dest=str, tid=opt(str))
@form(src=str, amount=float, date=str | datetime_t, desc=opt(str), cur=str, action=transaction_actions_t)
def transaction_save(tid, src, dest, amount, cur, action, **form):
    ops = m.op2(src, dest, amount, cur)
    return transaction_save_helper(action, tid, ops, form, dest)


def transaction_save_helper(action, tid, ops, form, dest):
    if action == 'delete':
        m.delete_transaction(tid)
    else:
        if action == 'copy-now':
            form['date'] = int(time.time())
        else:
            form['date'] = form['date'].timestamp()
        if tid and action not in ('copy', 'copy-now'):
            m.update_transaction(tid, ops, **form)
        else:
            m.create_transaction(ops, **form)

    state.transactions_changed()

    amap = state.account_map()
    cbal = state.current_balance()
    for op in ops:
        aid = op['aid']
        if aid != dest and amap[aid]['is_sheet']:
            flash(f'''{amap[aid]['full_name']}: {cbal[aid].total.get(op['cur'], 0)} {op['cur']}''')

    return redirect(url_for('account_view', aid=dest))


@app.route('/transaction/split-edit', methods=['POST'])
@query_string(dest=str, tid=opt(str))
@form(date=str | datetime_t, desc=opt(str),
      acc=item(str, multi=True),
      amount=item(float, multi=True),
      cur=item(str, multi=True),
      action=transaction_actions_t)
def transaction_split_save(tid, dest, acc, amount, cur, action, **form):
    ops = [m.op(*it) for it in zip(acc, amount, cur)]
    return transaction_save_helper(action, tid, ops, form, dest)


@app.route('/')
def index():
    return redirect(url_for('account_view'))


@app.route('/import/')
def import_data():
    return render_template('import_data.html')


@app.route('/import/', methods=['POST'])
def import_data_apply():
    if 'gnucash' in request.files:
        from wadwise import gnucash
        gnucash.import_data(request.files['gnucash'])

    state.accounts_changed()
    state.transactions_changed()
    return redirect(url_for('account_view'))


@app.route('/account/favs')
def favs_edit():
    return render_template('favs_edit.html', ids=state.get_favs())


@app.route('/account/favs', methods=['POST'])
@form(ids=opt(str, src='acc', multi=True))
def favs_edit_apply(ids):
    state.set_favs(ids)
    return redirect(url_for('account_view'))
