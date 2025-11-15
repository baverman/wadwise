import classNames from 'classnames'
import { useState } from 'preact/hooks'
import { signal, computed, batch } from '@preact/signals'
import {
    hh as h,
    initPreactData,
    idify,
    fieldModel,
    preventDefault,
    node2component,
    registerPreactData,
} from './utils.js'

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

function AccountSelector(props) {
    const [open, setOpen] = useState(false)
    const handleSelectFocus = () => setOpen(true)
    return h(
        'select',
        { ...props, onFocus: handleSelectFocus },
        open || props.value.value ? accountSelector.props.children : h('option', '---'),
    )
}

function Transaction({ trn }) {
    const [state_value, state_title] = trn.state.value ? [null, 'Include'] : ['seen', 'Exclude']

    return h(
        'div',
        { class: classNames({ card: true, ignored: trn.state.value, ok: !trn.state.value && trn.dest.value }) },
        h(
            'form-aligned',
            h('div.label', trn.type),
            h('div.date.aligned-right', trn.date_str),

            h('div.label', trn.name),
            h('div.aligned-right', h('span', trn.amount.toFixed(2)), '\xA0', h('span.cur', trn.cur)),

            h('span.aligned-full', trn.category),
            h(AccountSelector, { class: 'aligned-full', name: 'dest', ...fieldModel(trn.dest) }),
            h('input.aligned-full', { type: 'text', name: 'desc', ...fieldModel(trn.desc) }),
            h(
                'div.aligned-full',
                h(
                    'button.pure-button.button-secondary',
                    { onClick: preventDefault(() => setSimilar(trn)), disabled: !trn.dest.value },
                    'Set similar',
                ),
                ' ',
                h(
                    'button.pure-button.button-secondary',
                    { onClick: preventDefault(() => (trn.state.value = state_value)) },
                    state_title,
                ),
            ),
        ),
    )
}

function TransactionList() {
    return transactions.value.map((trn) => h(Transaction, { trn, key: trn.id }))
}

function ImportForm({ src, name, balance }) {
    return [
        h('input', { name: 'src', value: src, hidden: true }),
        h('input', { name: 'transactions', value: transactionsStr, hidden: true }),
        h(
            'p',
            'Account: ',
            name,
            h('br'),
            'Balance: ',
            `${balance.GBP.toFixed(2)} + ${total.value.toFixed(2)} = ${(balance.GBP + total.value).toFixed(2)}`,
        ),
        h('p', h('button.pure-button.pure-button-primary', { type: 'submit', disabled: !submit_ok.value }, 'Import')),
        h('v-stack', h(TransactionList)),
    ]
}

const accountSelector = node2component(document.querySelector('#accountSelector').content.querySelector('select'))
registerPreactData(ImportForm)

export { init, initPreactData }
