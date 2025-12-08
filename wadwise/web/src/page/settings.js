import { render } from 'preact'
import { signal, computed, batch } from '@preact/signals'

import { deleteIdxSignal, idify, fieldModel, pushSignal } from '../utils.js'
import { hh as h } from '../html.js'
import { button, submit, vstack, input, card, textarea, nav } from '../components.js'
import * as icons from '../icons.js'
import { AccountSelector } from '../account_selector.js'

const { div, form, a } = h
const header = h.h2['text-lg font-medium mb-1']

function wrapItem(item) {
    return {
        ...item,
        parent: signal(item.parent),
        clear: signal(item.clear),
        joints: signal(item.joints.map(signal)),
        assets: signal(item.assets.map(signal)),
    }
}

const joints = signal([])
const jointsStr = computed(() => JSON.stringify(joints))

const hasErrors = computed(() => {
    return !joints.value.every(
        (it) =>
            it.parent.value &&
            it.clear.value &&
            it.joints.value.every((a) => a.value) &&
            it.assets.value.every((a) => a.value),
    )
})

function add() {
    pushSignal(
        joints,
        wrapItem({
            id: crypto.randomUUID(),
            parent: '',
            joints: ['', ''],
            assets: [''],
            clear: '',
        }),
    )
}

function addParty(item) {
    batch(() => {
        pushSignal(item.joints, signal(''))
        pushSignal(item.assets, signal(''))
    })
}

function removeParty(item, pidx) {
    batch(() => {
        deleteIdxSignal(item.joints, pidx + 1)
        deleteIdxSignal(item.assets, pidx)
    })
}

function JointForm() {
    function partyFrag(card, pidx) {
        return [
            div['col-1 mt-2'](`Party ${pidx + 1}`),
            button['col-2 btn-sm mt-2 justify-self-start'](
                { onClick: () => removeParty(card, pidx) },
                icons.trash,
            ),
            div('Joint'),
            AccountSelector['col-2']({
                name: 'joint-other',
                ...fieldModel(card.joints.value[pidx + 1]),
            }),
            div('Asset'),
            AccountSelector['col-2']({
                name: 'asset-other',
                ...fieldModel(card.assets.value[pidx]),
            }),
        ]
    }

    function jointCard({ card, onDelete }) {
        return div['p-2 border-1 border-gray-300 rounded-box'](
            vstack['gap-2'](
                h.div['!grid grid-cols-[auto_1fr] items-center gap-y-1 gap-x-4'](
                    div('Main'),
                    AccountSelector['col-2']({ name: 'main', ...fieldModel(card.parent) }),
                    div('Me'),
                    AccountSelector['col-2']({ name: 'me', ...fieldModel(card.joints.value[0]) }),
                    div('Clear'),
                    AccountSelector['col-2']({ name: 'clear', ...fieldModel(card.clear) }),
                    card.assets.value.map((_, pidx) => partyFrag(card, pidx)),
                ),
                div['flex gap-2'](
                    button['btn-sm']({ onClick: () => addParty(card) }, 'Add Party'),
                    button['btn-sm']({ onClick: onDelete }, 'Remove Joint'),
                ),
            ),
        )
    }

    function JointList({ joints }) {
        return joints.value.map((card, idx) =>
            h(jointCard, { key: card.id, card, onDelete: () => deleteIdxSignal(joints, idx) }),
        )
    }

    return [
        header('Joint accounts'),
        form(
            { method: 'POST', action: './joint-accounts' },
            input.hidden({ name: 'data', value: jointsStr }),
            vstack['gap-2'](
                vstack['gap-2'](h(JointList, { joints })),
                div['flex gap-2'](
                    button({ onClick: add }, 'Add Joint'),
                    submit.primary({ disabled: hasErrors }, 'Save'),
                ),
            ),
        ),
    ]
}

function FavsForm({ favAccounts }) {
    const favs = signal(favAccounts.map(signal))

    function FavList() {
        return favs.value.map((it, idx) =>
            div['flex gap-1'](
                AccountSelector['flex-auto']({ name: 'acc', ...fieldModel(it) }),
                button['flex-none']({ onClick: () => deleteIdxSignal(favs, idx) }, icons.trash),
            ),
        )
    }

    return [
        header('Favorites'),
        form(
            { method: 'POST', action: './favs', 'data-preact': 'FavsForm', class: 'pure-form' },
            vstack['gap-2'](
                vstack['gap-1'](h(FavList)),
                div['flex gap-2'](
                    button({ onClick: () => pushSignal(favs, signal('')) }, 'Add'),
                    submit.primary('Save'),
                ),
            ),
        ),
    ]
}

function Settings(config) {
    const { curList } = config
    return [
        vstack['gap-2'](
            nav['p-2'](a['font-medium text-sm']({ href: '/account' }, 'Home'), div['h-4 m-2'](' ')),
            card(h(FavsForm, config)),
            card(h(JointForm, config)),
            card(
                header('Currencies'),
                form(
                    { method: 'POST', action: './cur-list' },
                    vstack['gap-2'](
                        textarea['w-full field-sizing-content']({
                            name: 'cur_list',
                            defaultValue: curList.join('\n'),
                        }),
                        div(submit.primary('Save')),
                    ),
                ),
            ),
            card(
                header('Backup'),
                form({ method: 'POST', action: './backup' }, submit.primary('Share database')),
            ),
        ),
    ]
}

joints.value = idify(Object.values(window.appData.jointAccounts)).map(wrapItem)
render(h(Settings, window.appData), document.querySelector('.content'))
