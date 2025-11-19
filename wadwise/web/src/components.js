import { useSignal } from '@preact/signals'
import { hh, wrapComponent } from './html.js'
import { node2component } from './utils.js'

function buttonSet(el) {
    return {
        primary: el['pure-button-primary'],
        secondary: el['button-secondary'],
        danger: el['button-error'],
    }
}

const btn = hh.button['pure-button']

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
}))

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

export const AccountSelector = wrapComponent(_AccountSelector)
