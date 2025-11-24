import { useSignal, batch, useComputed, signal, useSignalEffect } from '@preact/signals'
import { useMemo } from 'preact/hooks'
import {
    registerPreactData,
    initPreactData,
    join,
    urlqs,
    fieldModel,
    pushSignal,
    deleteIdxSignal,
} from './utils.js'
import { hh as h, nbsp } from './html.js'
import { button, submit, input, AccountSelector } from './components.js'

const { select, p, br, option, textarea, span, nobr } = h

function CurSelect(props) {
    const { curList, ...rest } = props
    return select(
        rest,
        curList.map((it) => option(it)),
    )
}

// function op2(src, dest, amount, cur) {
//     return [
//         [src, -amount, cur],
//         [dest, amount, cur]
//     ]
// }

function SrcDest({ form, accountTitle, curList, isError }) {
    const src = useSignal(form.src)
    const amount = useSignal(form.amount)
    const current = useSignal(null)
    const target = useSignal(0)
    const diff = useComputed(() => current.value - target.value)
    const cur = useSignal(form.cur)
    const default_ops = useComputed(() =>
        JSON.stringify({ simple: [src.value, form.dest, amount.value, cur.value] }),
    )
    const target_ops = useComputed(() =>
        JSON.stringify({ simple: [src.value, form.dest, diff.value, cur.value] }),
    )

    useSignalEffect(() => {
        isError.value = src.value == form.dest
    })

    async function fetchBalance(e) {
        const form = e.target.closest('form')
        const resp = await fetch(
            urlqs('/api/balance', { date: form.date.value, aid: form.src.value }),
        )
        const balance = (await resp.json()).result[cur.value] || 0

        batch(() => {
            current.value = balance
        })
    }

    const amountOpts = { placeholder: 'amount', autofocus: true, tabindex: 1, size: '8em' }

    return [
        p('From:', br(), AccountSelector({ name: 'src', ...fieldModel(src) })),
        p('To: ', accountTitle),
        p(
            current.value === null && [
                input.number({ ...amountOpts, value: amount }),
                ' ',
                h(CurSelect, { curList, ...fieldModel(cur) }),
                ' ',
                button({ onClick: fetchBalance }, 'Target'),
                input.hidden({ name: 'ops', value: default_ops }),
            ],
            current.value !== null && [
                span(current.value.toFixed(2)),
                diff.value > 0 ? ' - ' : ' + ',
                span(Math.abs(diff.value).toFixed(2)),
                ' = ',
                input.number({ ...amountOpts, value: target }),
                nbsp,
                span.cur(cur),
                input.hidden({ name: 'ops', value: target_ops }),
            ],
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

    return [
        ops.value.map((op, idx) =>
            p(
                AccountSelector({ ...fieldModel(op[0]) }),
                ' ',
                nobr(
                    join(' ', [
                        input.number({ placeholder: 'amount', size: '6em', value: op[1] }),
                        h(CurSelect, { curList, ...fieldModel(op[2]) }),
                        sameCur.value && button({ onClick: () => fixAmount(op) }, 'Fix'),
                        button({ onClick: () => deleteIdxSignal(ops, idx) }, '\u2716'),
                    ]),
                ),
            ),
        ),
        p(
            button({ onClick: add }, 'Add'),
            sameCur.value && [nbsp, 'Total: ', nbsp, span(total.value.toFixed(2))],
            input.hidden({ name: 'ops', value: raw_ops }),
        ),
    ]
}

function AccountEdit(config) {
    const { form, dateStr, timeStr, split } = config
    const isError = useSignal(null)
    const btnOpts = { disabled: isError.value }
    return [
        h(split ? Split : SrcDest, { ...config, isError }),
        p(textarea({ placeholder: 'description', name: 'desc', defaultValue: form.desc })),
        p(
            input.date({ name: 'date', defaultValue: dateStr }),
            input.hidden({ name: 'date_time', defaultValue: timeStr }),
        ),
        p(
            join(
                ' ',
                submit.primary({ ...btnOpts }, 'Save'),
                form.tid && [
                    submit.danger({ ...btnOpts, name: 'action', value: 'delete' }, 'Delete'),
                    submit.secondary({ ...btnOpts, name: 'action', value: 'copy-now' }, 'Copy Now'),
                    submit.secondary({ ...btnOpts, name: 'action', value: 'copy' }, 'Copy'),
                ],
            ),
        ),
    ]
}

registerPreactData(AccountEdit)

export { initPreactData }
