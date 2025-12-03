import { render } from 'preact'
import { urlqs } from './utils.js'
import { hh as h, wrapComponent } from './html.js'

import { uselect, submit, input, textarea, card } from './components.js'

const { option, a, span, div } = h
const label = h.label['floating-label']

const Select = wrapComponent((props) => {
    const { options, ...rest } = props
    return uselect(
        rest,
        options.map(([v, t]) => option({ value: v }, t)),
    )
})

function AccountEdit({ form, accTypes, hiddenTypes, urls, accList }) {
    return card['pt-3'](
        h.form['flex flex-col gap-4'](
            { method: 'POST' },
            label(input.text['w-full']({ name: 'name', defaultValue: form.name }), span('Name')),
            label(
                Select['w-full']({ name: 'type', defaultValue: form.type, options: accTypes }),
                span('Type'),
            ),
            label(
                Select['w-full']({ name: 'parent', defaultValue: form.parent, options: accList }),
                span('Parent'),
            ),
            label(
                textarea['w-full']({
                    placeholder: 'description',
                    name: 'desc',
                    defaultValue: form.desc,
                }),
                span('Description'),
            ),
            label(
                Select['w-full']({
                    name: 'is_hidden',
                    defaultValue: form.hidden_value,
                    options: hiddenTypes,
                }),
                span('Show'),
            ),
            h.label(
                h.input['checkbox [type=checkbox]']({
                    name: 'is_placeholder',
                    checked: form.is_placeholder,
                }),
                ' Placeholder account',
            ),
            div['!flex gap-2 [&>*]:flex-auto'](
                submit.primary('Save'),
                form.aid && [
                    submit.danger(
                        {
                            formaction: urlqs(urls.account_delete, { aid: form.aid }),
                            onClick: (e) => {
                                if (!confirm('Delete?')) {
                                    e.preventDefault()
                                }
                            },
                        },
                        'Delete',
                    ),
                    a['btn btn-secondary'](
                        { href: urlqs(urls.account_edit, { parent: form.aid }) },
                        'Add subaccount',
                    ),
                ],
            ),
        ),
    )
}

render(h(AccountEdit, window.appData), document.querySelector('.content'))
