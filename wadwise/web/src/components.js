import { hh } from './html.js'

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
