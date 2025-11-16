import classNames from 'classnames'
import { useEffect } from 'preact/hooks'
import { useSignal } from '@preact/signals'

import { registerPreactData, preventDefault, initPreactData, urlqs, join, wrap } from './utils.js'
import { hh as h, nbsp } from './html.js'

const { div, input, span, table, tbody, tr, td } = h

const dqs = document.querySelector.bind(document)
const intlFmt = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2 })

function AccountHeader({ account, urls, amap, today_str, today_dsp }) {
    function dateChanged(e) {
        const params = new URLSearchParams(window.location.search)
        params.set('today', e.currentTarget.value)
        window.location.search = params
    }

    return [
        h['form-aligned'](
            div.label(
                join(':', [
                    h.a({ href: urlqs(urls.account_view) }, 'Home'),
                    ...account.parents.map((p) =>
                        h.a({ href: urlqs(urls.account_view, { aid: p }) }, amap[p].name),
                    ),
                    h.a({ href: urlqs(urls.account_edit, { aid: account.aid }) }, account.name),
                ]),
            ),
            div['aligned-right'](
                input.opaque({
                    id: 'dateSelector',
                    type: 'month',
                    value: today_str,
                    onInput: dateChanged,
                }),
                h.a(
                    {
                        href: '#date',
                        onClick: preventDefault(() => dqs('#dateSelector').showPicker()),
                    },
                    today_dsp,
                ),
            ),
        ),
    ]
}

const delim = span.delim()

function fmtNumber(value) {
    const parts = intlFmt.format(value).split(',')
    return join(delim, parts)
}

function totalsRows(cur_list, total, children, props) {
    const result = []
    let first = true
    for (const cur of cur_list) {
        if (total[cur]) {
            result.push(
                tr(
                    td(first && children),
                    td.tright.amount(fmtNumber(total[cur]), nbsp, span.cur(cur)),
                ),
            )
            first = false
        }
    }

    if (!result.length && props?.showZero) {
        result.push(tr(td(children)))
    }
    return table['w-100'](props?.tprops, tbody(result))
}

function separateOnMultiCurs(cur_list, ...children) {
    if (cur_list.length > 1) {
        return h['v-stack'](children)
    } else {
        return children
    }
}

function AccountStatus({ account, balance, cur_list }) {
    const open = useSignal(account.is_sheet && cur_list.full.length == 1)
    if (account.is_sheet) {
        return separateOnMultiCurs(
            cur_list.full,
            totalsRows(
                cur_list.total,
                balance.current_total,
                'Balance' + (open.value ? '' : ' [+]'),
                { tprops: { onClick: () => (open.value = true) } },
            ),
            open.value && [
                totalsRows(cur_list.full, balance.prev_total, 'Month start'),
                totalsRows(cur_list.full, balance.month_debit, 'In'),
                totalsRows(cur_list.full, balance.month_credit, 'Out'),
            ],
        )
    } else {
        return totalsRows(cur_list.total, balance.month_total, 'This month')
    }
}

function SubAccounts({ cur_list, accounts, accounts_totals, urls, today_str }) {
    return [
        h.hr(),
        separateOnMultiCurs(
            cur_list.total,
            accounts.map((it) =>
                totalsRows(
                    cur_list.total,
                    accounts_totals[it.aid],
                    h.a(
                        { href: urlqs(urls.account_view, { aid: it.aid, today: today_str }) },
                        it.name,
                    ),
                    { showZero: true },
                ),
            ),
        ),
    ]
}

function AccountLinks({ account, urls, joint_accounts }) {
    const jaid = account.aid + '.joint'

    function handleImport(e, aid) {
        e.preventDefault()
        const frm = document.querySelector('#formImportData')
        frm.src.value = aid
        frm.monzo.click()
    }

    return div(
        join(' | ', [
            [
                h.a({ href: urlqs(urls.transaction_edit, { dest: account.aid }) }, 'Add'),
                wrap(
                    ' (^)',
                    join(', ', [
                        h.a(
                            { href: urlqs(urls.transaction_edit, { dest: account.aid, split: 1 }) },
                            'split',
                        ),
                        account.aid in joint_accounts &&
                            h.a({ href: urlqs(urls.transaction_edit, { dest: jaid }) }, 'joint'),
                    ]),
                ),
            ],
            [
                h.a({ href: '#import', onClick: (e) => handleImport(e, account.aid) }, 'Import'),
                wrap(' (^)', [
                    account.aid in joint_accounts &&
                        h.a({ href: '#import', onClick: (e) => handleImport(e, jaid) }, 'joint'),
                ]),
            ],
        ]),
    )
}

function TransactionList({ account, transactions, amap, urls }) {
    const ispos = 'qa'.includes(account.type)

    function fmtAmount(acc, amnt) {
        if (acc != account.aid || ispos ^ (amnt > 0)) {
            return span(amnt.toFixed(2))
        } else {
            return span['good-amount'](amnt.toFixed(2))
        }
    }

    function gotoTransaction(e) {
        const target = e.target.closest('[data-href]')
        window.location.href = target.dataset.href
    }

    function Transaction(it) {
        const turl = urlqs(urls.transaction_edit, { tid: it.tid, dest: account.aid })
        return div.card['transaction-item'](
            table(
                { id: 't-' + it.tid, onClick: gotoTransaction, 'data-href': turl },
                tbody(
                    it.desc &&
                        tr(
                            { class: classNames({ 'transaction-header': it.split }) },
                            td({ colspan: 2 }, it.desc),
                        ),
                    it.split
                        ? it.ops.map(([op_acc, op_amnt, op_cur]) =>
                              tr(
                                  td(amap[op_acc].full_name),
                                  td.tright(fmtAmount(op_acc, op_amnt), nbsp, span.cur(op_cur)),
                              ),
                          )
                        : tr(
                              td(amap[it.src].full_name),
                              td.tright(fmtAmount(account.aid, it.amount), nbsp, span.cur(it.cur)),
                          ),
                ),
            ),
        )
    }

    const loadSize = 10
    const head = useSignal(transactions.slice(0, loadSize))
    const tail = useSignal([])

    useEffect(() => {
        requestIdleCallback(() => {
            tail.value = transactions.slice(loadSize)
        })
    }, [])

    return h['v-stack.gap-xl'](
        [head, tail].map((chunk) =>
            chunk.value.map(([gdt, tlist]) =>
                div(div['transaction-date'](gdt), h['v-stack'](tlist.map(Transaction))),
            ),
        ),
    )
}

function AccountBody(config) {
    return [h.hr(), h(AccountLinks, config), h['v-gap.gap-l'](), h(TransactionList, config)]
}

function Toast({ messages }) {
    return messages?.map((it) => div.flash(it))
}

function AccountView(config) {
    const { account, accounts, urls } = config
    return [
        account
            ? [h(AccountHeader, config), h['v-gap'](), h(Toast, config), h(AccountStatus, config)]
            : h.a({ href: urls.settings }, 'Settings'),
        !!accounts.length && h(SubAccounts, config),
        account && h(AccountBody, config),
    ]
}

registerPreactData(AccountView)

export { initPreactData }
