import { createPortal } from 'preact/compat'
import { useSignal, useSignalEffect, signal } from '@preact/signals'
import { useMemo } from 'preact/hooks'
import { hh as h, wrapComponent } from './html.js'
import { input, button, vcard } from './components.js'

const { a, div } = h

const AccountTree = wrapComponent(
    ({ value, onSelect, search, selectPlaceholder, excludeSpecial }) => {
        const { rootAccounts, jointAccounts, amap } = window.appData
        const selected = 'value' in value ? value.value : value
        const changed = useSignal(0)

        const unfolded = useMemo(
            () => Object.fromEntries((amap[selected]?.parents ?? []).map((it) => [it, true])),
            [selected],
        )

        function toggle(aid) {
            unfolded[aid] = !unfolded[aid]
            changed.value += 1
        }

        changed.value

        function renderList(accs) {
            return accs.map((aid) => {
                const acc = amap[aid]
                const hasChildren = !!acc.children?.length
                return [
                    div['flex items-center w-full'](
                        { class: { 'bg-base-300': selected == aid } },
                        div['!flex-none w-4 text-[60%]'](
                            hasChildren && (unfolded[aid] ? '▼' : '▶'),
                        ),
                        a['flex-1 cursor-pointer'](
                            {
                                onClick: (e) => {
                                    e.preventDefault()
                                    hasChildren ? toggle(aid) : onSelect(aid)
                                },
                            },
                            acc.name,
                        ),
                        div['flex-none flex gap-2'](
                            hasChildren &&
                                (!acc.is_placeholder || selectPlaceholder) &&
                                div(button['btn-xs']({ onClick: () => onSelect(aid) }, 'Select')),
                            acc.aid in jointAccounts &&
                                !excludeSpecial &&
                                div(
                                    button['btn-xs'](
                                        { onClick: () => onSelect(aid + '.joint') },
                                        'Joint',
                                    ),
                                ),
                        ),
                    ),
                    hasChildren && unfolded[aid] && div['ml-5'](renderList(acc.children)),
                ]
            })
        }

        function renderSearch() {
            const result = Object.values(amap)
                .filter(
                    (it) =>
                        it.aid &&
                        (!it.is_placeholder || selectPlaceholder) &&
                        it.full_name.toLowerCase().includes(search.value.toLowerCase()),
                )
                .toSorted((a, b) => a.full_name.localeCompare(b.full_name))
            return result.map((it) =>
                div['flex'](
                    a['flex-1 cursor-pointer'](
                        {
                            onClick: (e) => {
                                e.preventDefault()
                                onSelect(it.aid)
                            },
                        },
                        it.full_name,
                    ),
                    it.aid in jointAccounts &&
                        !excludeSpecial &&
                        div['flex-none'](
                            button['btn-xs'](
                                { onClick: () => onSelect(it.aid + '.joint') },
                                'Joint',
                            ),
                        ),
                ),
            )
        }

        return div['overflow-y-scroll pr-2 leading-8'](
            search.value?.length > 0 ? renderSearch() : renderList(rootAccounts),
        )
    },
)

export const AccountSelector = wrapComponent((props) => {
    const { value, onInput, name, selectPlaceholder, excludeSpecial, ...rest } = props
    const { amap } = window.appData
    const open = useSignal(false)
    const search = signal(undefined)

    useSignalEffect(() => {
        if (open.value) {
            window.accSelectorDialog.showModal()
        }
    })

    function onSelect(aid) {
        const e = { currentTarget: { value: aid } }
        onInput(e)
        open.value = false
    }

    return [
        input.text({
            ...rest,
            readonly: true,
            value: amap[value]?.full_name ?? 'Select account',
            onMouseDown: (e) => {
                e.preventDefault()
                open.value = true
            },
        }),
        input.hidden({ value, name }),
        open.value &&
            createPortal(
                h.dialog['#accSelectorDialog.modal transition-none'](
                    { onClose: () => (open.value = false) },
                    vcard['! p-4 modal-box gap-4 h-[96dvh] transition-none'](
                        div['flex gap-4'](
                            h.form['flex-1 w-full'](
                                { onSubmit: (e) => e.preventDefault() },
                                input.text['w-full']({
                                    autofocus: true,
                                    placeholder: 'search',
                                    onInput: (e) => (search.value = e.currentTarget.value),
                                }),
                            ),
                            button.secondary['flex-none'](
                                {
                                    onClick: (e) => {
                                        e.stopPropagation()
                                        open.value = false
                                    },
                                },
                                'Close',
                            ),
                        ),
                        AccountTree({ onSelect, value, search, selectPlaceholder, excludeSpecial }),
                    ),
                ),
                window.accSelectorPortal,
            ),
    ]
})

if (import.meta.hot) {
    import.meta.hot.invalidate()
}
