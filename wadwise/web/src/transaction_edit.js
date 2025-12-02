import { render } from 'preact'
import { useSignal, useComputed, signal, useSignalEffect } from '@preact/signals'
import { useMemo } from 'preact/hooks'
import { urlqs, fieldModel, pushSignal, deleteIdxSignal } from './utils.js'
import { hh as h, nbsp, wrapComponent } from './html.js'
import {
    input,
    AccountSelector,
    select,
    button,
    submit,
    textarea,
    nav,
    vcard,
} from './components.js'
import * as icons from './icons.js'

const { p, option, span, a, div } = h
const mlink = a['tab [role=tab]']
const flabel = h.label['floating-label']

const CurSelect = wrapComponent((props) => {
    const { curList, ...rest } = props
    return select(
        rest,
        curList.map((it) => option(it)),
    )
})

function op2(src, dest, amount, cur, isMain) {
    return [
        [src, -amount, cur, isMain ?? false],
        [dest, amount, cur, isMain ?? false],
    ]
}

function SrcDest({ form, accountTitle, curList, isError, defaultAccount, urls }) {
    const mode = useSignal('simple')
    const src = useSignal(form.src || defaultAccount)
    const via = useSignal(defaultAccount)
    const amount = useSignal(form.amount)
    const current = useSignal(null)
    const target = useSignal(0)
    const diff = useComputed(() => current.value - target.value)
    const cur = useSignal(form.cur)
    // const isSpecial = useComputed(() => src.value.includes('.') || form.dest.includes('.'))

    const raw_ops = useComputed(() => {
        let result = null
        const m = mode.value
        if (m == 'target') {
            result = { simple: [src.value, form.dest, diff.value, cur.value] }
        } else if (m == 'noop') {
            result = {
                ops: [
                    ...op2(form.dest, form.dest, amount.value, cur.value, true),
                    ...op2(src.value, src.value, amount.value, cur.value, false),
                ],
            }
        } else if (m == 'via') {
            result = {
                ops: [
                    ...op2(src.value, form.dest, amount.value, cur.value, true),
                    ...op2(via.value, via.value, amount.value, cur.value, false),
                ],
            }
        } else {
            result = { simple: [src.value, form.dest, amount.value, cur.value] }
        }
        return JSON.stringify(result)
    })

    useSignalEffect(() => {
        isError.value = src.value == form.dest
    })

    async function fetchBalance(e, set) {
        const form = e.target.closest('form')
        const resp = await fetch(
            urlqs('/api/balance', { date: form.date.value, aid: form.src.value }),
        )
        const balance = (await resp.json()).result[cur.value] || 0
        current.value = balance
        set()
    }

    function toggleMode(to, fn) {
        return (e) => {
            e.preventDefault()
            if (mode.value == to) {
                mode.value = 'simple'
            } else {
                if (fn) {
                    fn(e, () => (mode.value = to))
                } else {
                    mode.value = to
                }
            }
        }
    }

    const amountOpts = { placeholder: 'amount', autofocus: true, tabindex: 1, size: '8em' }
    const m = mode.value
    function tabAct(val) {
        return { class: { 'tab-active': m == val } }
    }

    return [
        nav['px-2 justify-between'](
            a(
                {
                    href: urlqs(urls.transaction_edit, {
                        tid: form.tid,
                        dest: form.dest,
                        split: 1,
                    }),
                },
                'Split',
            ),
            div['tabs tabs-box px-0'](
                mlink(
                    { ...tabAct('target'), onClick: toggleMode('target', fetchBalance) },
                    'Target',
                ),
                mlink({ ...tabAct('noop'), onClick: toggleMode('noop') }, 'No Op'),
                mlink({ ...tabAct('via'), onClick: toggleMode('via') }, 'Via'),
            ),
        ),
        div['h-2'](),
        vcard['gap-4 pt-3'](
            p(flabel(AccountSelector['w-full']({ name: 'src', ...fieldModel(src) }), span('From'))),
            m == 'via' && p(flabel(AccountSelector['w-full']({ ...fieldModel(via) }), span('Via'))),
            p(flabel(input.text['w-full [readonly]']({ defaultValue: accountTitle }), span('To'))),
            div['flex gap-2 items-center'](
                m !== 'target' && [
                    input.number['w-40 flex-1']({ ...amountOpts, value: amount }),
                    CurSelect['w-20 flex-none']({ curList, ...fieldModel(cur) }),
                ],
                m === 'target' && [
                    div['flex-1'](
                        span(current.value.toFixed(2)),
                        diff.value > 0 ? ' - ' : ' + ',
                        span(Math.abs(diff.value).toFixed(2)),
                        ' = ',
                    ),
                    div['flex-none'](
                        input.number['w-25']({ ...amountOpts, value: target }),
                        nbsp,
                        span.cur(cur),
                    ),
                ],
            ),
            input.hidden({ name: 'ops', value: raw_ops }),
        ),
    ]
}

