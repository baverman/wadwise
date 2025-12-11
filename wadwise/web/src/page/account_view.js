import { render } from 'preact'
import { useEffect } from 'preact/hooks'
import { useSignal } from '@preact/signals'

import { preventDefault, urlqs, join } from '../utils.js'
import { hh as h, nbsp } from '../html.js'
import { input, card, delim, curSpan, vstack, vcard, nav } from '../components.js'
import * as icons from '../icons.js'

const { div, span, ul, li, a, nobr, form } = h

const intlFmt = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2 })

function AccountHeader({ account, urls, amap, today_str, today_dsp }) {
    function dateChanged(e) {
        const params = new URLSearchParams(window.location.search)
        params.set('today', e.currentTarget.value)
        window.location.search = params
    }

    return [
        div['flex-1 breadcrumbs text-sm'](
            ul(
                ...account.parents.map((p) =>
                    li(a({ href: urlqs(urls.account_view, { aid: p }) }, amap[p].name)),
                ),
                li(a({ href: urlqs(urls.account_edit, { aid: account.aid }) }, account.name)),
            ),
        ),
        div['flex-none text-sm'](
            input.month['#dateSelector.size-0 opacity-0']({
                value: today_str,
                onInput: dateChanged,
            }),
            h.a(
                { href: '#date', onClick: preventDefault(() => window.dateSelector.showPicker()) },
                today_dsp,
            ),
        ),
    ]
}

function fmtNumber(value) {
    const parts = intlFmt.format(value).split(',')
    return span['tabular-nums tracking-tighter'](join(delim, parts))
}

function totalsRows(accCur, total, children, props) {
    const result = []
    let first = true
    for (const cur of accCur) {
        if (total[cur]) {
            result.push([
                first && children,
                div['col-2 justify-self-end'](fmtNumber(total[cur]), nbsp, curSpan(cur)),
            ])
            first = false
        }
    }

    if (!result.length && props?.showZero) {
        result.push(children)
    }
    return div['grid grid-cols-2 w-full'](props?.tprops, result)
}

function separateOnMultiCurs(cur_list, ...children) {
    if (cur_list.length > 1) {
        return vstack['gap-2'](children)
    } else {
        return children
    }
}

function AccountStatus({ account, balance, accCur }) {
    const open = useSignal(account.is_sheet && accCur.full.length == 1)
    if (account.is_sheet) {
        const cursWithMovements = accCur.full.filter(
            (cur) => balance.month_debit[cur] || balance.month_credit[cur],
        )
        const hasDetails = cursWithMovements.length > 0
        const hasBalance = accCur.full.length > 0

        return (hasBalance || hasDetails) && card(
            separateOnMultiCurs(
                accCur.full,
                totalsRows(
                    accCur.total,
                    balance.current_total,
                    'Balance' + (hasDetails && !open.value ? ' [+]' : ''),
                    { tprops: { onClick: () => (open.value = true) } },
                ),
                open.value &&
                    hasDetails && [
                        totalsRows(cursWithMovements, balance.prev_total, 'Month start'),
                        totalsRows(cursWithMovements, balance.month_debit, 'In'),
                        totalsRows(cursWithMovements, balance.month_credit, 'Out'),
                    ],
            ),
        )
    } else {
        return (
            !!Object.keys(accCur.total).length &&
            card(totalsRows(accCur.total, balance.month_total, 'This month'))
        )
    }
}

function SubAccounts({ accCur, accounts, accounts_totals, urls, today_str }) {
    return vcard['gap-2'](
        accounts.map((it) =>
            totalsRows(
                accCur.total,
                accounts_totals[it.aid],
                h.a({ href: urlqs(urls.account_view, { aid: it.aid, today: today_str }) }, it.name),
                { showZero: true },
            ),
        ),
    )
}

