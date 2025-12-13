import { useEffect, useRef } from 'preact/hooks'
import { useSignal, batch, useSignalEffect } from '@preact/signals'
import { hh, wrapComponent } from './html.js'
import { negInput } from './utils.js'

function buttonSet(el) {
    return { primary: el['btn-primary'], secondary: el['btn-secondary'], danger: el['btn-warning'] }
}

export const uselect = wrapComponent((props) => {
    let { defaultValue, children, ...rest } = props
    if (defaultValue !== undefined) {
        const ref = useRef()
        useEffect(() => {
            ref.current.value = defaultValue
        }, [])
        rest.ref = ref
        rest.debugvalue = defaultValue
    }
    return select(rest, children)
})

function NumericInput({ value, ...props }) {
    const state = useSignal(value?.peek())
    const edit = useSignal(false)

    useSignalEffect(() => {
        let v = String(value.value)
        if (v == 'undefined' || v == 'null') {
            v = ''
        }
        if (!edit.value && state.peek() != v) {
            state.value = v
        }
    })

    function handle(e) {
        negInput(e)
        batch(() => {
            edit.value = true
            const numValue = parseFloat((state.value = e.currentTarget.value))
            value.value = numValue || 0
        })
    }

    return hh.input({
        type: 'text',
        inputmode: 'decimal',
        autocomplete: 'off',
        ...props,
        value: state,
        onInput: handle,
        onBlur: () => (edit.value = false),
    })
}

const btn = hh.button['btn']

export const button = btn['[type=button]'].$(buttonSet)
export const submit = btn['[type=submit]'].$(buttonSet)
export const vstack = hh.div['flex flex-col']
export const input = hh.input['input'].$((el) => ({
    text: el['[type=text]'],
    hidden: el['[type=hidden]'],
    date: el['[type=date]'],
    month: el['[type=month]'],
    file: el['[type=file]'],
    number: wrapComponent(NumericInput)['input'],
}))

export const inputns = hh.input.$((el) => ({
    text: el['[type=text]'],
    hidden: el['[type=hidden]'],
    date: el['[type=date]'],
    month: el['[type=month]'],
    file: el['[type=file]'],
    number: wrapComponent(NumericInput),
}))

export const card = hh.div['card p-2 bg-base-100 shadow-sm/20']
export const vcard = card['flex flex-col']
export const textarea = hh.textarea['textarea']
export const select = hh.select['select']
export const nav = hh.div['flex bg-base-200 shadow-sm/20 rounded-box items-center']
export const delim = hh.span.delim()
export const curSpan = hh.span['text-xs font-mono text-slate-500']

if (import.meta.hot) {
    import.meta.hot.invalidate()
}
