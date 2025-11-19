import { useSignal, batch, useSignalEffect } from '@preact/signals'
import { hh, wrapComponent } from './html.js'
import { node2component, negInput } from './utils.js'

function buttonSet(el) {
    return {
        primary: el['pure-button-primary'],
        secondary: el['button-secondary'],
        danger: el['button-error'],
    }
}

let accountSelectorOptions = [hh.option('Error')]

;(function () {
    const tpl = document.querySelector('#accountSelector')
    if (tpl) {
        accountSelectorOptions = node2component(tpl.content.querySelector('select')).props.children
    }
})()

function _AccountSelector({ lazy, ...props }) {
    const open = useSignal(false)
    if (lazy) {
        return hh.select(
            { ...props, onFocus: () => (open.value = true) },
            open.value || props.value.value ? accountSelectorOptions : hh.option('---'),
        )
    } else {
        return hh.select(props, accountSelectorOptions)
    }
}

function NumericInput({ value, ...props }) {
    const state = useSignal(value.peek())
    const isExternal = useSignal(true)

    useSignalEffect(() => {
        const v = value.value
        if (isExternal.peek()) {
            state.value = String(v)
        }
    })

    function handle(e) {
        negInput(e)
        batch(() => {
            isExternal.value = false
            const numValue = parseFloat((state.value = e.currentTarget.value))
            value.value = numValue || 0
        })
        setTimeout(() => (isExternal.value = true), 0)
    }

    return input.text({
        inputmode: 'decimal',
        autocomplete: 'off',
        ...props,
        value: state,
        onInput: handle,
    })
}

const btn = hh.button['pure-button']

export const AccountSelector = wrapComponent(_AccountSelector)
export const button = btn['[type=button]'].$(buttonSet)
export const submit = btn['[type=submit]'].$(buttonSet)
export const vstack = hh['v-stack']
export const vgap = hh['v-gap']
export const input = hh['input'].$((el) => ({
    text: el['[type=text]'],
    hidden: el['[type=hidden]'],
    date: el['[type=date]'],
    month: el['[type=month]'],
    file: el['[type=file]'],
    number: wrapComponent(NumericInput),
}))