function AccountLinks({ account, urls, jointAccounts }) {
    const jaid = account.aid + '.joint'

    function handleImport(e, aid) {
        e.preventDefault()
        window.formImportData.src.value = aid
        window.formImportData.monzo.click()
    }

    return [
        li(div['h-0']()),
        li(a({ href: urlqs(urls.transaction_edit, { dest: account.aid }) }, 'Add transaction')),
        li(a({ href: urlqs(urls.transaction_edit, { dest: account.aid, split: 1 }) }, 'Add Split')),
        account.aid in jointAccounts &&
            li(a({ href: urlqs(urls.transaction_edit, { dest: jaid }) }, 'Add Joint')),
        li(div['h-0']()),
        li(a({ href: '#import', onClick: (e) => handleImport(e, account.aid) }, 'Import')),
        account.aid in jointAccounts &&
            li(a({ href: '#import', onClick: (e) => handleImport(e, jaid) }, 'Import Joint')),
    ]
}

function TransactionList({ account, transactions, amap, urls }) {
    const ispos = 'qa'.includes(account.type)

    function fmtAmount(acc, amnt) {
        if (acc != account.aid || ispos ^ (amnt > 0)) {
            return span(amnt.toFixed(2))
        } else {
            return span['text-emerald-700 font-medium'](amnt.toFixed(2))
        }
    }

    function gotoTransaction(e) {
        const target = e.target.closest('[data-href]')
        window.location.href = target.dataset.href
    }

    function Transaction(it) {
        const turl = urlqs(urls.transaction_edit, { tid: it.tid, dest: account.aid })
        return card['grid grid-cols-2'](
            { id: 't-' + it.tid, onClick: gotoTransaction, 'data-href': turl },
            it.desc &&
                div['col-span-full'](
                    { class: { 'border-b-1 border-gray-300': it.split } },
                    it.desc,
                ),
            it.split
                ? it.ops.map(([op_acc, op_amnt, op_cur, op_main]) => [
                      div['text-wrap tracking-tight'](
                          { class: { 'text-slate-500': !op_main } },
                          amap[op_acc].full_name,
                      ),
                      div['col-2 justify-self-end'](
                          { class: { 'text-slate-500': !op_main } },
                          nobr(fmtAmount(op_acc, op_amnt), nbsp, curSpan(op_cur)),
                      ),
                  ])
                : [
                      div['text-wrap tracking-tight'](amap[it.src].full_name),
                      div['col-2 justify-self-end'](
                          nobr(fmtAmount(account.aid, it.amount), nbsp, curSpan(it.cur)),
                      ),
                  ],
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

    const tDate = div['small-caps text-sm text-slate-600 text-upper mb-1']

    return [head, tail].map((chunk) =>
        chunk.value.map(([gdt, tlist]) => div(tDate(gdt), vstack['gap-2'](tlist.map(Transaction)))),
    )
}

function AccountBody(config) {
    return [div['h-0'](), vstack['gap-4'](h(TransactionList, config))]
}

function Toast({ messages }) {
    return messages?.map((it) =>
        div['bg-sky-100 p-2 rounded-box text-sm shadow-sm/20 text-slate-800']({
            dangerouslySetInnerHTML: { __html: it },
        }),
    )
}

export function AccountView(config) {
    const { account, accounts, urls } = config
    return [
        account &&
            form['#formImportData.hidden [method=POST]'](
                { action: urls.import_monzo, enctype: 'multipart/form-data' },
                input.text({ name: 'src' }),
                input.file({
                    name: 'monzo',
                    accept: '.csv',
                    onInput: (e) => e.target.value && e.target.form.submit(),
                }),
            ),
        vstack['gap-2'](
            nav['py-1 pl-1 pr-2'](
                div['flex-none pr-1'](
                    div['dropdown'](
                        div['btn btn-ghost px-1 py-0 [role=button][tabindex=0]'](icons.burger2),
                        ul[
                            'menu dropdown-content bg-base-200 rounded-box z-1 -ml-1 mt-2 w-52 p-2 shadow-sm/20 [tabindex=-1]'
                        ](
                            account && li(a({ href: urls.account_view }, 'Home')),
                            li(a({ href: urls.settings }, 'Settings')),
                            account && !account.is_placeholder && h(AccountLinks, config),
                        ),
                    ),
                ),
                !account && div['flex-1'](span['text-sm font-medium']('Home')),
                account && h(AccountHeader, config),
            ),
            account && [h(Toast, config), h(AccountStatus, config)],
            !!accounts.length && h(SubAccounts, config),
            account && h(AccountBody, config),
        ),
    ]
}

render(h(AccountView, window.appData), document.querySelector('.content'))
