import { signal, computed, batch } from '@preact/signals'
import { initPreactData, idify, fieldModel, registerPreactData } from './utils.js'
import { hh as h, nbsp } from './html.js'
import { vstack, button, submit, input, AccountSelector } from './components.js'

const { div, span, p, nobr } = h

function wrapItem(item) {
    return { ...item, state: signal(item.state), dest: signal(item.dest), desc: signal(item.desc) }
}

const transactions = signal([])
const transactionsStr = computed(() => JSON.stringify(transactions.value))

const submit_ok = computed(() => {
    return !transactions.value.some((it) => !it.state.value && !it.dest.value)
})

function init(data) {
    transactions.value = idify(data).map(wrapItem)
}

const total = computed(() => {
    let result = 0
    for (const it of transactions.value) {
        if (!it.state.value) {
            result += it.amount
        }
    }
    return result
})

function setSimilar(other) {
    batch(() => {
        for (const tr of transactions.value) {
            if (tr === other) {
                continue
            }
            if (tr.key && tr.key == other.key) {
                tr.dest.value = other.dest.value
                tr.desc.value = other.desc.value
            }
        }
    })
}

function Transaction({ trn }) {
    const [state_value, state_title] = trn.state.value ? [null, 'Include'] : ['seen', 'Exclude']

    return div.card(
        { class: { ignored: trn.state.value, ok: !trn.state.value && trn.dest.value } },
        h['form-aligned'](
            div.label(trn.type),
            div['aligned-right'](nobr(trn.date_str)),

            div.label(trn.name),
            div['aligned-right'](nobr(span(trn.amount.toFixed(2)), nbsp, span.cur(trn.cur))),

            span['aligned-full'](trn.category),
            AccountSelector['aligned-full']({ lazy: true, name: 'dest', ...fieldModel(trn.dest) }),
            input.text['aligned-full']({ name: 'desc', ...fieldModel(trn.desc) }),
            div['aligned-full'](
                button.secondary(
                    { onClick: () => setSimilar(trn), disabled: !trn.dest.value },
                    'Set similar',
                ),
                ' ',
                button.secondary({ onClick: () => (trn.state.value = state_value) }, state_title),
            ),
        ),
    )
}

function TransactionList() {
    return transactions.value.map((trn) => h(Transaction, { trn, key: trn.id }))
}

function ImportForm({ src, name, balance }) {
    return [
        input.hidden({ name: 'src', value: src }),
        input.hidden({ name: 'transactions', value: transactionsStr }),
        p(
            'Account: ',
            name,
            h.br(),
            'Balance: ',
            `${balance.GBP.toFixed(2)} + ${total.value.toFixed(2)} = ${(balance.GBP + total.value).toFixed(2)}`,
        ),
        p(submit.primary({ disabled: !submit_ok.value }, 'Import')),
        vstack(h(TransactionList)),
    ]
}

registerPreactData(ImportForm)

export { init, initPreactData }
