import classNames from 'classnames'
import {useState, useEffect} from 'preact/hooks'
import {useSignal} from '@preact/signals'

import {hh as h, registerPreactData, preventDefault, initPreactData, urlqs,
        nbsp, join} from './utils.js'

const dqs = document.querySelector.bind(document)

function AccountHeader({account, urls, amap, today_str, today_dsp}) {
    function dateChanged(e) {
        const params = new URLSearchParams(window.location.search)
        params.set('today', e.currentTarget.value)
        window.location.search = params
    }

    return [
        h('form-aligned',
            h('div.label', join(':', [
                h('a', {href: urlqs(urls.account_view)}, 'Home'),
                ...account.parents.map((p) => h('a', {href: urlqs(urls.account_view, {aid: p})}, amap[p].name)),
                h('a', {href: urlqs(urls.account_edit, {aid: account.aid})}, account.name),
            ])),
            h('div.aligned-right',
                h('input.opaque', {id: 'dateSelector', type: 'month', value: today_str, onInput: dateChanged}),
                h('a', {href: '#date', onClick: preventDefault(() => dqs('#dateSelector').showPicker())}, today_dsp),
            ),
        )
    ]
}

function totalsRows(cur_list, total, children, props) {
    const result = []
    let first = true
    for(const cur of cur_list) {
        if (total[cur]) {
            result.push(h('tr',
                h('td', first && children),
                h('td.tright.amount', total[cur].toFixed(2), nbsp, h('span.cur', cur))
            ))
            first = false
        }
    }

    if (!result.length && props?.showZero) {
        result.push(h('tr', h('td', children)))
    }
    return h('table.w-100', props?.tprops, h('tbody', result))
}

function separateOnMultiCurs(cur_list, ...children) {
    if (cur_list.length > 1) {
        return h('v-stack', children)
    } else {
        return children
    }
}

function AccountStatus({account, balance, cur_list}) {
    const [open, setOpen] = useState(account.is_sheet && cur_list.full.length == 1)
    if (account.is_sheet) {
        return separateOnMultiCurs(cur_list.full,
            totalsRows(cur_list.total, balance.current_total, 'Balance' + (open ? '' : ' [+]'),
                       {tprops: {onClick: () => setOpen(true)}}),
            open && [
                totalsRows(cur_list.full, balance.prev_total, 'Month start'),
                totalsRows(cur_list.full, balance.month_debit, 'In'),
                totalsRows(cur_list.full, balance.month_credit, 'Out'),
            ],
        )
    } else {
        return totalsRows(cur_list.total, balance.month_total, 'This month')
    }
}

function SubAccounts({cur_list, accounts, accounts_totals, urls, today_str}) {
    return [
        h('hr'),
        separateOnMultiCurs(cur_list.total,
            accounts.map((it) =>
                totalsRows(cur_list.total, accounts_totals[it.aid],
                    h('a', {href: urlqs(urls.account_view, {aid: it.aid, today: today_str})}, it.name), {showZero: true}),
            )
        )
    ]
}

function AccountLinks({account, urls, joint_accounts}) {
    function handleImport(e, aid) {
        e.preventDefault()
        const frm = document.querySelector('#formImportData')
        frm.src.value = aid
        frm.monzo.click()
    }

    return h('div', join(' | ', [
        [h('a', {href: urlqs(urls.transaction_edit, {dest: account.aid})}, 'Add'),
         ' (', h('a', {href: urlqs(urls.transaction_edit, {dest: account.aid, split:1})}, 'split'), ')'],
        (account.aid in joint_accounts) &&
            h('a', {href: urlqs(urls.transaction_edit, {dest: account.aid+'.joint'})}, 'Joint'),
        [h('a', {href: '#import', onClick: (e) => handleImport(e, account.aid)}, 'Import'),
        ' (', h('a', {href: '#import', onClick: (e) => handleImport(e, account.aid + '.joint')}, 'joint'), ')'],
    ]))
}

function TransactionList({account, transactions, amap, urls}) {
    const ispos = 'qa'.includes(account.type)

    function fmtAmount(acc, amnt) {
        if ((acc != account.aid) || (ispos ^ (amnt > 0))) {
            return h('span', amnt.toFixed(2))
        } else {
            return h('span.good-amount', amnt.toFixed(2))
        }
    }

    function gotoTransaction(e) {
       const target = e.target.closest('[data-href]')
       window.location.href = target.dataset.href
    }

    function Transaction(it) {
        const turl = urlqs(urls.transaction_edit, {tid: it.tid, dest: account.aid})
        return h(
            'div.card.transaction-item',
            h('table', {id: 't-' + it.tid, onClick: gotoTransaction, 'data-href': turl}, h('tbody',
                it.desc && h('tr', {'class': classNames({'transaction-header': it.split})}, h('td', {colspan: 2}, it.desc)),
                it.split
                    ? it.ops.map(([op_acc, op_amnt, op_cur]) => (
                        h('tr',
                            h('td', amap[op_acc].full_name),
                            h('td.tright', fmtAmount(op_acc, op_amnt), nbsp, h('span.cur', op_cur))
                        )
                    ))
                    : h('tr',
                        h('td', amap[it.src].full_name),
                        h('td.tright', fmtAmount(account.aid, it.amount), nbsp, h('span.cur', it.cur))
                    )
            ))
         )
    }

    const head = transactions.slice(0, 10)
    const tail = transactions.slice(10)
    const showTail = useSignal(false)

    useEffect(() => {requestIdleCallback(() => {showTail.value = true})}, [])

    return h('v-stack.gap-xl',
        head.map(([gdt, tlist]) => h('div',
            h('div.transaction-date', gdt),
            h('v-stack', tlist.map(Transaction))
        )),
        showTail.value && tail.map(([gdt, tlist]) => h('div',
            h('div.transaction-date', gdt),
            h('v-stack', tlist.map(Transaction))
        )),
    )
}

function AccountBody(config) {
    return [
        h('hr'),
        h(AccountLinks, config),
        h('v-gap.gap-l'),
        h(TransactionList, config),
    ]
}

function Toast({messages}) {
    return messages?.map((it) => h('div.flash', it))
}

function AccountView(config) {
    const {account, accounts, urls} = config;
    return [
        account
            ? [h(AccountHeader, config), h('v-gap'), h(Toast, config), h(AccountStatus, config)]
            : h('a', {href: urls.settings}, 'Settings'),
        !!accounts.length && h(SubAccounts, config),
        account && h(AccountBody, config),
    ]
}

registerPreactData(AccountView)

export {initPreactData}
