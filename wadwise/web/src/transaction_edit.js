import { useSignal, batch, useComputed, signal } from '@preact/signals'
import {
    registerPreactData,
    initPreactData,
    negInput,
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

function SrcDest({ form, accountTitle, curList }) {
    const current = useSignal(null)
    const target = useSignal(0)
    const diff = useComputed(() => current.value - target.value)
    const cur = useSignal(null)

    async function fetchBalance(e) {
        const form = e.target.closest('form')
        const icur = form.cur.value
        const resp = await fetch(
            urlqs('/api/balance', { date: form.date.value, aid: form.src.value }),
        )
        const balance = (await resp.json()).result[icur] || 0

        batch(() => {
            cur.value = icur
            current.value = balance
        })
    }

    const amountOpts = {
        type: 'text',
        placeholder: 'amount',
        inputmode: 'decimal',
        autofocus: true,
        tabindex: 1,
        size: '8em',
        autocomplete: 'off',
    }

    return [
        p('From:', br(), AccountSelector({ name: 'src', value: form.src })),
        p('To: ', accountTitle),
        p(
            current.value === null && [
                input({ ...amountOpts, name: 'amount', onInput: negInput, value: form.amount }),
                ' ',
                h(CurSelect, { curList, name: 'cur', value: form.cur }),
                ' ',
                button({ onClick: fetchBalance }, 'Target'),
            ],
            current.value !== null && [
                input.hidden({ name: 'amount', value: diff.value.toFixed(2) }),
                input.hidden({ name: 'cur', value: cur }),
                span(current.value.toFixed(2)),
                diff.value > 0 ? ' - ' : ' + ',
                span(Math.abs(diff.value).toFixed(2)),
                ' = ',
                input({
                    ...amountOpts,
                    value: target,
                    onInput: (e) => {
                        negInput(e)
                        target.value = e.currentTarget.value
                    },
                }),
                nbsp,
                span.cur(cur),
            ],
        ),
    ]
}

function Split({ form, curList }) {
    const ops = useSignal(form.ops.map((it) => it.map(signal)))
    const sameCur = useComputed(() => new Set(ops.value.map((it) => it[2].value)).size < 2)
    const total = useComputed(() =>
        ops.value.reduce((acc, val) => acc + parseFloat(val[1].value || 0), 0),
    )

    function add() {
        pushSignal(ops, ['', 0, curList[0]].map(signal))
    }

    function fixAmount(op) {
        op[1].value = (parseFloat(op[1].value || 0) - total.value).toFixed(2)
    }

    return [
        ops.value.map((op, idx) =>
            p(
                AccountSelector({ name: 'acc', ...fieldModel(op[0]) }),
                ' ',
                nobr(
                    join(' ', [
                        input.text({
                            placeholder: 'amount',
                            inputmode: 'decimal',
                            name: 'amount',
                            size: '6em',
                            autocomplete: 'off',
                            value: op[1],
                            onInput: (e) => {
                                negInput(e)
                                op[1].value = e.currentTarget.value
                            },
                        }),
                        h(CurSelect, { curList, name: 'cur', ...fieldModel(op[2]) }),
                        sameCur.value && button({ onClick: () => fixAmount(op) }, 'Fix'),
                        button({ onClick: () => deleteIdxSignal(ops, idx) }, '\u2716'),
                    ]),
                ),
            ),
        ),
        p(
            button({ onClick: add }, 'Add'),
            sameCur.value && [nbsp, 'Total: ', nbsp, span(total.value.toFixed(2))],
        ),
    ]
}

function AccountEdit(config) {
    const { form, dateStr, timeStr, split } = config
    return [
        h(split ? Split : SrcDest, config),
        p(textarea({ placeholder: 'description', name: 'desc', value: form.desc })),
        p(
            input.date({ name: 'date', value: dateStr }),
            input.hidden({ name: 'date_time', value: timeStr }),
        ),
        p(
            join(
                ' ',
                submit.primary('Save'),
                form.tid && [
                    submit.danger({ name: 'action', value: 'delete' }, 'Delete'),
                    submit.secondary({ name: 'action', value: 'copy-now' }, 'Copy Now'),
                    submit.secondary({ name: 'action', value: 'copy' }, 'Copy'),
                ],
            ),
        ),
    ]
}

registerPreactData(AccountEdit)

export { initPreactData }