function Split({ form, curList, isError }) {
    const ops = useSignal(useMemo(() => form.ops.map((it) => it.map(signal)), [form.ops]))
    const sameCur = useComputed(() => new Set(ops.value.map((it) => it[2].value)).size < 2)
    const total = useComputed(() => ops.value.reduce((acc, val) => acc + val[1].value, 0))
    const raw_ops = useComputed(() => JSON.stringify({ ops: ops }))

    useSignalEffect(() => (isError.value = new Set(ops.value.map((it) => it[0].value)).size < 2))

    function add() {
        pushSignal(ops, ['', 0, curList[0]].map(signal))
    }

    function fixAmount(op) {
        op[1].value = op[1].value - total.value
    }

    return vcard['gap-4'](
        ops.value.map((op, idx) =>
            div(
                AccountSelector['w-full']({ ...fieldModel(op[0]) }),
                div['h-2'](),
                div['flex gap-2'](
                    input.number['flex-auto']({ placeholder: 'amount', value: op[1] }),
                    CurSelect['w-20 flex-none']({ curList, ...fieldModel(op[2]) }),
                    sameCur.value && button['flex-none']({ onClick: () => fixAmount(op) }, 'Fix'),
                    button['flex-none']({ onClick: () => deleteIdxSignal(ops, idx) }, icons.trash),
                ),
            ),
        ),
        div['flex items-center justify-between'](
            button['flex-none']({ onClick: add }, 'Add'),
            sameCur.value && div('Total:', nbsp, span(total.value.toFixed(2))),
        ),
        input.hidden({ name: 'ops', value: raw_ops }),
    )
}

function TransactionEdit(config) {
    const { form, dateStr, timeStr, split } = config
    const isError = useSignal(null)
    const btnOpts = { disabled: isError.value }
    return h.form(
        { method: 'POST' },
        h(split ? Split : SrcDest, { ...config, isError }),
        div['h-2'](),
        vcard['gap-4'](
            p(
                textarea['w-full']({
                    placeholder: 'description',
                    name: 'desc',
                    defaultValue: form.desc,
                }),
            ),
            p(
                input.date['w-full']({ name: 'date', defaultValue: dateStr }),
                input.hidden({ name: 'date_time', defaultValue: timeStr }),
            ),
            div['!flex gap-2 [&>*]:flex-auto'](
                submit.primary({ ...btnOpts }, 'Save'),
                form.tid && [
                    submit.danger({ ...btnOpts, name: 'action', value: 'delete' }, 'Delete'),
                    submit.secondary({ ...btnOpts, name: 'action', value: 'copy-now' }, 'Copy Now'),
                    submit.secondary({ ...btnOpts, name: 'action', value: 'copy' }, 'Copy'),
                ],
            ),
        ),
    )
}

render(h(TransactionEdit, window.appData), document.querySelector('.content'))
