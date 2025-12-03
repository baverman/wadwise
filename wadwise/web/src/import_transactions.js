import { render } from 'preact'
import { signal, computed, batch } from '@preact/signals'
import { idify, fieldModel } from './utils.js'
import { hh as h, nbsp } from './html.js'
import { input, submit, button, card, curSpan, vstack } from './components.js'
import { AccountSelector } from './account_selector.js'

const { div, span, p, nobr, form } = h

function wrapItem(item) {
    return { ...item, state: signal(item.state), dest: signal(item.dest), desc: signal(item.desc) }
}

const transactions = signal([])
const transactionsStr = computed(() => JSON.stringify(transactions.value))

const submit_ok = computed(() => {
    return !transactions.value.some((it) => !it.state.value && !it.dest.value)
})

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

    return card(
        {
            class: {
                'bg-slate-100': trn.state.value,
                'bg-green-100': !trn.state.value && trn.dest.value,
            },
        },
        div['grid grid-cols-2 w-full gap-y-2'](
            div(trn.type),
            div['text-right'](nobr(trn.date_str)),

            div(trn.name),
            div['text-right'](nobr(span(trn.amount.toFixed(2)), nbsp, curSpan(trn.cur))),

            span['col-span-full'](trn.category),
            AccountSelector['col-span-full w-full appearance-none']({
                lazy: true,
                name: 'dest',
                ...fieldModel(trn.dest),
            }),
            input.text['col-span-full w-full']({ name: 'desc', ...fieldModel(trn.desc) }),
            div['col-span-full'](
                button.secondary['btn-sm'](
                    { onClick: () => setSimilar(trn), disabled: !trn.dest.value },
                    'Set similar',
                ),
                ' ',
                button.secondary['btn-sm'](
                    { onClick: () => (trn.state.value = state_value) },
                    state_title,
                ),
            ),
        ),
    )
}

function TransactionList() {
    return transactions.value.map((trn) => h(Transaction, { trn, key: trn.id }))
}

function ImportForm({ src, name, balance, urls }) {
    return form(
        { method: 'POST', action: urls.import_transactions_apply },
        input.hidden({ name: 'src', value: src }),
        input.hidden({ name: 'transactions', value: transactionsStr }),
        vstack['gap-2'](
            card(
                p(
                    'Account: ',
                    name,
                    h.br(),
                    'Balance: ',
                    `${balance.GBP.toFixed(2)} + ${total.value.toFixed(2)} = ${(balance.GBP + total.value).toFixed(2)}`,
                ),
                p(submit['btn-sm'].primary({ disabled: !submit_ok.value }, 'Import')),
            ),
            h(TransactionList),
        ),
    )
}

transactions.value = idify(window.appData.transactions).map(wrapItem)
render(h(ImportForm, window.appData), document.querySelector('.content'))
